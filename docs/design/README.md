# Shared UI, brand, and theming brief

Updated 2026-11-04. Read this before UI, brand, or Appearance work and update it
when a decision changes another area's work. It is a shared handoff, not an
automatic transcript sync or a substitute for inspecting the implementation.

## Sources and authority

| Question | Source | Status |
| --- | --- | --- |
| Character identity and creative direction | [Canonical brand brief](../brand/RELICRAT_BRAND.md) and [original reference images](../brand/references/) | Approved creative direction; exact production specifications remain pending |
| What the current application looks like | [Root DESIGN.md](../../DESIGN.md), current components and CSS | Describes the incumbent application; does not lock permanent branding |
| Supported theme behavior and boundaries | [Appearance decision](../decisions/0007-appearance.md), [theme authoring contract](../../packages/themes/AUTHORING-PROMPT.md), current parser/schema | Implemented for review; verify rollout separately |
| Latest proposed logos, mascot extensions, palette samples and screens | [Brand kit revision 2](proposals/brand-kit-v2/README.txt), [interactive prototype](proposals/brand-kit-v2/prototype/index.html) | Proposed; separate local demo, not the production application |
| Original home, collection and detail mockups | [Original exploration and brief](proposals/ui-exploration-2026-10-31/) | Exploratory crops; next composition target is separate full 4:3 desktop screens |
| Product behavior, domain rules and verification | [Product record](../../PRODUCT.md), [architecture](../architecture/overview.md), [harness](../harness.md) and affected code/tests | Evidence must distinguish goals, implementation and deployment |

The canonical brief and original reference PNGs were copied without edits from
the recovered design package. The primary mascot image governs face, anatomy
and outfit; the modern-collectibles board governs subject matter and creative
direction; the silhouette sheet supports icon research. The additional
`wordmark-exploration.png` is earlier exploration, not a replacement authority.
Keep canonical inputs here once; link to them from future proposal revisions.

## How the work fits together

- **UI/brand work** proposes screen structure, navigation, collectible presentation,
  logo/icon/mascot assets and brand applications. Preserve the existing save,
  conflict, ownership, accessibility and history behavior when proposing integration.
- **Theming work** owns the supported appearance contract, validation, import/export,
  isolated preview, explicit apply, persistence and revision handling. Preserve
  user customization; a brand proposal does not override a collector's saved theme.
- **Both** use the same brief and record cross-cutting decisions here. Existing
  chats should re-read it on their next relevant turn. Read the other chat when
  history matters; message it only with explicit user authorization.

## Current agreements and unresolved differences

1. **Approved direction:** modern, collection-first software; the established rat
   character; forest, burgundy, charcoal, ivory and restrained gold color families.
   Avoid blanket sepia or paper texture in the product interface. The owner approved
   the factory theme tokens below; final brand-wide color specifications,
   typography, logo geometry and new mascot extensions remain proposed.
2. **Implemented theme boundary:** portable schema-version-1 JSON supports eight
   color roles, bounded body/heading font choices, spacing, corners and density.
   It does not install CSS, images, logos, navigation or layouts. AI assistance
   uses downloadable guidelines and an imported response, not an embedded model.
   Use the authoring contract above for exact fields and contrast requirements.
3. **Integration gap:** revision-2 screens use forest navigation and burgundy
   primary actions. The current theme contract has one shared action accent for
   links, focus and primary buttons. The kit's light/dark JSON samples fit that
   existing single-accent contract; they cannot recreate the complete screen design.
   Do not silently expand the theme schema to match the mockup. Decide separately
   whether a future interface needs fixed brand surfaces or more semantic roles.
4. **Approval boundary:** the owner accepted the review recommendations and asked
   for revision 2. That authorizes the revision work, not automatic promotion of
   each new vector, character pose or layout to an approved production master.
5. **Production boundary:** the review uses generated fictional imagery and
   browser-local synthetic records. It is not the app, real provenance evidence,
   a production inventory store, or an authorization to deploy.

## Current handoff record

