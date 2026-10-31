# Shared UI, brand, and theming brief

Updated 2026-10-31. Read this before UI, brand, or Appearance work and update it
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
