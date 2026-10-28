# Inventory text search

`GET /api/v1/inventory?q=blue%20cover&limit=50&offset=0` returns physical
copies whose provisional title, description, current catalog canonical name, or
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
subtrees, global catalog search, facets, or a search UI.

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
production backup support. Catalog CRUD/UI,
authentication, automated matching and broader audit history remain out of scope.

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
Authentication, usable frontend/catalog UI, operator production backups,
container reparenting/history and broader provenance remain unfinished. The first
vertical slice is incomplete.

The hierarchy functions pin their schema lookup to pg_catalog/public with
pg_temp last. Temporary relations named like the hierarchy or guard cannot
replace the canonical tables. Focused direct-SQL tests cover both shadowing
cases, alongside the existing isolation-level races.
