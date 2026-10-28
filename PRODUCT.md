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

The API supports provisional copy intake, photos, manual revision-checked catalog/release reconciliation with retained identification history, nested storage locations, revision-checked copy movements with retained history, and literal text search across provisional information and linked catalog/release names.

The first working web screen supports add-first provisional intake with a title or notes, photo upload/viewing after saving, nested location creation, explicit location assignment/unassignment, movement history, and paginated search/browsing of physical copies. The owner explicitly chose adding a find first and directly building this working screen. This is a task-specific choice, not a standing build-path or configuration preference.

Copy, photo, location creation and copy movement save separately. Creating a location does not move the copy. Drafts remain page-local; reloads can lose them. Saves are never retried automatically. Unconfirmed writes and revision conflicts require reload and review. Identification and catalog editing UI, authentication and production recovery remain missing. A synthetic database/media recovery rehearsal is development evidence, not production backup support. The complete first vertical slice is not yet delivered.

The separate frozen [progress report](docs/project-dashboard.html) records history through PR #14; it is manually maintained and does not reflect the current working screen. Its [historical design record](docs/design/project-dashboard.md) remains scoped to that report. Root DESIGN.md describes the current inventory app implementation, without establishing a permanent brand or user palette preference.

## Evidence on Hand

README.md, docs/architecture/overview.md, docs/harness.md, apps/api/INVENTORY.md and the current web implementation ground capability claims. Source base for this working screen: 299aeaffb9cb6b4a6eb78e9e977314b6d4d09810.

Current branch validation reported by the implementing agent: 10 Node boundary tests and 7 browser cases passed with no skips; production build/typecheck and a real disposable stack with no published ports passed. The independent finish review returned ship with no material findings or fixes. Full-page production captures are recorded in .impeccable/review/desktop.png and mobile.png; they use synthetic records and a synthetic PNG photo fixture. No approved comp, shipping illustration or icon assets are part of this surface; user photos are data.

The older 43 API test result, migration round trips and synthetic recovery with missing/corrupt-media controls belong to historical evidence. The latest merged search/storage API evidence is 86 passing tests from PR #19; that API suite was not rerun here. API pytest and the backup suite were not rerun for this web-screen change. Current web checks do not replace those suites or prove production readiness.

## Product Principles

- Prefer evidence over implied completion.
- Preserve physical-copy identity, data and history.
- Make uncertainty, conflicts and save boundaries explicit.
- Keep progress-report snapshots separate from product capability claims.

## Open Decisions

Permanent branding and production deployment choices remain open. Catalog identification UI, authentication and production recovery still require implementation and verification.
