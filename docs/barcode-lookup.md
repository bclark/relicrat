# Barcode lookup configuration

Status: implemented for review; not deployed. MusicBrainz is the first installed
adapter. Lookup reads public suggestions; it never establishes catalog identity
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
   returns a bounded list of public candidates. Raise `LookupBusy` or
   `LookupUnavailable` for safe, explicit failure. Keep raw error bodies and
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
