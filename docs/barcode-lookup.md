# Barcode lookup configuration

Status: MusicBrainz Album lookup and UPCitemdb Movie title lookup are implemented;
verify deployment separately. Mounted configuration overrides remain available.
The installed registry, not browser code, selects each external service. Lookup reads public suggestions; it never establishes catalog identity
or ownership. Physical camera capture and saved barcode observations remain
separate from external search.

In `apps/api/relicrat/collection_types/record.json`:

```json
"lookup": {
  "provider": "musicbrainz",
  "action_label": "Find album details",
  "max_results": 5,
  "field_mappings": {"title": "title", "artist": "artist", "format": "format"},
  "value_maps": {"format": {"12\" Vinyl": "Vinyl", "10\" Vinyl": "Vinyl", "7\" Vinyl": "Vinyl"}},
  "cover_art": true
}
```

The mapping keys are supported local form fields; values are public fields
exported by the installed adapter. Album's defaults fill only title, artist and
format after review. Date/country/label/catalog number help distinguish candidates
but do not automatically become the copy's edition. Missing values stay unknown.
Set `lookup` to null or omit it to disable external lookup for that type. Comics
and Other have no configured lookup. Rebuild/restart the API after bundled-config
changes; the authenticated definitions endpoint supplies current choices to web.
Malformed configuration fails startup. No migration or new dependency is required.

## Workflow and privacy

1. For a type with lookup configured, a successful scan stops the camera, attaches
   the barcode to the draft and searches immediately, without a separate barcode
   confirmation. Find album details can retry a lookup from the attached draft.
   A type without lookup keeps the explicit Use barcode step. Nothing is saved.
2. Review possible releases, source link and optional cover. Select fields to fill;
   nonempty current fields start unchecked. Changed drafts require another review.
3. Choose Use these details, review/edit the filled form, then Save copy or Save
   details. Existing save-conflict and unconfirmed-write rules still apply.

Only the barcode and release-cover identifier go to the configured provider and
cover host through the API. Camera frames, owner credentials and collection
records are not sent. The barcode is posted in a bounded body rather than an
inventory URL query. A failed/empty lookup leaves manual entry available. Covers are previews unless the owner explicitly selects Include catalog cover
and saves the form. Saved artwork retains its source and is separate from
physical-copy photos; see [optional catalog artwork](catalog-covers.md). Suggestions do not create/link catalog items
or releases; provider references are shown during review, not yet persisted as a
separate evidence record. Confirmed field changes use existing copy history.

MusicBrainz's search may return multiple pressings sharing a barcode. The adapter
checks returned barcode equality, allowing only the UPC-A/zero-prefixed EAN-13
equivalence, and preserves the original observed digits. UPC-E expansion, ISBN
conversion, fuzzy matching and automatic edition confirmation are absent. The
adapter honors a one-request-per-second process gate and bounded timeouts. The
current deployment has one API process; coordinate the gate across workers before
scaling it. Upstream throttling remains possible. No automatic retries or queues.

## Add or swap an adapter

1. Add a small Python adapter beside `musicbrainz.py`. Its `search(reading, limit)`
   returns a bounded list of public candidates. Import `LookupBusy`, `LookupTimeout` and `LookupUnavailable` from
   `barcode_errors.py` for safe, explicit failure. Keep raw error bodies and
   credentials out of responses/logs.
2. Register its stable ID in `barcode_providers.py` with `label`, a set of public
   exported `fields`, `source_origin`, `search`, and optional `cover` callable. Cover retention also
   needs a trusted `source_url` callable; optional `canonical_id` normalizes IDs.
3. Select that ID in the type JSON and change the mappings/translations to match
   its exported fields. Forms and inventory services require no provider branches.
4. Test config validation, exact identifier handling, malformed/oversized data,
   auth/redirect/URL boundaries, no-write behavior and the reviewed fill workflow
   with generated fixtures. Never use collection exports or owner records as tests.

Each candidate contains `id` (1–128 ASCII letters/digits/underscore/hyphen),
`title` (1–500 chars), `description` (up to1000), `source_url` (HTTPS on its
registered public origin), and `fields` (up to20 string values). Response values
are revalidated and bounded to destination storage limits. Cover requests use
that type's installed adapter and a bounded candidate ID, never a client URL.
Adapters own API differences and any private credential lookup. The config
contains no secrets, arbitrary path/import expressions or executable mappings.

For MusicBrainz, the fixed search destination is musicbrainz.org. Optional cover
requests start at coverartarchive.org and allow at most four HTTPS requests on
that host or archive.org subdomains; HTTP downgrades and other hosts are rejected.
Only small JPEG/PNG/WebP images within the pixel/byte limits are decoded and
transcoded to JPEG, behind owner access. Missing/unsafe art has a text fallback.

