# Browser/API connection (development only)

The inventory screen is still a placeholder. Its server now exposes the existing
inventory/storage API at `/api/v1/...` on the same origin as the web app. This
preparatory route is not authentication or a production deployment.

## Run locally with synthetic data

From the repository root, after copying `.env.example` to `.env`:

```sh
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up --build
```

All development ports remain bound to host loopback. Web is on
`http://localhost:3000`; the upstream API is also available locally on port 8000.
Do not expose these services or enter real collection data. Apply migrations
explicitly before API use; startup does not migrate an existing database.

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
photo upload/list/download, and storage create/list/get paths are forwarded.
UUID path segments and supported methods are allowlisted; clients cannot choose
upstream hosts or arbitrary API paths. Query strings remain literal and the API
retains validation authority. No redirect is followed.

POST requires `Origin` to exactly match the request scheme and actual Host header,
and JSON
content type except for multipart photo uploads. Browser `fetch` supplies this
origin; missing/null/cross-origin values receive 403. Forwarded host headers are
not trusted. This also handles Next.js normalizing its internal URL to localhost. This blocks cross-site
form uploads too. Do not treat this check as user authentication, or assume a
reverse proxy with a different public origin works without deliberate testing.

The route reads at most 64 KiB of JSON or 16 MiB of multipart body, regardless
of Content-Length. The API independently validates image bytes and its existing
15 MiB image limit. Multipart bytes and photo downloads are preserved exactly.
No browser cookies, Authorization or forwarded headers go to the API; only the
request content type is forwarded. Browser responses retain upstream status and
content type, with no-store/nosniff, without upstream cookies/internal headers.

API connection failures return 502; invalid operator configuration returns 503.
Upstream requests have a 30-second timeout. Saves are never automatically
retried: after an uncertain outcome, refresh and inspect the inventory/history
before deciding whether to retry. There is no idempotency key or per-user
concurrency/rate/memory budget. Authentication, production limits, hardened
network access and the inventory screen remain separate work.

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
