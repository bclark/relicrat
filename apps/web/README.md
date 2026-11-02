# Browser/API connection (development only)

The add-first inventory screen supports provisional copies, photos, immediate
storage changes, and inventory search. Use synthetic records and test photos only.
The server exposes the existing inventory/storage API at `/api/v1/...` on the same
origin behind single-owner authentication. This remains a synthetic development deployment.

## Appearance

Appearance supports visual themes for colors, body/heading fonts, section spacing,
corners and density. Choose a starting theme or adjust the controls, preview the
sample, then explicitly apply it. Applied appearance is an owner preference stored
on the server, with a separate conflict revision. It does not change inventory or
collection setup. Login retains the default look; the saved theme loads after
authentication. Reload appearance after an uncertain save or revision conflict.

Under **Make a theme with AI**, describe a look and copy the generated prompt or
download its Markdown guidelines. Give it to your preferred AI app, then paste
the returned JSON under **Import or export a theme**. RelicRat makes no model
requests and needs no AI key. The guidelines contain the description and theme
settings, without collection data. Manual/imported themes use the same strict
validation and contrast checks. The reusable guide is
[AUTHORING-PROMPT.md](../../packages/themes/AUTHORING-PROMPT.md).

This feature requires migration `0008_appearance` and matching API/web code.
Downgrade refuses customized themes; see [ADR 0007](../../docs/decisions/0007-appearance.md).

The approved factory palette uses ivory/white surfaces, charcoal text and burgundy
actions, with a forest/gold dark preset. Migration `0010_brand_default` aligns new
installations and untouched legacy factory settings; saved owner choices remain
intact. Login and initial loading use the branded light palette. A portable export
is [relicrat-default.json](../../packages/themes/relicrat-default.json). Review the
ADR's rollback behavior before downgrading.

## First screen

A title is the only required field when adding a find in the browser. Notes, edition,
photos, storage and catalog matching are optional. The API still supports notes-only
intake, and existing copies are preserved. Save the title to create one provisional
physical copy, then use
its record to upload JPEG/PNG/WebP photos and choose storage. Creating a storage
location does not move the copy: choose it in Location afterward. Choosing a
location saves immediately, shows “Saving location…” while pending and confirms
“Added to Comic box B.” beside the selector after success. Choosing Unassigned
removes the assignment while retaining movement history. A failed save keeps the
last confirmed selection; uncertain results require reload and review.

The list searches literal text and paginates 20 copies per page. It includes
non-deleted sold/traded/lost copies, just like the API; it is not an ownership
filter. Search, storage choices and history use bounded pages, without claiming a
partial page is a total count. Load more locations/history when offered.

Copy creation, photo upload, storage creation and assignment are separate saves.
A failed photo does not undo the saved copy. Double submission is blocked in
flight. Stale storage or uncertain save outcomes disable record saves until an
explicit reload; the UI never automatically repeats a POST. Reload and inspect
before deciding to save again. Existing record data, photos and history remain
server-authoritative; unsaved form drafts are page-local and do not survive
navigation/reload. Switching copies clears that record's unsaved file selection.

Open a saved copy and use **Edit this copy**. Its existing title is prefilled;
**Edition** is optional. **Save details** updates both labels together on the same
physical copy and retains an edit history. No catalog setup is required. The
collection displays saved-copy status instead of treating unmatched copies as
unfinished. Personal edition labels also appear in list labels and literal search.

Existing matched editions prefill the form. Changing only the title leaves the
match intact; an explicit personal edition label does not edit the shared release.
A failed edition lookup disables saving until it can be reloaded. Conflicting or
uncertain saves require **Reload copy** and review, without automatic retries.

**Advanced: catalog matching** is closed by default and loaded only after it is
opened. It retains the separate catalog/release creation and revision-checked
**Save catalog match** workflow. Matching preserves personal title/edition labels.
Similar names remain distinct. **Edition not specified** removes a matched release
with history retained; it does not erase a personal label. Reloading catalog data
alone cannot unlock an uncertain copy. Catalog editing/deletion, automated
matching, valuation, real imports and production recovery remain
out of scope. The worker has a separate offline synthetic backup workflow. The separate local
progress dashboard is unchanged.

## Run locally with synthetic data

Follow [owner setup](../../docs/owner-access.md) before starting Compose. Pass both
`.env` and ignored `.env.owner` on every Compose command. Only the web port is
published on loopback at the configured origin (default `http://127.0.0.1:3000`).
API and database ports are internal. Apply migrations before starting the app.
Use synthetic data only.

Inside Compose, the web server reads `RELICRAT_API_URL=http://api:8000` at runtime.
For a host-run web server it defaults to `http://127.0.0.1:8000`; set the variable
only in the server environment when using another trusted internal API origin.
It must be an HTTP(S) origin without credentials, path, query or fragment. It is
never a `NEXT_PUBLIC_` browser setting. Browser code uses relative URLs.

Compose mounts `media_data` at the API's `MEDIA_ROOT`. Recreating an API container
preserves its photos, provided its matching PostgreSQL volume is preserved too.
`docker compose down --volumes` **destroys both database and photo volumes**.
An existing container's unmanaged media is not copied into this new volume;
stop writers and preserve/reconcile any previous files before changing mounts.
This is storage wiring, not backup/recovery, retention, encryption, or migration
of existing data. The supported development trial uses synthetic records only.