## Availability

Provider requests are optional and may time out or be rate limited. Keep manual
entry available; an unavailable result never discards the draft or silently
retries. A public protocol probe from a disposable worker container verified
MusicBrainz search and cover decoding after earlier transient search timeouts.
This confirms the adapter protocol, not catalog coverage or future availability.

## Deployment

The standard development Compose network already permits outbound access. A
private trial may deliberately use only an internal network. It needs a reviewed
API-only outbound path before live provider calls can work. The optional
`infra/docker/compose.lookup-egress.yaml` overlay attaches only API to an outbound
network while retaining its existing default network. It adds no published ports,
credentials, DB/web exposure, subnet routes or incoming public access. Verify the
merged Compose model and exact image/configuration identities before rollout;
record that network change in the private deployment receipts. Do not apply it to
an existing private deployment implicitly during tests or a routine backup.

Owner sign-in, exact origins, CSRF and secure cookies remain in effect. The new
API should be deployed before/with web; an old API returns an explicit lookup
failure and manual intake still works. Read-only lookup itself requires no schema migration. Optional saved artwork
requires migration 0012 and is included in ordinary database/media backups; see
the [cover migration and recovery contract](catalog-covers.md). Recovery keys and
the archive format are unchanged.

Sources: [MusicBrainz release search](https://musicbrainz.org/doc/MusicBrainz_API/Search#Release),
[rate-limit and User-Agent guidance](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting),
[Cover Art Archive endpoints](https://musicbrainz.org/doc/Cover_Art_Archive/API).

Optional cover retention uses the [catalog artwork contract](catalog-covers.md);
the default remains an unchecked selection and no media is saved during lookup.

## Slow or unavailable providers

Provider network reads allow up to eight seconds per read operation, with a
12-second elapsed budget checked before each request, after response headers and
after each body chunk. Remaining budget caps subsequent operations. This is not
a hard whole-request timer: an in-flight network operation can finish after the
elapsed budget and is then rejected. Host/redirect/type/size limits and search
throttling remain intact. There are no automatic retries.

Search timeouts return 504; upstream throttling returns 429; other unavailable
responses remain 503. The browser shows the sanitized API explanation and keeps
the draft/manual-entry/retry controls available. Transport failures do not say a
lookup was an unconfirmed inventory save. Diagnostic logs contain only failure
category/status, never barcode, URL, provider response body or owner data.

## Swap with an operator-owned config mount

Provider choice remains in each collection type's JSON; the browser has no
provider-specific branches. The installed registry translates provider APIs into
the common candidate/field/optional-cover contract. A config selects an installed
adapter; it cannot install arbitrary Python, URLs or credential expressions.
MusicBrainz and UPCitemdb are bundled live adapters; UPCitemdb exports title only and has no cover callable. Discogs is not
installed or activated: its integration needs a separate decision about token
setup, attribution and the provider's data-retention contract. This change tests
the swap boundary with a synthetic second adapter rather than claiming a second
production service is available.

For an existing image that includes this override support:

1. Create a private operator directory on the Docker host, outside the repository,
   uploads and media. Copy the complete bundled `record.json` there. Its stable
   filename and ID remain `record` even though the displayed label is Album.
2. Change `lookup.provider` to an installed adapter ID, and adjust
   `field_mappings`, `value_maps` and `cover_art` to its declared capabilities.
   Select `musicbrainz` to return to the current provider; set `lookup` to `null`
   to disable lookup for this type. No other type needs a copied config.
3. Set the operator shell's `RELICRAT_COLLECTION_TYPES_DIR` to that existing
   absolute host directory and add `infra/docker/compose.collection-types.yaml`
   to the deployment's existing Compose files. This mounts the directory
   read-only at `/etc/relicrat/collection-types` on **API only**. It preserves the
   database/media mounts and adds no ports or network access. The bind mount
   refuses to create a missing host directory. Review the resolved Compose model
   against the current deployment before applying it.
4. Recreate API using the existing project and all existing deployment overlays,
   then refresh the app. Config loads at process startup, not on every request;
   changing an existing mount's files requires an API restart. No image rebuild
   is needed for later config edits or swaps between installed adapters.

Example for the development Compose model (owner environment must already be
configured; this is not a command to apply unchanged to a private NAS trial):

```sh
export RELICRAT_COLLECTION_TYPES_DIR=/absolute/private/collection-types
docker compose -f compose.yaml -f infra/docker/compose.collection-types.yaml config --quiet
docker compose -f compose.yaml -f infra/docker/compose.collection-types.yaml up -d --no-deps api
```

`RELICRAT_COLLECTION_TYPES_DIR` inside API names the mounted container directory,
while Compose substitution uses the host operator directory. Without the variable
in API, all bundled definitions apply. With it, one or more known filenames
(`record.json`, `comic.json`, `movie.json`, `other.json`) override their bundled definitions;
unmentioned types keep their bundled defaults. A missing/empty directory, unknown
JSON filename, mismatched ID, malformed JSON, duplicate keys, oversized file
(over 64 KiB), uninstalled adapter or invalid schema prevents startup. A broken
override never silently falls back to the previous provider.

Keep provider tokens in private environment/secret files injected only into API
by that adapter's deployment overlay. Tokens never belong in collection JSON,
Git, browser definitions or a URL. This generic mount contains no credentials.
An adapter-specific token is not automatically forwarded to other providers.
No automatic fallback calls a second service: the config selects who receives the
barcode. Manual retry and final-save rules remain unchanged.

After a provider swap, refresh the app and review any pending match again before
saving. A staged cover from the previous provider is rejected rather than
reinterpreted under the new provider; existing saved media and source metadata
remain intact. Reverting the mounted JSON and restarting API reverses the choice;
removing the overlay and recreating API restores bundled defaults. Preserve the
prior private config and deployment receipt for rollback. No migration is needed.

Provider-specific use requirements remain part of each integration's contract.
See [Discogs API terms](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use)
for the attribution and retention requirements that prevent treating it as an
unreviewed drop-in source for durable artwork.

Recovery note: an operator mount is deployment configuration outside the Git
archive. Before enabling it on a private trial, retain its exact validated files
and checksums in the private deployment/recovery evidence and update the capsule
procedure to recover them. The existing Git-source capsule does not automatically
include arbitrary host-mounted definitions. Never substitute a config directory
containing provider credentials. No live mount or backup workflow is changed by
this PR.


## Movie title lookup with UPCitemdb

Movie's bundled JSON selects `upcitemdb`, maps only `title` to `title`, uses
**Find movie details**, and sets `cover_art` to false. Change provider/mappings in
that same config to select another installed adapter, or set lookup to null to
disable it. The existing scan → review → fill draft → explicit save flow applies.
No provider-specific browser branch, new dependency, migration, account or key is
needed. Rebuild/restart API for bundled changes; an existing read-only operator
mount can override movie.json using the established recovery/config contract.

UPCitemdb is a general retail database, not an authoritative movie-edition catalog.
Results identify themselves as retail suggestions and display bounded brand and
category text when supplied. Brand is not treated as studio. Titles are not parsed
to invent format, edition, disc count, studio, catalog identity or quantity. Only
a reviewed title can fill the form; all other observations remain manual. Returned
UPC/EAN must agree exactly with the scan or its UPC-A/zero-prefixed EAN-13 equivalent.
Conflicting codes are rejected. GTIN-14 packaging codes are ignored; there is no
UPC-E expansion, fuzzy search, automatic retry or fallback provider.

The fixed HTTPS destination is api.upcitemdb.com/prod/trial/lookup. Only the observed
barcode is sent, never photos, credentials or collection records. Response bytes
are bounded to 1 MiB, redirects and compressed/non-JSON bodies are rejected, and
timeouts use eight-second reads plus a checked twelve-second elapsed budget (not
a hard whole-request timer). Provider image URLs, offers and pricing are ignored;
no third-party artwork is downloaded, previewed or retained by this adapter. The
existing Album cover feature remains available through its own provider.

The no-signup free plan currently allows 100 combined requests/day, one connection
and a sustained lookup every ten seconds. A per-process gate enforces the latter;
coordinate across processes before scaling the one-process deployment. Provider
429 responses impose a sixty-second local cooldown and return a sanitized 429 with
Retry-After; a daily quota may require waiting until the provider resets it. There
is no paid-plan activation, automatic retry or claim of persistent local quota
accounting across restarts. A documented 404 NOT_FOUND is an empty result; other
404/error bodies remain explicit failures. Lookup never creates ownership or media.

Checked 2026-11-01 against the provider's [free-plan limits](https://www.upcitemdb.com/wp/docs/main/development/plan/),
[response schema](https://www.upcitemdb.com/wp/docs/main/development/responses/) and
[service terms](https://www.upcitemdb.com/terms). Availability, metadata accuracy and
coverage are not guaranteed. The private deployment needs its existing API-only
outbound access; this implementation does not change network topology.
