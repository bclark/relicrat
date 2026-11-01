# Owner access

All inventory, catalog, storage, history and photo endpoints require a current
owner Bearer session. Browser clients use the private Next.js cookie gateway.
Only minimal GET /health and bounded POST /api/v1/auth/login are anonymous.
See [owner access](../../docs/owner-access.md) for the authentication contract.

# Inventory text search

`GET /api/v1/inventory?q=blue%20cover&limit=50&offset=0` returns physical
copies whose provisional title, personal edition label, description, current catalog canonical name, or
current release name contains the search text, case-insensitively using
PostgreSQL's database collation. Surrounding whitespace is trimmed; omitted,
empty, or whitespace-only `q` uses the original unfiltered listing. The input
limit is 200 characters before trimming; longer input and NUL characters
(which PostgreSQL text cannot store) return 422.

Search treats `%`, `_`, backslashes, quotes, and SQL-looking input as literal
text. SQLAlchemy binds parameters and escapes LIKE pattern characters. It is
one substring, not a token/query language: no stemming, ranking, typo correction,
or accent folding. NULL fields do not prevent another field matching.

Responses retain the existing inventory shape and newest-first order
(`created_at DESC, id DESC`), with limit 1–100 and nonnegative offset. Only
non-deleted physical copies are returned; catalog records alone never imply
ownership, and distinct copies of the same identity remain distinct. As with the
existing list endpoint, sold/traded/lost records are included. Offset pagination
is deterministic for a fixed dataset; concurrent writes can shift page boundaries.
Search does not modify copies, identification, storage, history, or photos.

No migration, dependency, or deployment change is needed. Substring matching
can scan the inventory and linked identities; large-collection performance has
not been measured. Add indexing or a different PostgreSQL search strategy when
measurements justify it. This is inventory text search only, without location
subtrees, global catalog search or facets. The web screen uses this query
for its inventory list.

# Manual reconciliation

`POST /api/v1/inventory/{copy_id}/reconcile` accepts:

```json
{"catalog_item_id":"existing-uuid", "release_id":null, "expected_revision":0}
```

Catalog is required and cannot be cleared. The fields describe the complete
identification: omitted or null release means catalog-only, including removal of
an earlier release. Unknown fields, malformed UUIDs and noninteger/negative
revisions return 422 (accepted range: 0–2147483646). GET/list inventory responses expose `identification_revision`.
Existing copies start at zero, without invented historical events.

The service locks the copy row and checks the expected revision before applying
changes. Stale requests return 409, even when their target matches current state;
reload and review before retrying. Missing or soft-deleted copies and missing
catalog/release identities return 404. A release belonging to another catalog
returns 422; the existing composite database FK remains the final guard.

A change to catalog, release or identification status sets status to `identified`,
increments revision once, and commits one manual event in the same transaction.
It never sets `verified`. A request at the current revision with the same catalog,
release and `identified` status returns 200 with unchanged revision, timestamps
and history. A status-only change (including from `verified`) is an event.
UUID, provisional title/description, creation time, ownership/disposition,
location and photos are preserved. Concurrent requests with one expected revision
permit at most one actual change; identical requests can subsequently be stale.

`GET /api/v1/inventory/{copy_id}/reconciliations?limit=50&offset=0` returns events
in ascending resulting revision order. Limit is 1–100; offset is nonnegative.
Each event has copy/event UUIDs, before/after catalog, release, status and revision,
`operation: manual`, and database transaction time `created_at`. Revision gives
ordering even if timestamps coincide. No history mutation endpoints exist.
This is identification history only, without authentication, actor attribution or
protection from a privileged database editor. References restrict deletion of
identities needed by historical events.

## Migration and recovery

Apply additive `0002_reconciliation` before serving the changed API. It adds a
nonnegative, nonnull revision defaulting to zero and the event table with FKs,
status/manual/revision checks and a unique per-copy resulting revision. Migration
0001 is unchanged. Normal PostgreSQL DDL locking applies; schedule deployment
accordingly. ORM identification updates advance `updated_at`; direct SQL retains
the existing timestamp behavior and must explicitly set timestamps as needed.
Direct SQL is not a reconciliation API and does not automatically generate events.