## Request boundary

Only inventory create/list/get, reconciliation and movement actions/history,
photo upload/list/download, storage create/list/get and the fixed catalog category/item/release lookup/create
paths are forwarded.
UUID path segments and supported methods are allowlisted; clients cannot choose
upstream hosts or arbitrary API paths. Query strings remain literal and the API
retains validation authority. No redirect is followed.

Every request requires the actual Host and protocol to match `RELICRAT_WEB_ORIGIN`.
POST additionally requires an exact matching Origin and JSON content type except for multipart photo uploads. Browser `fetch` supplies this
origin; missing/null/cross-origin values receive 403. Forwarded host headers are
not trusted. These checks supplement the owner session and block cross-site form uploads.
A reverse proxy requires deliberate end-to-end testing at its configured origin.

The route reads at most 64 KiB of JSON or 16 MiB of multipart body, regardless
of Content-Length. The API independently validates image bytes and its existing
15 MiB image limit. Multipart bytes and photo downloads are preserved exactly.
Only the recognized HttpOnly owner cookie is translated to an API Bearer header.
Unrelated cookies, browser Authorization and forwarded headers never reach the API.
The request content type is forwarded. Browser responses retain upstream status and
content type, with no-store/nosniff, without upstream cookies/internal headers.

API connection failures return 502; invalid operator configuration returns 503.
Upstream requests have a 30-second timeout. Saves are never automatically
retried: after an uncertain outcome, refresh and inspect the inventory/history
before deciding whether to retry. There is no idempotency key or per-user
concurrency/rate/memory budget. Production limits, hardened network access, catalog editing and automated matching remain separate work.

## Checks

Node 22+ and npm, using the committed lockfile:

```sh
cd apps/web
npm ci
npm test
npm run lint
NEXT_TELEMETRY_DISABLED=1 npm run build
```

`npm test` uses Node's built-in test runner and a disposable loopback HTTP
upstream. It covers allowlisted paths, origins, bounded/interrupted requests,
header isolation, errors/redirects, JSON/multipart bodies and exact binary bytes.
No live collection API is used by these boundary tests.

On the dedicated `relicrat-worker` Docker engine, from a scoped source checkout:

```sh
sh scripts/test-web.sh
```

This test accepts no custom target/project/database. It builds the production
web/API images, runs Node tests and TypeScript checks under Node 22, migrates a
fresh PostgreSQL 17 tmpfs database, and exercises the built Next.js route through
FastAPI with synthetic inventory, photo, nested storage, movement/history, literal
search, rejected cross-site writes and body limits. It recreates the API
container and verifies the same UUID/state/history and exact photo bytes from
the media volume. It does not drive a browser UI or prove backup/restore.

The stack has no published ports and an internal runtime network. A unique
project owns its media volume, containers, images, network and disposable build
metadata. Ordinary exits/signals remove only these resources; SIGKILL, a crash,
or Docker failure may require cleanup by the logged project name. Base images
and shared Docker build cache are retained. The test is not a deployment.


## Browser verification

Playwright is a test-only dependency: Node HTTP tests cannot verify selection,
keyboard focus, asynchronous read races and form recovery. No component library
or application runtime dependency was added. Use a modern Chromium installation
(`npx playwright install chromium`), or set PLAYWRIGHT_CHROMIUM_EXECUTABLE to an
existing test browser. Tests create isolated browser contexts, without your
regular browser profile.

Use a fresh disposable worker stack from `infra/docker/compose.web-test.yaml` with
its public synthetic owner fixture. Set `RELICRAT_TEST_WEB_ORIGIN` to the exact
loopback URL served by `scripts/private-preview.py`. The browser runner signs in
through the actual owner endpoint before intercepting domain fixtures. It needs a
running API/session database even for fixture cases. Never use a collection app.

```sh
RELICRAT_TEST_WEB_URL=http://127.0.0.1:TEST_PORT RELICRAT_REAL_UI_TEST=1 npm run test:browser
```

By default, domain API calls in fixture scenarios are intercepted with clearly
synthetic in-memory fixtures. These cover empty/error/no-match states, title and
notes intake, duplicate in-flight submission, photo failure/size validation,
immediate nested storage/movement, pagination, stale revisions, delayed reads,
unreadable/network errors, escaped text, keyboard focus and mobile overflow.
The separately guarded real-stack scenario is skipped unless
RELICRAT_REAL_UI_TEST=1. It refuses writes to a nonempty inventory. Run it only
against the dedicated disposable stack, never a collection app. Set
RELICRAT_TEST_WEB_URL to its loopback bridge when using the remote worker.

For the verified operator run, a temporary loopback bridge relayed only test
HTTP requests through the existing two-hop SSH helper into a fresh no-port worker
container. The test drove actual Chrome → production Next.js → FastAPI →
PostgreSQL/media, then reloaded the page and checked exact photo bytes and storage
history. The versioned `scripts/private-preview.py` helper provides this limited synthetic
SSH preview access; no NAS TCP-forwarding settings changed. It and the synthetic
stack were removed after verification. A usable hands-on trial requires a
separately started private preview with synthetic data.

