<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/wordmark-reversed-PROPOSED.svg">
    <img src="docs/brand/wordmark-PROPOSED.svg" alt="RelicRat" width="360">
  </picture>
</h1>

<p align="center"><strong>Modern collecting. Timeless stories.</strong></p>

<p align="center">A self-hosted home for your comics, albums and other finds.<br>Know what you have, where it lives, and the story behind each copy.</p>

<p align="center">
  <a href="#what-works-today">Features</a> ·
  <a href="#try-it-locally">Local setup</a> ·
  <a href="#documentation">Documentation</a> ·
  <a href="#license">AGPL-3.0-only</a>
</p>

<p align="center">
  <img src="docs/brand/mascot-vinyl-v2-PROPOSED.png" alt="RelicRat’s collector mascot carefully holding a record by its edges, wearing a burgundy waistcoat and leather satchel." width="260">
</p>

> **Early development.** RelicRat is an experimental single-owner application, not a production-ready deployment. The setup below is for private local testing with synthetic data. Production hardening and recovery remain unfinished.

## What works today

Start with a title. Add the details when you have them.

| Your collection | What you can do |
| --- | --- |
| **Comics, albums and other finds** | Add a physical copy with just a title; attach notes, an edition label and photos later. Albums support artist and format; Comics support series, issue and publisher. |
| **CLZ and Discogs imports** | Upload a CSV, review the mapping and samples, then explicitly import. Original fields stay attached to each copy; exact-file retries do not add duplicates. |
| **Review imported storage** | Map a CLZ box label to a physical location after previewing its copies. Existing placements and earlier manual unassignments stay intact. Discogs folders remain source information. |
| **Movies** | Title-first entry, optional format/studio/packaging, title groups and a reviewed Blu-ray.com CSV preset. One row stays one owned item; original metadata and conflicting barcodes remain source evidence. [Movie guide](docs/movies.md). Requires migration 0013 and a reviewed rollout. |
| **Barcode intake** | Read UPC/EAN barcodes on-device, explicitly attach a reading, then save it with a find. Search saved barcodes and retain corrections in copy history. Album lookup can query configured MusicBrainz suggestions, review selected fields and fill a draft before the final save. Provider availability and private outbound access are separate rollout checks. [Trial guide](docs/barcode-scanning.md); [provider configuration and read-only overrides](docs/barcode-lookup.md#swap-with-an-operator-owned-config-mount). |
| **Groups that make sense** | Browse Comics by series and Albums by artist, with counts and paginated copies. Search and filter by collection type or assigned storage location. |
| **A place for every copy** | Create nested locations, assign a copy to a box or shelf, and retain its movement history. |
| **Details without losing history** | Edit personal copy details or optionally match a shared catalog item and edition. Physical copies keep their own identities, photos and history. |
| **A look of your own** | Preview and apply themes for colors, fonts, spacing, corners and density. Import/export theme JSON or use the authoring guidelines with your chosen AI tool. |

Single-owner sign-in protects the inventory, source records and photos. PostgreSQL
stores the records; a separate media volume holds uploaded images.

Imported storage labels remain source information until you assign locations.
Changed CSV exports can add duplicates: exact-file protection is not automatic
reconciliation across exports. There is no embedded AI service or automatic
catalog matching.

## One collectible. Several editions. Your individual copies.

RelicRat keeps three things separate:

- **Catalog item:** the logical collectible, such as an album.
- **Release:** a particular edition or variant, such as a CD release.
- **Owned copy:** your individual physical object, with its own photos, location and history.

You can save a find before identifying its catalog item or edition. Grouping by
artist or series helps you browse; it never merges your physical copies. Unknown
values remain unknown, and catalog information never silently creates ownership.

## Try it locally

You’ll need **Git, Python 3.11+ and Docker Engine with Compose v2**. Containers
provide the API and web runtimes; local Node.js is optional.

```bash
git clone https://github.com/bclark/relicrat.git
cd relicrat
cp .env.example .env
python3 scripts/configure-owner.py --origin http://127.0.0.1:3000 --allow-loopback-http
docker compose --env-file .env --env-file .env.owner up -d db
docker compose --env-file .env --env-file .env.owner run --build --rm api alembic upgrade head
docker compose --env-file .env --env-file .env.owner up --build
```

Open [localhost:3000](http://127.0.0.1:3000) and sign in with the owner password
you configured. Add a made-up find, try a photo and storage assignment, or preview
a synthetic CSV import.

Only the web server binds to host loopback. API and PostgreSQL services stay on
the internal Compose network; API documentation routes are disabled. Images use
a dedicated named media volume. Apply migrations before starting the app.

**This is a development setup.** It uses development database credentials; do not
expose it to the internet or use it for real collection data. See
[owner setup and private access](docs/owner-access.md) for configuration and
[the web guide](apps/web/README.md) for browser/API details.

## Built to stay in your hands

RelicRat is a modular monolith: one application with clear boundaries, rather
than a collection of separate services for each feature.

| Part | Stack |
| --- | --- |
| Web | Next.js, React, TypeScript |
| API | Python, FastAPI, Pydantic |
| Data | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Photos | Filesystem-backed media volume |
| Local runtime | Docker Compose |

```text
apps/api/              API, domain services, models and migrations
apps/web/              Web interface and private API gateway
packages/              Collection-pack and theme authoring guidelines
docs/                  Architecture, decisions, operator guides and brand assets
scripts/               Development checks and operator utilities
compose.yaml           Local development services
.env.example           Configuration template; no secrets
```

The repository includes an offline operator backup/restore workflow and disposable
recovery checks. These are documented development procedures, not a finished
production recovery product. Keep credentials, collection exports and photos out
of Git.

## What comes next

The longer-term direction includes:

- Reviewed mapping of imported storage labels, and reconciliation across revised exports.
- Barcode intake, reviewable identification suggestions and Collection Packs.
- Condition and grading workflows, valuation evidence and price history.
- Wishlists, sales and disposition workflows that preserve provenance.

These are plans, not implemented capabilities. See the
[architecture overview](docs/architecture/overview.md) for the intended boundaries.

## Documentation

| Start here | Go deeper |
| --- | --- |
| [Browser features and verification](apps/web/README.md) | [Inventory API contract](apps/api/INVENTORY.md) |
| [Owner setup and private access](docs/owner-access.md) | [Architecture decisions](docs/decisions/) |
| [Development harness and Symphony boundaries](docs/harness.md) | [Offline backup and restore](docs/backup-restore.md) |
| [Theme authoring guidelines](packages/themes/AUTHORING-PROMPT.md) | [Brand artwork and status](docs/brand/README.md) |

The [project dashboard](docs/project-dashboard.html) is a manually maintained
snapshot; it can lag behind merged work. Architecture documents describe design
intent and do not establish that a planned feature is implemented.

See the shared [UI and brand context](docs/design/README.md) before changing the interface.

## Contributing

RelicRat is public and open source. Focused pull requests are welcome. Read
[AGENTS.md](AGENTS.md), trace the affected workflow, and include relevant tests
for domain invariants, security boundaries and migration behavior. Keep proposed
features separate from shipped capabilities.

## License

Copyright (c) 2026 Bryan Clark.

Except where otherwise noted, RelicRat is licensed under the
[GNU Affero General Public License v3.0 only](LICENSE) (`AGPL-3.0-only`).
You may use, modify and redistribute it, including commercially, under that
license. If you distribute a modified version, or let users interact with a
modified version over a network, you must provide the corresponding source code
under the license's terms. See [LICENSE](LICENSE) for the full terms.

Third-party components retain their own licenses. The software license does not
change ownership of your collection records or uploaded media.