| Date | Area | Decision or evidence | Source and next step |
| --- | --- | --- | --- |
| 2026-11-02 | Three-pane layout reviewed and integrated for PR | Approved quick-entry rail, List/Bricks and separate copy inspector adapted onto current main. Retains Movies, CSV import, storage/type filters, server grouping and structured barcode/provider/optional-cover review. Back preserves drafts; hidden phone rail stops its camera. | Owner asked to review and open a PR. Original designer checkout preserved. [Plan](../../DESIGN_PLAN.md) and [validation](../harness.md). Not deployed. |
| 2026-11-01 | Unboxed collection workspace | Approved and implemented: unboxed intake, compact title/edition/location rows; individual pages group Albums, Comics, Movies and Other finds with page-local counts. Existing whole-collection groups remain. | Owner “implement and deploy it”; [implementation plan](../../DESIGN_PLAN.md). Deployed to the existing private trial from commit a1b2b16; [PR63](https://github.com/bclark/relicrat/pull/63) remains open. Chromium/WebKit, responsive/theme and existing workflow checks passed; backend and full inventory/media fingerprints preserved. |
| 2026-11-01 | Movie barcode title lookup — implemented for review | Movie JSON selects UPCitemdb through the installed registry. Reuse the existing automatic search, reviewed fill and final save; title only, optional fields remain manual, no artwork. No theme, layout, schema or dependency change. | Owner requested Movie barcodes; [provider and privacy contract](../barcode-lookup.md#movie-title-lookup-with-upcitemdb). Free-tier rate/coverage limits apply; deployment remains separate. |
| 2026-11-01 | Workspace layout integration | Port the approved local navigation/layout onto the PR59 baseline, preserving Movies, CSV import, grouped browsing and configured barcode lookup/covers. Mobile disclosure keeps the draft mounted and stops its camera when hidden. | Owner requested deployment of the local work. Integration is isolated from the original design checkout; no API, schema, dependency or theme-contract change. Rollout status belongs to the private deployment receipt. |
| 2026-11-01 | Workspace navigation approved and implemented | Owner approved the reviewed desktop/mobile layout: intake at desktop left, with Appearance, collection settings and Sign out in the header. Mobile groups those controls under Menu and starts intake collapsed with a Show/Hide control that preserves drafts. Removed the separate Add a find jump button; Save copy still creates the record. Settings editors remain inline, with focus handling and the same theme/save contracts. | Current frontend-design follow-up: “ok let's go with theses” after the revised previews and validation. Replaces the previous layout direction below. Local implementation only, not deployed; no API, migration, dependency or brand-asset change. |
| 2026-11-01 | Collection opening, superseded by correction above | Owner confirmed the initial screen means the signed-in collection workspace. Saved copies and search now lead at left on desktop and first on mobile, with intake beside/below them. A prominent Add a find link and the skip link focus intake directly. Settings share a compact toolbar; the synthetic-trial notice follows the workspace. Approved theme tokens and saved customization remain intact; no proposed brand assets are promoted. | Current frontend-design conversation and `apps/web/app/inventory-client.tsx`; local implementation only, not deployed. No API, migration or save-boundary change. |
| 2026-11-01 | Intake order — implemented for review, not deployed | Place What are you adding? before Scan barcode inside the existing find form. Type selection configures scanning/lookup before use; ordinary final save and all native controls/theme tokens remain. | Owner’s request to put type selection at the top and scan below; no domain/schema change. |
| 2026-11-01 | Movies and Blu-ray.com CSV — implemented for review, not deployed | Extend existing Operate setup/intake/edit/import/browse surfaces with title-first Movie config, optional format/studio/edition/notes, native choices with Other and saved studio suggestions. Preview/confirmation stays explicit; each export row, including a box set, is one owned item. No theme/layout/brand changes. | Owner’s Movie-support request with a private Blu-ray.com export; [Movie and import contract](../movies.md). Synthetic verification and migration/recovery evidence precede rollout. |
| 2026-11-01 | Lookup failure recovery — implemented for review | Preserve sanitized API failure details (busy, timeout, unavailable) beside the existing retry action; retain the draft. No layout/theme change or automatic retry. | Owner reported intermittent lookup failures; diagnostics found the same code later matched. Provider read window increases within an elapsed budget; see lookup contract. Not deployed. |
| 2026-11-01 | Catalog cover — approved direction; implemented for review | Owner requested optional retention of matched artwork. Unchecked Include catalog cover stages artwork for the ordinary final save, with source metadata; display it separately from physical-copy photos. Preserve existing media and catalog/ownership identity. Not deployed. | Owner’s cover-option request; [cover contract](../catalog-covers.md). |
| 2026-11-01 | Scan-to-lookup — approved direction; implemented for review | A successful scan for a type with a configured provider now stops the camera and starts lookup immediately. Remove the redundant barcode confirmation; preserve match/field review and the final save. Types without lookup keep Use barcode. No theme/layout change. Not deployed. | Owner’s “go straight to trying to find it” request; [lookup workflow](../barcode-lookup.md). |
| 2026-11-01 | Provider configuration mount — implemented for review, not deployed | An operator-owned read-only type definition can select an installed provider and field mappings without rebuilding API. No UI or theme changes; refresh after API restart. Credentials and executable adapters stay outside the JSON. MusicBrainz remains the only bundled live adapter; Discogs integration is separate. | Owner’s “They should be simple to swap” and “Set that up” requests; [configuration/rollout/recovery contract](../barcode-lookup.md#swap-with-an-operator-owned-config-mount). |
| 2026-11-01 | Barcode lookup — approved direction; implemented for review | Owner approved type-config selection of installed barcode-provider adapters, field mappings and bounded options. Album selects MusicBrainz; review fills only chosen draft fields, preserving existing text and ordinary final saves. Cover previews remain separate from copy photos. Incumbent theme/layout is preserved; no new theme tokens or brand assets. Not deployed. | Owner’s configurable-provider and “lets move forward” requests; [lookup contract](../barcode-lookup.md), [type-definition decision](../decisions/0005-type-definitions.md). Provider search availability and live outbound access must be checked before rollout; a new API requires an adapter. |
| 2026-10-31 | Factory theme approved | Owner accepted the reviewed out-of-box theme: light ivory/white surfaces, charcoal text, burgundy shared action accent, sans body/headings, balanced spacing, soft corners and comfortable density, with a forest/gold dark companion. Implementation updates API/browser defaults and the dark preset. Migration 0010 updates only exact legacy factory values at revision zero; other saved owner choices remain unchanged. Validation passed: 206 API checks plus migration round trip, 26 Node checks, production build/typecheck and four affected browser scenarios; fresh visual review returned ship. This is not deployed. | “Theming” chat: “looks good” after the palette review; [approved default JSON](../../packages/themes/relicrat-default.json), [appearance decision](../decisions/0007-appearance.md). This approves application theme tokens, not new logo/mascot assets, brand-wide master specifications, or prototype layout installation. |
| 2026-10-31 | Theming | Chat reported commit `0cdcd9e`, “Add portable AI-assisted visual themes”; implementation exists locally. This handoff does not establish deployment. | “Theming” chat, `01a19284-a160-7951-b082-47515a4dd109`; use current authoring contract and deployment evidence before rollout claims. |
| 2026-10-31 | UI/brand | Revision 2 refines wordmark/head icon, adds a small-size silhouette, standalone transparent mascot studies and varied fictional collectible imagery. All remain proposed/exploratory. | “Prepare RelicRat UI mockups” chat, `01a192ae-8bc4-7272-ba3e-1d6342ea9a9f`; owner visual review and production integration remain separate. |
| 2026-10-31 | Shared context | Canonical references and review sources brought into this repository; AGENTS.md and root README now point here. No application behavior changed. | Original export folder: `/Users/bryanclark/Documents/ChatGPT/Relic Rat/`. Original brand/UI chats remain historical sources. |

## Updating and sharing

Keep updates short: date, decision, approval/implementation/deployment status,
source, and what another chat needs to do. Link to detailed contracts rather than
copying their schemas here. Never infer current deployment from old chat claims.

Same-checkout chats can read saved changes immediately. A different worktree or
branch needs the relevant commit brought over first; a message alone does not
transfer files or merge branches. When concurrent work overlaps, agree on the
files/area being changed before editing. Do not overwrite another chat's work.

Rebuild the offline design review from the revision-2 folder with
`python3 build-review.py`; generated standalone HTML is ignored to avoid storing
another embedded copy of every asset. The original exports remain available in
the external folder. This setup does not install a theme, modify production
assets, start recurring synchronization, or authorize messages between chats.

### Integrated release handoff (2026-10-31)

The approved factory-theme work is being integrated with the merged CSV importer,
config-driven grouped browser and branded README. Its previously local migration
was never deployed; it is now `0010_brand_default`, following `0009_csv_import`,
so there is one linear migration history. Deployed migration files remain intact.
The original worktree and its unrelated root lockfile are untouched.

The release preserves saved owner choices. It changes only a pristine exact old
factory theme at revision zero; it does not force the new palette onto an owner
who selected another theme or explicitly saved the old default. Use Appearance →
Restore default draft → Preview theme → Apply theme to adopt it explicitly.
Integration checks and rollout evidence are separate from the historical theme
checks above. The prototype layouts, new mascot extensions and wordmark masters
remain proposed; this release adopts application colors, not a new navigation UI.


### Reviewed storage mapping (2026-10-31)

The owner accepted explicit CLZ storage-box mapping after CSV import. This
increment adds a native-control flow within import history: source label →
physical destination → paginated preview → explicit confirmation. Existing
placements and prior manual unassignments are preserved; Discogs folders remain
source information. It uses existing theme tokens and movement history without
changing navigation, branding assets, schema or the collection editor. Implemented on the storage-mapping branch; synthetic verification and rollout
are recorded separately in the harness evidence.


### Camera barcode trial (2026-10-31)

The owner chose phone-camera scanning and accepted a barcode-only prototype
before catalog lookup. A compact inline scanner beside Add a find inherits the
current Operate surface, theme and native controls. It reads on-device, keeps
readings transient, and makes no ownership or catalog changes. Explicit start,
stop, rescan and close controls preserve intake drafts and keyboard focus. No
new brand assets, layout system, theme schema or type-config fields are needed.
Implementation and synthetic camera verification precede physical-phone testing;
private HTTPS access and phone/browser selection remain separate setup work.


### Collection authoring preview (2026-11-02)

Owner approved a TMNT pilot: original 1988 Playmates ten basic characters, one
per character, optional accessories/condition/packaging and separate variant notes.
Implemented for review: native expandable Start a new collection flow, description,
downloadable external-agent prompt, JSON paste/upload, strict server validation,
read-only entry form/checklist/source preview. The API-generated schema is the
prompt authority. This does not activate custom types, write inventory, evaluate
ownership/completion or fetch evidence URLs. Uses existing theme and form controls;
no theme/brand/layout contract change. The bounded figure-style contract and next
storage work are documented in
[the pilot](../../packages/collection-packs/proposals/tmnt-original-1988/README.md).
Not deployed.


### Explicit collection creation and figures (2026-11-02)

Owner approved Create collection after the successful TMNT preview and requested
plain-URL guidance after an agent returned Markdown links. Implemented for review:
acknowledged activation creates only immutable definition/checklist records; a
saved-collection selector offers explicit Add figure with configured optional text
fields. Figures retain ordinary inventory photos/storage/search and one shared
Save details with custom observation history. Exact retries are safe; unfinished
figure drafts and uncertain saves remain in their original collection when a
second collection is created. Reuses existing theme/native controls. No token,
brand or layout contract change. Migration0014 and boundaries are authoritative
in [ADR0011](../decisions/0011-custom-collections.md). Not deployed; completion,
definition revision and existing-copy membership changes remain deferred.

### Configurable custom fields (2026-11-03)

Owner approved single-choice Head Variant controls and compatible definition
updates. Implemented for review: shared native text/dropdown/radio/checkbox
controls in preview/intake/edit, explicit Review and Apply for changes affecting
all collections sharing a type, and retained definition history. Missing, No and
None selected stay distinct; stale forms preserve drafts. Reuses incumbent theme
tokens and layout. No new brand assets or theme contract. Not deployed;
[ADR0012](../decisions/0012-custom-field-controls.md) defines data/recovery rules.

### Authoring field plan (2026-11-03)

Owner requested that field controls be settled during agent/JSON authoring.
Implemented for review: generated and static prompts propose controls, confirm
exact choice labels within the existing question budget, and emit agreed input
and options in JSON. Existing preview already renders these controls before
creation. Preserve existing labels during revisions; no automatic conversion.
No UI, schema or live definition changes. Not deployed.

### Evidence-link import recovery (2026-11-03)

Owner encountered Markdown-wrapped source URLs despite authoring guidance.
Implemented for review: API canonicalizes a whole single safe HTTPS Markdown
link and reports corrections through the existing preview notice; sources remain
plain text for review, never fetched. Draft text and ownership stay unchanged.
No frontend, theme or layout change; not deployed. See ADR0011 extension.

### Reviewed checklist progress (2026-11-03)

Owner approved explicit figure-to-entry matches, distinct-entry progress and
visible missing goals. Implemented for review: saved collections show whole-goal
progress and a missing filter; the figure inspector has an independent reviewed
checklist save and paginated history. A link without eligibility confirmation
stays pending. Duplicates count once; inactive/nonowned copies do not count.
Existing native controls/theme, intake drafts, copy details and catalog/storage
boundaries remain. No new assets or tokens. Not deployed;
[ADR0013](../decisions/0013-checklist-progress.md) defines data and recovery rules.

### Custom collections in shared browsing (2026-11-03)

Owner requested moving forward after checklist progress. Implemented for review:
custom goal collections appear alongside built-in types in the main filter and
whole-inventory grouped overview. Search, storage, pagination and the selected
copy inspector are shared. Custom names/UUIDs stay separate from Other finds;
main progress covers the whole collection, unaffected by browse filters. A
shortcut opens the existing figure-intake flow and respects unfinished drafts.
Existing forms retain their independent save/membership rules. Native optgroups
and paged choices use existing theme/layout; no new tokens/assets or schema.
Not deployed. Detailed [browsing contract](../custom-collection-browsing.md).

### Missing checklist entry to figure draft (2026-11-03)

Owner approved an Add this figure action on missing goals. Implemented for review:
main and saved-collection checklists can open existing custom intake with the
entry name prefilled and focused. Pending/collected entries retain their review
path. An unfinished custom draft or uncertain save cannot be replaced. Explicit
Add figure and later checklist qualification remain separate owner actions.
Native buttons and existing layout/theme retained; no new tokens or assets.
Not deployed. See [intake behavior](../checklist-intake.md).

### Portable custom collection definitions (2026-11-03)

Owner approved Export collection JSON. Implemented for review: a saved-collection
button downloads the current persisted field controls and proposal in the normal
import format. Fresh reads and existing preview validation precede download;
personal inventory and unsaved drafts are excluded. Native button/status/error
patterns and current layout/theme retained. No new tokens/assets/API/schema.
Not deployed. See [export contract](../collection-definition-export.md).

### Import as an independent collection (2026-11-03)

Owner approved reusing a shared definition without editing JSON identifiers.
Implemented for review: an optional Import as a new collection checkbox and name
field precede the existing validation, preview, acknowledgement and Create flow.
Raw source validates first; fresh collection/type identities isolate later field
edits. Owned figures/progress are not copied. An uncertain creation response keeps
its reviewed proposal for same-identity retry. Native controls, existing theme
and layout retained; no new assets/tokens/API/schema. Not deployed.
[Copy-import contract](../import-collection-copy.md).

### Private-beta acceptance audit (2026-11-03)

Owner requested the remaining phase-one work. The current progressive intake,
three-pane desktop layout, phone Back navigation and theme contract remain the
approved behavior. Older browser journeys now follow Review item
and the intake closing after Save copy. This is acceptance/harness work, not a
layout or branding change. Physical-phone usability remains an owner acceptance
step; automated viewport checks do not establish it. See the
[phase-one checklist](../private-beta-acceptance.md) and
[verification record](../harness.md#private-beta-acceptance-audit-2026-11-03).

### Operating reliability and report status (2026-11-03)

Owner requested the full reliability follow-up after accepting phase-one
functionality and deferring a major UI/UX overhaul. Implemented for review:
a separate Operations tab in the existing project report, preserving its
historical sections and incumbent design. It reads private aggregate health,
capacity and distinct NAS/Mac/Drive checkpoints through a loopback-only server.
No inventory interface, theme, collection field or ownership behavior changes.
Native controls, escaped text, stale/unavailable states and responsive views
were checked. See [operating contract](../operating-reliability.md) and the
[report design record](project-dashboard.md#operations-extension--2026-11-03).

### Collection browsing journey concept (2026-11-04)

Owner requested a redesign of open collection → find item → view/edit and chose visual concepts before implementation. Proposed: collections in navigation, a collection-scoped search/filter row, artist/series grouping, and a read-first inspector with an explicit Edit details step. Desktop keeps browse context; phone Back should restore query, position and focus. Preserve supported theme roles, physical-copy identity, separate photo/location saves and dirty/uncertain drafts. [Three concept frames and implementation boundaries](proposals/collection-journey-2026-11-04/README.md) use fictional collection data. Status: proposed for review, not approved, implemented or deployed. Existing designer checkout and active inventory are unchanged.

### Collection journey approved for implementation (2026-11-04)

Owner approved the three visual concepts and requested a focused implementation
PR, with review before deployment. Collections lead navigation; browsing retains
server grouping and storage/search scope; copy details open read-first with an
explicit Edit details step. Back preserves mounted drafts and browse context;
replacing a dirty copy requires an explicit discard decision, and uncertain saves
require inspection. Core/API/web stay here; native and immersive clients use the
API. The implementation preserves the current theme roles and separate
storage/photo/catalog saves. Fictional artwork in the concepts is not shipping
inventory or a new brand master. Implementation and verification are recorded
separately below; no deployment is authorized by this handoff.

### Collection journey implemented for review (2026-11-04)

The focused implementation uses collection navigation, a search/storage toolbar,
List/Covers, existing artist/series groups and a read-first inspector with explicit
Edit details. Back retains mounted drafts and restores browse position/focus;
confirmed Save returns focus to Edit details. Existing theme tokens and domain
save boundaries remain. API list display metadata adds existing artwork/location
names without per-row metadata requests. No migration or dependency is added.
[Behavior and limits](../collection-journey.md), [current product](../../PRODUCT.md)
and [checks](../harness.md) are authoritative. Status: implemented for review,
not deployed. Broader screen redesign and native/immersive clients remain future work.

### One Collections list — approved and implemented for review (2026-11-04)

After trying PR78, the owner found Collections versus My Collections confusing
and requested one list. Desktop navigation now places built-in and named
collections in one continuous list under Collections, with All items first.
The phone chooser has the same flat choices and All items label, without type
or custom collection optgroups. Scope IDs, ownership, grouping, paging, errors
and draft preservation remain unchanged. No theme, schema or API change.
Status: implemented for review; not deployed.

### Add-item journey — proposed visual concept (2026-11-04)

Owner requested collection → scan or title → review optional details/cover → one
clear Save across built-in and custom collections, with a visual concept before
implementation. The [interactive proposal](proposals/item-intake-2026-11-04/README.md)
extends the current palette/components and uses fictional in-memory examples.
It brings the destination first and reviews suggestions in the final form;
current provider/cover capabilities and separate custom ownership/checklist rules
remain explicit. Status: proposed for owner review; no app or deployment change.

Owner refinement (2026-11-04): selecting a collection already establishes the
intake destination. The concept now says “Add to Movies” (or the selected name)
and removes the repeated picker. Only Add from All items asks for a destination.
Applies equally to named custom collections and phone entry. Proposed; app unchanged.

### Add-item concept approved for implementation (2026-11-04)

Owner approved the refined concept: a scoped “Add to Movies” (or collection name)
without a repeated picker; All items keeps destination selection. Build one
config-driven entry, review suggestions and optional cover in the final form,
and confirm one physical copy after Save. Preserve custom request identity,
explicit checklist qualification, manual input, drafts and uncertain outcomes.
Implementation and verification remain separate from deployment.

### Shared item intake — implemented for review (2026-11-04)

The approved concept is implemented in one shared, config-driven task. Selected
collections establish the destination; only All items asks for one. Suggested
fields and optional cover are reviewed before one Save item. Built-in and custom
creation preserve drafts, uncertain outcomes and explicit ownership rules.
See [item intake](../item-intake.md) for the behavior contract and
[verification](../harness.md) for evidence and limits. Desktop, 390px and dark-theme
synthetic captures were reviewed. Status: implemented for PR review; not deployed.

### Item view and editing — proposed visual concept (2026-11-04)

Owner accepted exploring focused editing after PR80 intake. The
[interactive concept](proposals/item-edit-2026-11-04/README.md) extends that approved
world: read-first item, explicit Edit details, configured fields, one details save,
clear confirmation and context-preserving Back. It covers built-in and custom
examples on desktop and phone. Existing immediate storage confirmation and
separate photo upload remain explicit; notes stay read-only under the current API.
Fictional page-memory data only. Status: proposed for owner review; no app or
deployment change. Implementation must reuse actual configs and revision guards.

### Item view and editing — approved implementation (2026-11-04)

Owner approved the interactive concept and requested implementation. The item now
uses the browser content area, with read-first observations and a focused Edit
details task. Back retains the detail draft and browse context. Save changes is
one revision-checked details write; immediate storage confirmation, independent
photo upload, read-only notes and explicit ownership/checklist rules remain.
See [behavior contract](../item-editing.md). Status: implemented for review;
verification is recorded in the harness and PR; not deployed by this change.

### Collection management — proposed visual concept (2026-11-04)

Owner accepted exploring collection setup/management next. The
[interactive proposal](proposals/collection-management-2026-11-04/README.md) places
built-in and custom collections in one management list, with entry preferences or
custom controls, explicit shared-definition impact, and a describe → external
agent prompt → JSON review → empty collection creation path. Scope, evidence,
uncertainties, compatibility and no-ownership creation remain explicit. The
existing figure pilot, type defaults, revision/unknown-save rules and actual
server validation must remain during implementation. Fictional page-memory data
only. Status: proposed for owner review; no app or deployment change.

### Collection management — approved implementation (2026-11-04)

Owner approved the interactive concept and requested implementation. Manage
collections now gathers the paginated built-in/custom list, scoped entry
preferences, the complete existing defaults/setup workflow, and figure JSON
creation into one task. Custom controls retain compatibility/revision checks,
live previews, explicit review and history; shared impact uses the server's
confirmed count rather than guessed names. Creation ends with an empty-collection
confirmation and explicit Browse action. [Behavior contract](../collection-management.md).
Status: implemented for review; checks and limits belong in the harness/PR.
No app deployment or theme-contract change is implied by this implementation.

### Collection management rollout and next journeys (2026-11-04)

Owner authorized deployment after PR82 merged and requested the photos/storage
and CSV follow-ups. PR82 is deployed to the existing private trial from merged
commit `147cb6d`; exact preservation, fresh capture/offline restore, private access
and operations-profile evidence is retained privately. Prior Mac/Drive receipts
still identify their own actual source; this rollout claims no new cloud backup.

The [two-journey interactive proposal](proposals/photos-storage-import-2026-11-04/README.md)
extends the approved visual system: local photo preview plus explicit upload,
immediate storage selection and confirmation, and preset-driven CSV preview,
explicit import and result inspection. It retains uncertainty, exact-file limits,
copy identity, source evidence and separate reviewed CLZ storage mapping. Status:
proposed for visual review, separate from deployed PR82. Use two focused app PRs
after review; no API, theme-schema or brand-default change is proposed.
