---
version: 1
slug: barcode-intake
primary_target: apps/web/app/barcode-input.tsx
related_targets: [apps/web/app/barcode-scanner.tsx, apps/web/app/inventory-client.tsx, apps/web/app/copy-details-form.tsx, apps/web/app/globals.css]
---

# Barcode observation intake

Mode: Operate. Ordinary extension of the existing inventory workbench, implemented
for review while the physical-phone camera trial remains outstanding. Inherit the
current [DESIGN.md](../../DESIGN.md), [design sidecar](../design.json) and
[shared design brief](../../docs/design/README.md): approved ivory/white surfaces,
charcoal text, burgundy actions, system type, native controls and the existing
responsive workbench. These current sources govern appearance rather than the
earlier blue palette recorded in historical surface briefs. No new visual world,
tokens, assets, fonts, navigation or theme contract is introduced.

Job: retain a barcode as a separate observation on one physical copy. Scanning
shows the reading, format and optional supplement; the camera stops at a result.
Use barcode transfers it to a page-local draft. Save copy persists a new copy and
its observation; scanning and choosing a reading alone do not create ownership.
A title remains user supplied. No provider lookup, title inference or confirmed
edition claim is made. Missing supplements read Not detected.

The intake panel presents its draft observation before the ordinary labeled copy
fields, with explicit save guidance and Remove barcode from draft. The saved-copy
form places the same controls inside native Barcode (optional), before its existing
Save details action. Replacement and removal first change the draft; Save details
persists the revision-checked edit. Correction history retains before/after barcode,
format and supplement values in Copy edit history. Existing conflict and uncertain
write review boundaries remain in force.

Scanner controls reuse secondary buttons; persistence stays with the existing
burgundy primary actions. The scanner opens inline with native camera access,
readable waiting/error/result states and a Close scanner control. Result focus and
return to the launch control support keyboard continuity. Barcode text wraps in
its containing column; mobile preserves intake, selected-copy and collection
reading order. Camera video is contained within the existing surface.

## Comparison and finish evidence

Documentation review examined the five source targets above, current DESIGN.md,
the design sidecar, shared design brief and existing surface briefs. It visually
inspected all four final full-page captures of synthetic records:

- [Intake desktop](../review/intake-desktop.png) and [intake mobile](../review/intake-mobile.png).
- [Saved copy desktop](../review/saved-desktop.png) and [saved copy mobile](../review/saved-mobile.png).

The captures preserve the incumbent factory appearance, layout, native disclosure,
focus treatment and visible draft/saved distinction. They are implementation
evidence, not approved design comps or physical-camera performance evidence. No
shipping raster artwork requires provenance; screenshots contain synthetic data.
The implementing agent reports that a fresh independent finish reviewer examined
these four captures and code and returned **ship**, with no material findings.
The inspected local detector result at
`.harness-results/barcode-intake/detector.json` is an empty finding list (`[]`).

Physical-device detection speed, focus, camera permission behavior and supplement
capture remain unverified. This brief does not establish deployment or production
readiness. Existing historical metadata drift in PRODUCT.md and DESIGN.md is left
intact; the global design record and sidecar are preserved. Runtime, migration and
test results belong in their existing implementation and harness documentation.
