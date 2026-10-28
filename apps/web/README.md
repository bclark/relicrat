# Browser/API connection (development only)

The add-first inventory screen supports provisional copies, photos, explicit
storage changes, and inventory search. Use synthetic records and test photos only.
The server exposes the existing inventory/storage API at `/api/v1/...` on the same
origin behind single-owner authentication. This remains a synthetic development deployment.

## First screen

A title or notes creates one provisional physical copy. Save it first, then use
its record to upload JPEG/PNG/WebP photos and choose storage. Creating a storage
location does not move the copy: use Save location explicitly. Selecting Unassigned
and saving removes its current assignment while retaining movement history.

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

Manual identification now searches or creates a catalog entry, optionally selects
a release, and explicitly saves on the same copy with retained history. Creation
never implies ownership or links the copy by itself. No release specified removes
a previous edition. Similar names remain separate, with references shown for
disambiguation. Stale or uncertain writes require Reload copy and review; catalog
reload alone cannot unlock an uncertain copy. Catalog editing/deletion, automated
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
explicit nested storage/movement, pagination, stale revisions, delayed reads,
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
