---
version: 1
slug: "appearance"
primary_target: "apps/web/app/appearance.tsx"
related_targets: ["apps/web/app/inventory-client.tsx", "apps/web/app/globals.css"]
---

# Appearance editor

## Approved factory palette follow-up (2026-10-31)

The owner accepted the brand-kit review's default theme: ivory page, white
surfaces, charcoal text and burgundy shared accent, sans body/headings, balanced
spacing, soft corners and comfortable density. The dark preset uses forest
surfaces and light-gold actions. This changes factory theme values, not structure,
navigation, logos or mascot assets. The application remains the existing Operate
workbench; the original extension and finish records below describe its history.

The default export is `packages/themes/relicrat-default.json`. Browser fallback
and login must match it; migration 0010 updates only pristine legacy factory
values and preserves other owner choices. Any migration-driven appearance change
increments its conflict revision. Require desktop/mobile evidence for initial
light appearance, login and the dark preset. No new comp or raster assets are
needed. Exact runtime/rollback behavior belongs in ADR 0007.

Mode: Operate. This is a local extension of the existing inventory surface,
inheriting its native labeled controls, focus behavior, typography and ruled
sections. It does not establish a replacement brand or permanent user palette.

The collector confirmed colors, fonts, spacing, corners and density, with manual
controls and preview. AI assistance is a prompt/Markdown guidelines file for an
external AI tool, followed by imported theme JSON. No embedded provider is wanted
for this increment. Layout and navigation are outside scope.

Interaction: a compact Appearance button expands an inline editor. Starting
themes and manual controls sit beside an isolated, labeled sample on desktop;
mobile keeps controls before sample. Preview validates without writing. Editing
invalidates it; explicit Apply saves only appearance with its own revision.
Disclosures hold the palette, AI guidelines and JSON import/export. Unconfirmed
writes require reload and review. Collection drafts and ownership remain intact.

The sample must demonstrate font, color, spacing, density and corners. Preserve
44 px touch targets and readable statuses; theme values never become executable
CSS or external resources. Error styling stays controlled by the application.

No comp, illustration, raster asset, icon or redesign is required. Desktop and
mobile screenshots use synthetic data and are verification evidence only.

## Finish record (2026-10-31)

Documentation review: consistent with this brief and PRODUCT.md's Appearance
authoring section. The final implementation retains DESIGN.md's default
workbench palette, system typography, native labeled controls, flat ruled
sections, explicit save/status treatment and 44 px control minimums. Its bounded
owner-selected theme values are a presentation extension, not a replacement
visual world. Desktop keeps controls beside the isolated sample; mobile places
the sample after them. The sample's themed heading, selected row and fixed error
treatment demonstrate the supported scope without implying an inventory write.

Final synthetic full-page evidence: `.harness-results/appearance/review/appearance-desktop.png`
(1440 × 2455) and `appearance-mobile.png` (390 × 4215). The independent finish
review disposition was SHIP with no material fixes. Validation and its final
preview-spacing rerun are recorded in `docs/harness.md`; this documentation pass
inspected the final captures and code rather than rerunning those checks.
DESIGN.md, `.impeccable/design.json` and historical records remain unchanged;
pre-existing metadata drift is outside this extension.


## Current factory-theme documentation update (2026-10-31)

Status: implemented for review; independent finish disposition SHIP, not deployed.
The approved light factory palette is now recorded in root DESIGN.md and its
sidecar, including the runtime role aliases and self-contained component samples.
The same inventory workbench and semantic controls remain; this update introduces
no layout, navigation, logo or mascot changes. The After hours companion uses
forest surfaces, ivory text and light-gold actions. Login and initial fallback
retain the approved light palette, with the saved theme applied after sign-in.

This documentation pass inspected the current CSS, theme runtime and all six
synthetic browser captures under `.harness-results/brand-default/review/`:
`default-desktop.png`, `default-mobile.png`, `dark-desktop.png`,
`dark-mobile.png`, `login-desktop.png` and `login-mobile.png`. Desktop retains the
two-column intake/register composition; mobile stacks the same labeled controls.
The captures confirm the palette and retained structure, not a deployment or
whole-interface accessibility certification. Authenticated primary hover retains the action accent and adds an underline.
The parent verification also checked an enabled, focused keyboard-pressed primary
action (`:active` true): burgundy background with white text. No active-state
CSS correction was made. The preceding Finish record belongs
to the earlier Appearance extension; its verdict does not cover this palette update.
A fresh independent finish review of this palette-only update and all six final
captures returned SHIP with no material fixes. Its persistence, fidelity, ceiling,
material-fixes and keep assessment applies to this scoped appearance change.
Runtime, migration, rollback and test evidence remain in ADR 0007, PRODUCT.md and
the harness record.