## Album setup

Set up your collection is optional. Enable Albums, choose the default entry type,
adjust suggested Artist, Format, Edition/pressing and Notes fields, then preview
and Save setup. Back/cancel do not save; Skip for now keeps generic entry.
Collection settings reopens the same flow. Only Albums and Other have implemented
entry flows today. Photos and storage remain optional actions after saving.

The native type dropdown allows a one-off Album without changing the owner's
default. Album entry requires only Album title. Artist and format are bounded,
optional personal text; no album lookup, automatic title parsing, catalog creation
or ownership inference occurs. A nonempty draft must be explicitly discarded
before changing its type. Saved rows display Artist — Album when an artist is
present; search matches either, including previously hidden observations.

Settings affect new-entry visibility only. Saved artist, format and edition remain editable on existing copies even after
hiding a field or changing type. Existing notes remain visible as before. Preferences survive
browser changes and session expiry. If settings cannot be read, the owner can
explicitly choose generic entry without overwriting preferences. Conflicting or
uncertain setup writes require reload/review before another save.

This feature requires API, migration0006 and web together. No upgrade is implied
by building the web image alone. The downgrade loses new metadata/preferences and
record-only audit events; never automatically use it to roll back a live UI.

## Comics

Comics can be enabled alongside Albums in the same optional setup, with its own
field choices and default. Entry requires only Series/title; issue number,
publisher, edition/cover and notes are optional. The `comic.json` definition drives
field order/labels/controls. Issue is text, preserving fractions and leading zeroes.
Publisher suggestions come from saved Comics, not an external catalog. A saved
copy displays Series #Issue when an issue was entered. Photos/storage and optional
catalog matching retain the existing flow. Type changes and hidden fields never
erase saved observations; edits use the existing Save details transaction/history.
API/schema/web rollout and verified recovery are required before using this flow.

The collection list has a Show collection type selector (All types, Albums,
Comics, Other) labelled from the bundled definitions. Search and pagination stay
within the selection; a type change starts at page one. It is page-local browsing
state, independent of intake/default type, open-copy edits and setup preferences.
Clearing search retains the selected type. Saving a different type retains the
filter and explains how to show the saved find. Nothing is retagged automatically.

## CLZ and Discogs CSV intake

**Import CSV** opens an inline upload/preview/confirm flow. Choose CLZ Comics or
Discogs Albums and a UTF-8 comma-separated CSV (up to 4 MiB). Preview displays
counts, field mapping, ten sample records, duplicate-ID advisories and errors;
all rows must be valid before the explicit acknowledgement and Import action.
Nothing is imported by selecting a file or previewing it. Existing draft intake,
type filters and owner preferences remain separate.

Imports retain every original column in private database provenance. Browse
paginated **Import history** and **View retained fields**, or open the associated
physical copy. File contents and filenames are never written into the repository.
Storage labels, prices, grades and external IDs stay source data rather than
silently becoming locations, financial valuations or catalog matches. Exact-file
retries add no copies; changed exports can duplicate existing items. There is no
cross-export reconciliation or batch undo in this first increment.

The fixed proxy accepts bounded `text/csv` only for preview/commit, keeps the
existing same-origin/owner-cookie boundary, and forwards only to the configured
private API. The UI never evaluates cells. Uncertain saves clear confirmation and
require a fresh preview, which can identify a completed exact-file batch.
Requires migration `0009_csv_import` and matching API/web images.

## Grouped collection browsing

**Grouped collection** is the default browse view. All types first shows counts
by collection type. Albums then groups by saved artist; Comics groups by saved
series/title. Choose a group to open its independently paged physical copies.
Group summaries are paginated on the server with counts covering the full
matching collection. Opening one group replaces the previous open group. Missing
artists/series have an explicit group and case distinctions remain separate;
grouping never makes a catalog match or merges copies. The grouping metadata lives
beside the entry definitions in the collection-type JSON configs.

**Individual copies** retains the previous flat browsing mode. Other is always
shown individually. Search, collection type and the separate **Storage location**
filter apply to both views. Storage matches copies assigned directly to that
location; CSV box/folder labels still need a reviewed assignment before they can
match. Location options can be explicitly loaded beyond the first 100. Filter
changes reset browsing pages, cancel obsolete reads and preserve intake/edit
drafts. The choice is page-local and does not change intake defaults or settings.

The dedicated generated-volume browser coverage runs with an owned disposable
loopback URL using `node --test apps/web/tests/groups.browser.mjs`. The existing
inventory/import browser tests explicitly select Individual copies for their
original copy-workflow coverage. Do not point test commands at the private trial.

## Compact collection workspace

Intake sits openly on the workspace. Individual-copy pages group Albums, Comics,
Movies and Other finds with counts labelled “on this page”; these are not whole
collection totals. Rows keep title and optional edition together, with Location
assigned or Unassigned alongside. Notes remain in the selected record. Existing
server groups, search, type/storage filters and pagination retain their semantics.
