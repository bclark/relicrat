# RelicRat 🐀

**Know what you have. Know where it is. Know its story.**

RelicRat is a self-hosted inventory and collection-management platform for physical collectibles. It is designed for collectors who want to catalog individual items, keep track of where they live, understand their provenance and value, and see what is missing from a collection—without surrendering control of their data.

> **Project status:** Early development. The first browser workflow supports synthetic intake, photos, storage, and search. It is **not ready for real collection data or production use**; identification UI, authentication and production recovery remain unfinished.

## What we're building

- **A home for every physical copy.** Catalog identities, editions, and individual owned copies are distinct. Each copy can have its own condition, grading, photos, location, acquisition details, and history.
- **Fast cataloging.** Start with a photo or short description, then identify and reconcile items later. Planned workflows include barcode scanning, AI-assisted recognition, and reviewable bulk imports.
- **Collection Packs.** Portable, versioned Markdown/YAML definitions describe categories, checklists, metadata, and completion rules. Packs never imply ownership.
- **Organize and find things.** Nested storage locations, QR labels, manual collections, smart collections, and unified search across owned items, wishlists, listings, and missing items.
- **Understand your collection.** Optional valuation providers, evidence and confidence, price history, completion tracking, and wishlists.
- **Sell without losing history.** Draft listings, multi-item lots, marketplace integrations where available, and recorded sale transactions.
- **Own your data.** Run locally on a NAS or server, use PostgreSQL and filesystem-backed media, and maintain verified backups and portable exports.

These are **product goals**, not implemented features.

## Design principles

1. **Inventory is authoritative.** AI, marketplaces, and external catalogs propose changes; the collector reviews them.
2. **One object, one identity.** A physical copy retains its UUID and history even when identification improves.
3. **Catalogs are shared, ownership is personal.** Multiple packs may reference the same canonical item.
4. **Local-first deployment.** Self-hosting, backup, privacy, and data portability are fundamental.
5. **Small, testable increments.** Build an end-to-end workflow before expanding into integrations.
6. **Explain uncertainty.** Unknown value is not zero; tentative matches and disputed metadata remain visible.

## Architecture

| Layer | Planned stack |
| --- | --- |
| Web | Next.js, React, TypeScript, responsive PWA |
| API | Python, FastAPI, Pydantic |
| Persistence | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Background work | Python worker/scheduler; queue implementation to be selected |
| Media | Filesystem storage on the host/NAS |
| Deployment | Docker Compose |
| AI | Configurable local or cloud providers, opt-in where appropriate |

A **modular monolith** keeps domain boundaries clear without premature microservices.

### Repository layout

```text
apps/
  api/                  FastAPI service and Alembic migrations
  web/                  Next.js frontend
packages/
  collection-packs/     Pack schema and examples
infra/
  docker/               Docker build definitions
docs/
  architecture/         System design and domain model
  decisions/            Architecture decision records
scripts/                Developer utilities
compose.yaml            Local services
.env.example            Configuration template (no secrets)
```

## Getting started (development)

**Prerequisites:** Docker Engine with Compose v2, and Git. Local Python/Node toolchains are optional if using containers.

```bash
git clone https://github.com/bclark/relicrat.git
cd relicrat
cp .env.example .env
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up --build
```

Development URLs (synthetic data only):

- Web: http://localhost:3000
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

The web server forwards allowlisted `/api/v1/...` requests to the private API.
Photo files use a dedicated named media volume; apply migrations before API use.
See [browser/API setup and verification](apps/web/README.md).

**Development only:** The example Compose setup uses local credentials and publishes ports on the host. Do not expose it to the internet or store real collectibles data in it until authentication, secrets, and backup/recovery have been hardened.

## First milestone

The first vertical slice is intentionally narrow:

1. Add a provisional owned copy with a description or photo.
2. Identify/link it to a canonical catalog item and optional release.
3. Assign a storage location.
4. Find it using search.
5. Back up the database and media.

The API supports provisional copies, photos, and manual catalog/release reconciliation
with revision checks and retained identification history, nested storage locations,
and explicit revision-checked copy movements with retained history. Literal text
search finds copies by provisional information and linked catalog/release names.
See the [inventory API contract](apps/api/INVENTORY.md).
The add-first web screen supports provisional intake, photo upload/viewing, nested
storage creation, explicit location changes and literal search. Catalog CRUD and
identification UI, authentication and production backup remain unimplemented;
an [offline operator backup/restore workflow](docs/backup-restore.md) is available
for synthetic data on the dedicated worker, alongside the disposable recovery
harness. Production recovery remains unfinished. The complete
vertical slice is not delivered yet.

## Documentation

- [Project dashboard](docs/project-dashboard.html) — open the self-contained HTML in a browser for completed work, next steps and recorded validation. The snapshot is updated manually after merged milestones.
- [Architecture overview](docs/architecture/overview.md)
- [ADR 0001: Modular monolith and stack](docs/decisions/0001-modular-monolith.md)
- [Development harness and Symphony pilot](docs/harness.md)

The architecture documentation records intended behavior. It is not a claim that integrations or database constraints are already implemented.

## Contributing and project status

This repository is currently a private, early-stage project. Development is organized into small pull requests. Prefer focused changes, tests for domain invariants, and migration review before changing persistent data.

No license has been selected. Until one is added, do not assume permission to redistribute or reuse this code outside applicable law.

## Roadmap

| Phase | Focus |
| --- | --- |
| 1 — Foundation | Inventory, canonical identities, storage, search, imports, backups |
| 2 — Intelligence | AI-assisted entry, Collection Packs, completion goals |
| 3 — Valuation & commerce | Pricing evidence, listings, wishlists, notifications |
| 4 — Extensions | Shared packs, richer integrations, optional native clients |

**RelicRat** is the working project name. Branding and mascot design can evolve without changing the underlying data model.