Downgrading drops every reconciliation event and revision counter, while retaining
current identification and photos. Before any nondisposable downgrade: stop all
writers, capture and verify a quiescent full PostgreSQL dump and matching media
snapshot, and preserve the application revision and keys/configuration needed to
restore. To recover lost history, stop writers and restore that pre-downgrade dump
and media together to a separate clean database/media target using the matching
application revision; verify identities, events and downloads before switching.
Re-upgrading alone initializes revisions to zero and cannot recover history.
The harness exercises destructive downgrade only on disposable synthetic data.

The synthetic recovery rehearsal now retains two reconciliations and all referenced
identities alongside the original exact photo bytes after source destruction.
Its quiescent-writer and same-schema-version assumptions remain; this is not
production backup support. That rehearsal did not exercise catalog creation/UI;
see the current manual catalog contract below. Authentication, automated matching
and broader audit history remain out of scope.

## Storage locations and manual movement (0003)

`POST /api/v1/storage-locations` creates a location with `name` (trimmed,
1–250 characters), optional existing `parent_id`, optional `kind` (up to 100)
and `description` (up to 10000). Strings are trimmed. Unknown fields, invalid
UUIDs and invalid lengths return 422; a missing parent returns 404.
`GET /api/v1/storage-locations` lists by creation time then UUID, ascending,
with `limit=50` (1–100) and nonnegative `offset=0`.
`GET /api/v1/storage-locations/{id}` returns one location or 404. Responses
include UUID, parent UUID, name, kind, description and creation/update timestamps.
There are no location rename, reparent or deletion endpoints.

`POST /api/v1/inventory/{copy_id}/location` accepts the complete target:

```json
{"storage_location_id":"existing-location-uuid", "expected_storage_revision":0}
```

Both fields are required. Explicit null location unassigns the copy. The revision
must be an integer (not boolean/string), 0–2147483646. Unknown fields and invalid
UUIDs return 422. Inventory responses expose independent `storage_revision`,
initially zero for existing copies. Missing/deleted copies or missing targets
return 404; stale storage revisions return 409, including stale identical targets.
The service locks and reloads the copy. At the current revision an identical
target returns unchanged timestamps, revision and history. A real change advances
only storage revision, current location and ORM `updated_at`; identification,
provisional information, ownership, creation time and photos remain unchanged.
Identification and storage serialize on the same copy lock but use independent
revision counters. Movement and its event commit or roll back together.

`GET /api/v1/inventory/{copy_id}/locations?limit=50&offset=0` returns manual
movement events in ascending resulting storage revision order. Pagination uses
the same limits. Each event contains UUID, copy UUID, nullable before/after
location UUIDs, before/after revision, `operation: manual` and transaction time
`created_at`. FKs restrict deleting referenced copies/locations; checks require a
changed target and a nonnegative single revision step, with one resulting
revision per copy. History has no mutation endpoints or actor attribution and
is not tamper-proof against a privileged database editor. Direct SQL copy updates
do not automatically generate history or update timestamps.

Apply additive migration `0003_storage` before serving this API. Migrations 0001
and 0002 are unchanged. The migration takes an ACCESS EXCLUSIVE lock on locations,
checks the legacy topology, and installs protection in the same transaction.
A legacy cycle fails with a diagnostic and rolls back installation; an operator
must review and repair the topology separately, preserving records.

