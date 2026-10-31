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

The repository uses FastAPI, PostgreSQL, Alembic and Next.js. Development runs on an isolated worker on the owner's NAS. Symphony has completed four supervised implementation tasks; work is handed off through human-reviewed pull requests. The current application is a synthetic collection trial. PR #25 catalog identification is merged and deployed to the existing trial. This branch implements single-owner access and awaits human PR review/merge; the existing trial has not been upgraded with authentication. Private credential setup and an explicit trial upgrade must follow merge, preserving its existing data volumes. Production backup/recovery and public ingress remain deferred. Never use real collection data in this development workflow.

## Capabilities and Constraints

The API supports provisional copy intake, photos, catalog category/item/release creation and lookup, manual revision-checked catalog/release reconciliation with retained identification history, nested storage locations, revision-checked copy movements with retained history, and literal text search across provisional information and linked catalog/release names.

The working web screen supports add-first provisional intake with a title or notes, photo upload/viewing after saving, nested location creation, location assignment/unassignment saved immediately on selection, movement history, and paginated search/browsing of physical copies. The selected record now supports explicit catalog search/selection, an optional release, separate category/item/release creation, revision-checked Save catalog match under Advanced, and retained identification history. Similar names remain separate. Catalog-only identification removes a previous release while preserving the physical copy UUID, provisional information, photos, storage and history. Manual identification is not a verified match. The earlier add-first and direct-build choices applied to that screen task; they do not establish a standing build-path or configuration preference.

Copy, photo, catalog creation, identification, location creation and copy movement save separately. Creating a catalog entry or release only selects it for a later explicit identification save; it never creates ownership or silently links a copy. Creating a location does not move the copy. Choosing a location immediately saves a revision-checked move and confirms the destination beside the selector; pending or failed moves never appear as confirmed. Drafts remain page-local; reloads can lose them. Saves are never retried automatically. Unconfirmed writes and revision conflicts require reload and review. Catalog editing/deleting/merging, automatic matching and production recovery remain unfinished. An offline operator backup/restore workflow exists for synthetic data on the dedicated worker. That workflow and the disposable database/media recovery rehearsal are development evidence, not production recovery support. The complete first vertical slice is not yet delivered.

This branch adds one owner password provisioned privately through SSH, using salted standard-library scrypt. Guests sign in before accessing inventory, catalog, storage, history, uploads or photo downloads. Opaque sessions expire after 12 hours; the browser holds a host-only HttpOnly, SameSite=Strict cookie and PostgreSQL stores only token hashes. HTTPS cookies are Secure and __Host-prefixed; the HTTP exception is explicitly limited to loopback SSH preview. Sign out revokes the server session before clearing its cookie; a failed revocation retains the cookie and shows an error. Password or session-secret rotation invalidates prior sessions once all API processes restart with the new settings. Restore promotion requires a fresh session secret.

The Next.js gateway pins the configured browser origin, rejects cross-origin writes and translates only the owner cookie to an internal Bearer header. Browser JSON and localStorage never receive tokens. API and PostgreSQL remain private with no published host ports; missing configuration fails closed. The database serializes a global failed-login guard. There is no signup, SSO, MFA, email reset or multi-user permission model. Password reset remains private SSH operator work. Authentication does not establish hardened hosting, public ingress, off-host backup or production recovery.

The separate frozen [progress report](docs/project-dashboard.html) records history through PR #14; it is manually maintained and does not reflect the current working screen. Its [historical design record](docs/design/project-dashboard.md) remains scoped to that report. Root DESIGN.md describes the current inventory app implementation, without establishing a permanent brand or user palette preference.

## Evidence on Hand

