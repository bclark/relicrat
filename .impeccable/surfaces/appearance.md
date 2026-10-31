---
version: 1
slug: "appearance"
primary_target: "apps/web/app/appearance.tsx"
related_targets: ["apps/web/app/inventory-client.tsx", "apps/web/app/globals.css"]
---

# Appearance editor

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