Every hierarchy INSERT/UPDATE/DELETE first actually updates one narrow singleton
guard row, holding its write lock until transaction completion. An AFTER STATEMENT
trigger recursively checks the final graph after INSERT/UPDATE, including all
rows from multi-row statements. The functions are volatile (PostgreSQL's default).
At READ COMMITTED the check gets fresh visibility after a competing guard writer
commits; a cycle fails with SQLSTATE 23514. At REPEATABLE READ, an older snapshot
conflicts with the actual guard write and fails with 40001. SERIALIZABLE may also
require a whole-transaction retry. Missing guard state fails closed with 23514.
Callers must roll back rejected transactions and review/retry from a fresh
snapshot; no automatic retry policy is provided. This deliberately serializes
hierarchy mutations and scans the graph, favoring correctness for this first
storage task; large hierarchies have not been load tested. It follows PostgreSQL's
[consistency/locking guidance](https://www.postgresql.org/docs/17/applevel-consistency.html)
and [statement trigger visibility](https://www.postgresql.org/docs/17/trigger-datachanges.html).

Downgrade to 0002 removes **all movement events, storage revisions and new cycle
protection**, retaining current assignments, location records, identification and
media. Before a nondisposable downgrade, stop every API/job/SQL writer, run
`pg_dump --format=custom --file=pre-0003.dump relicrat` using the operator's secured
connection configuration, and archive the configured media root with
`tar -C "$MEDIA_ROOT" -cf pre-0003-media.tar .`. Keep both artifacts, checksums,
application revision and secured configuration together outside the live volumes.
Restore the dump with `pg_restore --exit-on-error --dbname=relicrat_recovery
pre-0003.dump` into a new empty database, extract media to a separate empty root,
and verify row counts, history, assignments and exact photo downloads using the
matching application revision **before** downgrading. These commands describe an
operator procedure, not a supported production backup tool. To recover after
downgrade, stop writers and restore that verified DB/media pair to separate clean
targets, verify again, then switch configuration. Re-upgrading initializes zero
revisions and empty movement history; it cannot recover lost events.

The synthetic recovery fixture retains a nested hierarchy, current assignment,
two movements, two reconciliations and exact photo bytes after source destruction.
Authentication, catalog identification UI, operator production backups,
container reparenting/history and broader provenance remain unfinished. The first
vertical slice is incomplete.

The hierarchy functions pin their schema lookup to pg_catalog/public with
pg_temp last. Temporary relations named like the hierarchy or guard cannot
replace the canonical tables. Focused direct-SQL tests cover both shadowing
cases, alongside the existing isolation-level races.

# Manual catalog lookup and creation

`GET /api/v1/catalog/items?q=literal&limit=50&offset=0` searches canonical names
with the same escaped, parameterized substring behavior as inventory search.
`q` is trimmed, at most 200 characters before trimming, and rejects NUL. Empty
search lists entries. Order is canonical name then UUID; the database collation
applies. `GET /catalog/items/{id}` returns one entry. All paths in this section
have the `/api/v1` prefix. These endpoints never create or change owned copies.

`GET /catalog/categories` lists categories by name/UUID. `POST` takes `name`
(trimmed, 1–200 characters). `POST /catalog/items` takes `category_id` and
`canonical_name` (trimmed, 1–500); missing categories return 404.
`GET /catalog/items/{id}/releases` lists releases of that item by creation time/UUID;
missing items return 404. `POST` on that collection creates a release with `name`
(trimmed, 1–500). `GET /catalog/items/{id}/releases/{release_id}` returns 404 if
the release is missing or belongs to another item. Existing unnamed releases
remain readable. Lists use limit 1–100 and nonnegative offset, with default 50.
New names reject NUL; unknown payload fields and malformed UUIDs return 422.

Each manual create generates a separate UUID-based `manual-...` slug/identity key/
release key using the existing schema. Names are descriptive, not a deduplication
key. Similar or equal names never silently merge, and there is no upsert,
rename, deletion, attribute editing, provider matching or catalog verification.
Search first and choose explicitly; duplicate names are distinguished by reference.
A category, catalog item, release and copy reconciliation are separate transactions.
A failed or uncertain reconciliation does not undo a confirmed catalog creation.
There are no idempotency keys or automatic retries after uncertain outcomes.

The web record now supports this lookup/creation flow followed by an explicit
Save identification using the existing expected identification revision. The
No release specified option intentionally removes a previous edition. It does
not clear the catalog identity. Current entries/releases are fetched independently
of result pages, so a selection beyond page one is not silently lost. Catalog,
category, release and identification-history pages are bounded at 20 with a
one-row lookahead. Read cancellation rejects obsolete responses; unknown/failed
reads remain errors rather than fabricated identities. Historical references are
retained in oldest-first history. Drafts remain page-local.

No migration or dependency is added. Existing composite FKs and reconciliation
transactions still enforce matching catalog/release and preserve physical UUID,
photos, provisional fields, ownership and independent storage history/revision.
Authentication and production deployment remain unfinished; synthetic data only.
Offset pages may shift under concurrent catalog creation. There is no catalog
uniqueness inference or large-catalog performance guarantee.

# Edit a saved physical copy

`POST /api/v1/inventory/{copy_id}/details` atomically changes that copy's own
`title` and `edition_label`. It never creates catalog records, changes a catalog
or release link, creates ownership, or edits another physical copy.

```json
{
  "title": "Harbor Lights",
  "edition_label": "Blue vinyl",
  "expected_details_revision": 0,
  "expected_identification_revision": 0
}
```

Both revision fields are required strict integers. A stale copy-edit revision or
catalog-match revision returns 409 before writing. Storage revisions remain
independent. A no-op with current revisions returns the unchanged record without
an event or timestamp update. Missing/deleted copies return 404. Labels trim
surrounding whitespace, reject NUL, and have a 500-character limit. Clearing the
title requires retained meaningful notes or a photo; an edition alone does not
replace the existing recognizable-content requirement.

Inventory responses add `details_revision` and nullable `edition_label`:

- `null`: no personal edition label; the UI may show the existing linked release.
- Nonempty text: the owner's explicit label for this physical copy.
- Empty text: the owner explicitly left the edition unknown, even if a catalog
  release is linked. Unknown is not a zero or a verified match.

Editing only a title preserves an unchanged linked edition. Personal labels
remain explicit and survive later catalog matching; they do not rename or
reclassify the shared release. They participate in the same literal inventory
search as titles and notes. The UI shows the personal-label source when a shared
release is also linked.

`GET /api/v1/inventory/{copy_id}/detail-history?limit=20&offset=0` returns bounded,
oldest-first before/after labels and revision numbers. Each edit records the
identification revision observed under the same copy row lock, so the separate
match history supplies context for inherited editions. UUID, creation time,
photos, storage, disposition and prior histories are retained. Failed transactions
roll back both labels and history. An uncertain response must be reloaded and
reviewed; clients never automatically retry a POST.

Migration 0005 adds the nullable label, a default-zero revision and an audit table.
Existing rows retain their old values and timestamps. Upgrade before starting the
new API/web pair. Downgrade intentionally drops the new edition labels and copy
edit history; it is exercised only on disposable data. Before any live migration,
capture and verify a recovery copy. Do not automatically downgrade live data to
roll back a web release; the new API can serve the earlier web while recovery is
reviewed. Use a matching API image/migration head for backup verification.

## Personal Records details and setup

Migration0006 adds `collection_type` (`other` or `record`, default `other`) and
`record_details` (default `{}`) to physical copies. The bounded object accepts only
optional `artist` (500 characters) and `format` (100 characters). Blank values are
omitted as unknown. New Other copies reject record observations; an explicit type
change on an existing copy preserves its saved observations. Shared catalog and
release attributes are untouched.

Creation optionally accepts these fields plus `edition_label`. The details save
accepts type and observations in the existing revision-checked transaction and
extends before/after history. Omitted new fields preserve current values for older
clients. Explicit `{}` clears observations with retained history. Literal search
includes artist and format with parameterized escaping, even if setup hides them.

`GET /api/v1/collection-settings` returns the single owner's `status` (`not_started`,
`skipped`, `configured`), `records_enabled`, `default_type`, `record_fields` and
`revision`. `POST` takes those values plus `expected_revision`. Record fields are a
unique bounded selection of `artist`, `format`, `edition`, `notes`; no arbitrary
schema is accepted. The Record default requires Records enabled. Stale writes409;
invalid values422; missing preference row503. A no-op keeps its revision. Both
methods require owner authentication; writes retain same-origin browser defenses.
Setup writes never alter inventory, visibility preferences never delete copy data,
and all preferences are included in database capture and independent recovery.


`GET /api/v1/collection-settings/types` is an owner-only, read-only map of the
bundled version-1 entry definitions (`other`, `record`). Setup/intake labels,
optional field order, suggested visibility and bounded input lengths come from
these validated JSON files. Definitions never change ownership or stored owner
preferences. The existing collection-settings GET/POST contract is unchanged.
Unsupported methods are rejected; custom type uploads are not supported.


`GET /api/v1/collection-settings/artist-suggestions?q=...` is owner-only and
read-only. `q` is optional, at most 500 characters, without NUL. It returns up to
20 artist strings from non-deleted Record copies, grouped case-insensitively,
with deterministic casing/order and literal case-insensitive prefix matching.
Unknown/blank values and Other-type copies do not contribute. Suggestions never
write ownership, settings, audit history or catalog identities. No external
provider, new table or migration is involved.

## Comics

`collection_type: "comic"` accepts bounded `comic_details` with optional string
`issue_number` (100 characters) and `publisher` (250 characters). Series/title
uses the existing title; personal cover/edition uses `edition_label`. Values are
trimmed and blank means unknown. Browser entry requires only Series/title.
Create rejects nonempty Comic observations on a different type; revision-checked
edits preserve existing observations across explicit type changes. Omitting the
new field in an older client preserves it. Responses and history expose current
and before/after Comic observations. Search matches literal issue/publisher text.

Settings additionally expose `comics_enabled` and `comic_fields` (issue_number,
publisher, edition, notes), and allow default `comic` only when enabled. Omitted
new preference keys preserve their persisted values. Revision/no-op/conflict and
transaction boundaries are unchanged. `GET collection-settings/publisher-suggestions`
is owner-only, read-only and returns at most 20 deduplicated literal prefix matches;
`q` is at most 250 characters without NUL. Definitions now include `comic`.
Migration 0007 requires the release plan in ADR 0006 and refuses destructive downgrade.

`GET /api/v1/inventory` accepts optional `collection_type=record|comic|other`.
Omitting it returns all types. The validated exact type condition is combined
with literal `q` search and applied before limit/offset; ordering, deletion filters
and owner access are unchanged. Filtering never changes ownership or type.

## Appearance (schema 0008)

Owner-only `GET /api/v1/appearance` returns `theme`, allowlisted React `styles`,
`revision`, `default_theme`, `presets`, and the theme JSON `schema` for authoring.
Theme fields and color roles are documented in
[the authoring guidelines](../../packages/themes/AUTHORING-PROMPT.md).

`POST /api/v1/appearance/preview` accepts `{ "theme": <theme object> }`, validates
it, and returns `theme` and `styles`. It writes nothing. `POST /api/v1/appearance`
accepts `{ "theme": <theme object>, "expected_revision": <integer> }` and returns
`theme`, `styles`, and `revision` after commit. It locks the singleton row and
increments the independent appearance revision only when values change. A stale
revision returns 409, invalid values/contrast return 422 with a bounded explanation,
and unavailable/invalid persisted settings return 503. Unknown fields and executable
styling are rejected. All three endpoints use the same owner/origin gateway boundary.

Previews and applies do not touch inventory, history, catalog or collection setup.
Unconfirmed writes require reload/review, with no automatic retry. The app uses
prompts/Markdown guidelines with a user-selected AI tool; no model endpoint is
called. See [ADR 0007](../../docs/decisions/0007-appearance.md) for migration,
rollback, accessibility checks and remaining limits.

## CSV imports (schema 0009)

Owner-only `POST /api/v1/imports/preview?source=clz|discogs` accepts raw UTF-8
comma-separated CSV with `Content-Type: text/csv`. Preview writes nothing. The
response includes an SHA256, fixed field mapping, first ten normalized rows,
copy/row counts, up to 50 row errors, repeated-ID advisory count and an existing
exact-file batch when present. All row errors block the whole import.

`POST /api/v1/imports/commit?source=…&reviewed_sha256=…` accepts the same bytes,
reparses and validates them, and checks the reviewed digest. A single transaction
creates provisional physical copies, a batch, and retained original column/value
objects per copy. CLZ accepts only `In Collection` and positive whole Quantity;
Discogs creates one copy per row. Issue identifiers stay text; detailed Discogs
Format values stay intact. No catalog/release, financial value, grading authority,
storage assignment or preference is inferred. CLZ storage boxes and Discogs
folders remain source information in this increment.

Limits: 4 MiB file, 100 unique nonempty headers, 5,000 CSV records, 10,000 copies,
standard-library CSV field limit, mapped field/domain limits and 16 MiB expanded
JSON evidence. Invalid UTF-8, NUL, malformed records and mismatched columns are
rejected without echoing file contents in errors. CSV record numbers (header is
record 1) are used even when quoted fields contain line breaks. Nothing evaluates
formulas, HTML or URLs in source cells.

A unique `(source, sha256)` batch insert serializes simultaneous exact-file
retries, including a lost response. It is not cross-export deduplication: changed
bytes create a new batch, and repeated source IDs never merge physical copies.
Commit does not automatically retry. Preview the same file to inspect completion
following an uncertain write. No imported item overwrites an existing copy.

`GET /api/v1/imports?limit=20&offset=0` lists batches newest first;
`GET /api/v1/imports/{batch_id}/rows?limit=20&offset=0` lists retained fields,
copy UUID, source record and quantity expansion index. Both are private and
paginated (maximum 100). Source metadata is evidence, not executable content.
Batch/source references use restrictive foreign keys. Existing full database
backups include these tables. Migration downgrade refuses any retained batch;
retain provenance or use a verified pre-import recovery copy. There is no batch
delete/undo API or automatic matching across revised exports.

## Grouped browsing

Owner-only `GET /api/v1/collection-groups` returns collection-type counts when
`collection_type` is omitted, or configured artist/series summaries when it is
`record`/`comic`. Each summary has `collection_type`, `value` (nullable), `label`
and `copy_count`. Counts cover the entire matching inventory before summary
pagination. `limit` defaults to 20 (maximum 100); `offset` defaults to 0. Results
sort by label, with unrecorded group fields last. Unknown artist/series groups use
a null value; ordinary labels remain exact, case-sensitive saved text after
trimming outer spaces. These are navigation groups, not canonical identities.

Both summaries and `GET inventory` accept the same literal `q`, optional
`storage_location_id` UUID, and `unassigned` boolean. Location matches the copy's
exact current location, without descendants. Choosing a location together with
`unassigned=true` is rejected. Soft-deleted copies are excluded, consistently with
normal listing. Summaries group across the full filtered result; member paging is
independent.

`GET inventory?collection_type=record|comic&group=…` lists exact group members.
`group=` selects copies with an unrecorded group field; omitting group preserves
the existing individual-copy listing. Group requires Albums/Comics, is bounded to
500 characters, and is bound as data even when it contains wildcards or markup.
Search and location filters apply before member limit/offset. Grouped Albums sort
by title. Comic issues sort by their leading whole number, then full issue text;
non-numeric/special issues follow numeric prefixes and missing issues sort last.
The issue text is never rewritten or interpreted as an identity.

`grouping` in the bundled collection-type JSON defines its field, plural label,
unknown label and supported member order. Only the deployed artist/title grouping
and title/issue ordering combinations are accepted; Other remains ungrouped.
Grouping performs no writes or inference, changes no UUIDs, and never combines
physical copies. No migration, provider, new index or stored owner preference is
introduced.

## Observed barcodes (schema 0011)

An optional `barcode` observation belongs to a physical copy, not to a shared
catalog identity. Create accepts `null`/omission (unknown) or an object such as
`{"value":"012345678905","format":"UPC_A","supplement":"00001"}`.
Values stay ASCII digit strings including leading zeroes. Supported formats are
UPC_A (12 digits), UPC_E (8), EAN_8 (8), EAN_13 (13); supplements are optional two
or five digits. No identifier conversion, checksum certification or edition
inference is made. API and PostgreSQL both bound the persisted shape. Unknown
readings return `{}`; absent supplements are omitted, never filled with zeroes.
Multiple copies can have the same barcode. A barcode alone does not qualify as
meaningful provisional intake. Imports do not infer barcodes from source columns.

The revision-checked details endpoint accepts the same `barcode` object, or
explicit `null` to remove it; omission preserves the saved observation for old
clients. Corrections/removals share the existing copy lock, details revision and
transaction with labels, and retain `before_barcode`/`after_barcode` in detail
history. Search `q` also matches the observed main barcode as literal text;
supplements are not searched or merged into the main digits. This remains an
owner-authenticated inventory search, not a provider lookup or unique match.

Type definitions declare a bounded `barcode_formats` list consumed by the scan
review UI. Omission disables new scans for earlier version-1 definitions without
hiding saved observations. Settings/optional-field preferences remain unchanged.
There is no configurable URL, executable rule or external provider.

Apply migration 0011 before deploying the API/web together. Upgrade gives every
existing copy an empty barcode and leaves all prior columns/history intact.
Downgrade locks both tables and refuses to drop current or historical barcode
observations, including edits that only changed a barcode. Retain a verified
backup and matching source/images before rollout; use the older release against
an isolated recovery restore when rollback is needed. Do not delete observations
or history to make a production downgrade succeed. Offline backups already
capture all columns and bundled source; no new volume or credential is required.

## Configured barcode suggestions

Owner-only `POST /api/v1/barcode-lookups/{collection_type}` accepts the same
validated barcode reading used for copy observations and returns bounded
provider candidates. The type definition selects an installed adapter, fields,
value translations and optional cover previews. Album initially uses MusicBrainz;
Comics and Other have lookup disabled. Unsupported formats return 422; a missing
configuration returns 404; busy/unavailable providers return 429/503.

`GET /api/v1/barcode-lookups/{collection_type}/{candidate_id}/cover` proxies only
the configured adapter's validated image destination, behind owner access. No
client URL is accepted. Source links and field values are validated; browser
review fills selected draft fields only. Neither endpoint creates a catalog
identity, release, physical copy, photo or audit event. The ordinary final save
retains existing copy history and revision checks. See the complete
[configuration and adapter contract](../../docs/barcode-lookup.md).

No migration or dependency is added. Private internal-only deployments require
an explicitly reviewed API outbound network before live lookup works.
