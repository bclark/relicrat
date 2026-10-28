# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

RelicRat is for a collector managing physical collectibles on their own infrastructure.
The separate local project progress report is for the project owner reviewing a dated development snapshot.

## Product Purpose

Keep logical catalog items, releases and individual owned copies distinct; preserve identity, provenance and collection data as identification improves.

## Operating Context

The repository uses FastAPI, PostgreSQL, Alembic and Next.js. Development runs on an isolated worker on the owner's NAS. Symphony has completed four supervised implementation tasks; work is handed off through human-reviewed pull requests. The current application is a synthetic collection trial: authentication and production backup/recovery are unfinished. Never use real collection data in this development workflow.

## Capabilities and Constraints

The API supports provisional copy intake, photos, catalog category/item/release creation and lookup, manual revision-checked catalog/release reconciliation with retained identification history, nested storage locations, revision-checked copy movements with retained history, and literal text search across provisional information and linked catalog/release names.

The working web screen supports add-first provisional intake with a title or notes, photo upload/viewing after saving, nested location creation, explicit location assignment/unassignment, movement history, and paginated search/browsing of physical copies. The selected record now supports explicit catalog search/selection, an optional release, separate category/item/release creation, revision-checked Save identification, and retained identification history. Similar names remain separate. Catalog-only identification removes a previous release while preserving the physical copy UUID, provisional information, photos, storage and history. Manual identification is not a verified match. The earlier add-first and direct-build choices applied to that screen task; they do not establish a standing build-path or configuration preference.

Copy, photo, catalog creation, identification, location creation and copy movement save separately. Creating a catalog entry or release only selects it for a later explicit identification save; it never creates ownership or silently links a copy. Creating a location does not move the copy. Drafts remain page-local; reloads can lose them. Saves are never retried automatically. Unconfirmed writes and revision conflicts require reload and review. Catalog editing/deleting/merging, automatic matching, authentication and production recovery remain unfinished. An offline operator backup/restore workflow exists for synthetic data on the dedicated worker. That workflow and the disposable database/media recovery rehearsal are development evidence, not production recovery support. The complete first vertical slice is not yet delivered.

The separate frozen [progress report](docs/project-dashboard.html) records history through PR #14; it is manually maintained and does not reflect the current working screen. Its [historical design record](docs/design/project-dashboard.md) remains scoped to that report. Root DESIGN.md describes the current inventory app implementation, without establishing a permanent brand or user palette preference.

## Evidence on Hand

README.md, docs/architecture/overview.md, docs/harness.md, apps/api/INVENTORY.md and the current web implementation ground capability claims. The catalog identification extension starts from merged main 0fd90c424c50ebfe23f29cc3d88d394fa0e368df, including the offline backup work from PR #24.

Current catalog extension validation: 90 API tests passed with zero skips and a full migration downgrade/upgrade round trip; 11 Node proxy tests passed with zero skips; production Next.js build/typecheck and worker `sh scripts/test-web.sh` passed. The final browser run passed 10 scenarios with zero skips, including real Chrome against the production web/API/PostgreSQL/media stack: category, item and release creation, two reconciliations, and release removal preserved the same copy UUID, photo and storage. No dependency or migration was added. API, browser, stack and detector logs are local evidence under `/Users/bryanclark/Developer/relicrat/.harness-results/catalog-identification/` (`api.log`, `browser-final.log`, `stack.log`, `detector.json`). These checks do not prove production readiness; backup/restore was not rerun for this catalog extension.

The manual visual detector ran once and returned no findings. Valid final full-page production captures are .impeccable/review/desktop.png (1440 × 2953) and mobile.png (390 × 3644), using synthetic records. Exact PNG photo bytes were checked in the real browser scenario. A bounded visual fix batch removed redundant single-page catalog navigation, applied the incumbent radio accent and corrected footer capability text. The fresh independent finish review requested a documentation correction; its verdict pass scored that sole fix resolved with disposition ship. No approved comp, shipping illustration or icon assets are part of this surface; user photos are data. DESIGN.md and .impeccable/design.json remain the incumbent system for this ordinary extension.

Historical evidence: the initial inventory web screen started from 299aeaffb9cb6b4a6eb78e9e977314b6d4d09810 and reported 10 Node boundary tests, 7 browser cases, a production build/typecheck and a disposable production stack passing, with an independent ship review. That verdict applies to the earlier screen. The older 43 API result, migration round trips and synthetic recovery damage controls, and PR #19's 86 API tests remain dated evidence rather than the current catalog validation. PR #24's offline synthetic operator backup evidence is recorded separately in docs/harness.md and docs/backup-restore.md.

## Product Principles

- Prefer evidence over implied completion.
- Preserve physical-copy identity, data and history.
- Make uncertainty, conflicts and save boundaries explicit.
- Keep progress-report snapshots separate from product capability claims.

## Open Decisions

Permanent branding and production deployment choices remain open. Catalog editing/deleting/merging, automatic matching, authentication and production recovery still require implementation and verification. The identification extension has completed its finish review and awaits human PR review/merge; it is not yet deployed to the existing trial.