README.md, docs/architecture/overview.md, docs/harness.md, apps/api/INVENTORY.md and the current implementation ground capability claims. Owner access is documented in [the setup and rotation runbook](docs/owner-access.md), [accepted ADR 0002](docs/decisions/0002-single-owner-access.md) and [the harness verification record](docs/harness.md#single-owner-access-verification-2026-10-28). This branch starts from merged main `1455b4eb04c3684e41209c12ce93f73e697c06fa` (PR #25). Migration 0004 adds only authentication tables, preserving collection rows; no runtime dependency is added.

Current owner-access validation: `python3 scripts/test-api-remote.py relicrat-worker` reported 97 passed, zero skips or expected failures, and 20 warnings, with a full migration downgrade to base and upgrade through 0004. Worker `sh scripts/test-web.sh` passed production build/typecheck, 19 Node tests with zero skips/failures, fresh migrations, authenticated HTTP smoke and exact photo persistence after API recreation. Host Node tests, TypeScript check and production Next.js build also passed. `RELICRAT_REAL_UI_TEST=1 npm run test:browser` passed 11 real-browser scenarios with zero skips/failures, covering guest/login/reload/logout/replay and the inventory/catalog workflow. Physical-copy UUID, photo bytes, storage and reconciliation history remained intact.

`python3 scripts/test-operator-backup.py` passed actual synthetic backup, writer restart, source destruction, fresh offline restore and independent fixture verification; all five damaged-bundle modes were rejected as expected and cleanup passed. Restores remain stopped without owner configuration. Operator unit checks reported 11 passed; Python compilation and `git diff --check` also passed. Local evidence is under `/Users/bryanclark/Developer/relicrat/.harness-results/owner-authentication/`: `api-final.log`, `stack.log`, `browser.log`, `recovery.log`, `script-tests.log` and `detector.json`. Early stack readiness and Compose configuration-hash failures were corrected before these final passing integrations, as recorded in docs/harness.md. These checks use synthetic data and do not prove production readiness.

The manual visual detector ran once and returned no findings (`[]`). The fresh independent finish review checked all four final captures, matched the incumbent UI and requested only factual PRODUCT.md corrections; this update addresses that documentation finding without another UI change. Valid final production captures are `.impeccable/review/desktop.png` (1440 × 2961), `mobile.png` (390 × 3652), `login-desktop.png` (1440 × 1050) and `login-mobile.png` (390 × 844). The mobile login capture was recaptured in a fresh fixed-size context after a resize artifact. No approved comp, new illustration or icon asset is part of this surface; user photos are data. DESIGN.md and .impeccable/design.json remain unchanged for this ordinary extension. Pre-existing build-path-unset metadata drift remains unrepaired; it does not establish a standing build preference.

Historical catalog evidence: the PR #25 identification extension started from main `0fd90c424c50ebfe23f29cc3d88d394fa0e368df`, including PR #24 offline backup work. It reported 90 API tests, a full migration downgrade/upgrade round trip, 11 Node tests, production build/typecheck and worker web checks, plus 10 real-browser scenarios, all with zero skips. Logs remain under `/Users/bryanclark/Developer/relicrat/.harness-results/catalog-identification/`. Its independent finish review reached disposition ship after a documentation correction. No dependency or migration was added for that catalog extension, and backup/restore was not rerun for that extension. That evidence and its older captures describe the catalog change, not owner access.

Historical evidence: the initial inventory web screen started from 299aeaffb9cb6b4a6eb78e9e977314b6d4d09810 and reported 10 Node boundary tests, 7 browser cases, a production build/typecheck and a disposable production stack passing, with an independent ship review. That verdict applies to the earlier screen. The older 43 API result, migration round trips and synthetic recovery damage controls, and PR #19's 86 API tests remain dated evidence rather than the current catalog validation. PR #24's offline synthetic operator backup evidence is recorded separately in docs/harness.md and docs/backup-restore.md.

## Product Principles

- Prefer evidence over implied completion.
- Preserve physical-copy identity, data and history.
- Make uncertainty, conflicts and save boundaries explicit.
- Keep progress-report snapshots separate from product capability claims.

## Open Decisions

Permanent branding and production deployment choices remain open. Catalog editing/deleting/merging and automatic matching still require implementation and verification. Public ingress, off-host backup and production recovery remain deferred. PR #25 catalog identification is merged and deployed to the existing synthetic trial. This owner-access branch awaits human PR review/merge; authentication is not deployed to that trial. After merge, a trusted operator must create private owner credentials and explicitly upgrade the trial with its existing volumes and a verified offline backup. The first vertical slice remains incomplete; real collection data is not authorized.


## Copy-first detail editing refinement (2026-10-29)

The owner completed the catalog exercise but still found the same-item/shared-
edition model confusing. The selected physical copy now starts with a prefilled
Title and optional Edition form. One Save details request updates those personal
labels atomically, preserving the copy UUID, creation time, media, storage,
disposition and all earlier history. Copy edits use independent revisions and
retain before/after history. Catalog matching moves into a closed Advanced
disclosure; it is optional and never creates ownership from ordinary edits.

Existing linked edition names prefill when no personal label exists. Title-only
edits keep that source; explicit labels stay personal and are not silently
changed by later matching. Failed/stale reads cannot fill another copy or save
an unavailable edition as unknown. Conflicting/uncertain writes require review
without retries. Migration 0005 and a verified recovery capture are required
before deployment. The current live trial remains on merged PR33 until review,
merge and rollout of this feature. No standing brand/build-path preference is
introduced; the incumbent visual system is retained.

## Records setup refinement (proposed implementation, 2026-10-30)

The owner approved a skippable collection setup with adjustable suggested fields,
starting with the complete Records path. The implementation adds durable owner
preferences, personal copy type/artist/format, adapted album entry, preview without
ownership writes, and settings that preserve hidden values. Only a title is needed
for new entry. Other remains generic; more specialized types and financial fields
are deferred. This feature is not deployed until review, merge, verified recovery
and an explicit migration0006/API/web rollout. Existing combined titles and their
physical-copy identities must not be rewritten automatically.

## Appearance authoring (implemented for review, 2026-10-31)

The owner selected visual themes for colors, body/heading fonts, section spacing,
corners and density, with manual controls and preview. AI assistance uses a prompt
or Markdown guidelines file describing the supported values. The app generates
that file from the current theme and JSON Schema; users provide it to their own AI
tool and import its JSON response. RelicRat makes no external AI request. A reusable
source guide lives at `packages/themes/AUTHORING-PROMPT.md`.

The inline Appearance editor inherits the incumbent interface. Draft changes stay
in an isolated sample until explicit apply, and edits invalidate preview. Both
manual/imported themes use strict bounded values and palette contrast checks.
Control targets stay at least 44 px, error styling remains fixed, and no custom
CSS, external fonts, layout/navigation or inventory changes are supported. One
active owner theme is durable server data with its own conflict revision.
Unconfirmed/stale saves require reload and review. Login retains default styling;
the saved appearance loads after authentication and can briefly flash from default.

Migration 0008 adds only appearance settings and refuses downgrade of customized
themes. This change has not rolled out to the live trial. Current synthetic checks:
201 API tests plus full migration downgrade/upgrade, 26 Node boundary tests,
production build/typecheck, and 40 browser scenarios passed with zero skips or
failures. A final preview-spacing correction was rebuilt and its three affected
browser scenarios passed again, including persistence and desktop/mobile captures.
Details and evidence are in `docs/harness.md`; backup/restore was not rerun here.

## Approved factory appearance (implemented for review, 2026-10-31)

The owner accepted the reviewed brand-kit theme as the out-of-box appearance:
ivory/white surfaces, charcoal text, burgundy actions, sans body/headings, balanced
spacing, soft corners and comfortable density. The dark preset uses forest and
contrasting light gold. This approves application theme tokens, not proposed
brand masters, logos, mascot artwork, navigation or layouts.

Migration 0010 aligns the database factory default and updates only exact legacy
factory settings at revision zero, incrementing that revision. Other saved owner
choices are preserved. Login and initial browser fallback match the branded light
palette. Downgrade maps the exact new default back to the older default with a
higher revision; custom themes remain intact. A rollback/re-upgrade does not
automatically readopt the new default. See ADR 0007 for the explicit restore path.
The portable theme is `packages/themes/relicrat-default.json`. This is not deployed.
