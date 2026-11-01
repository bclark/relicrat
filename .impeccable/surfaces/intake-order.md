---
version: 1
slug: intake-order
primary_target: apps/web/app/inventory-client.tsx
related_targets: [apps/web/app/barcode-input.tsx, apps/web/app/barcode-scanner.tsx, apps/web/app/barcode-lookup.tsx]
---

# Type before barcode

2026-11-01: implemented for review, **not deployed**. Mode: Operate; ordinary
extension of the existing Add a find form. The owner requested type selection
at the top with scanning below. Inherit [DESIGN.md](../../DESIGN.md), the
[sidecar](../design.json) and [shared brief](../../docs/design/README.md).

Order: What are you adding? → Scan barcode → configured entry fields → Save copy.
The existing BarcodeInput invocation now sits inside the existing form fieldset,
immediately after the native type selector. Selected type continues to configure
supported barcode formats and lookup; existing type-change draft confirmation,
keys, props, camera cleanup and focus behavior remain in force.

All scanner and lookup actions retain explicit `type="button"`. Scanning,
reviewing matches and filling fields only affect the draft; Save copy remains
the ownership boundary. The saved-copy editor caller is unchanged. This increment
introduces no CSS, asset, token, theme-schema, API or database changes.

Inspected [desktop](../review/type-first-desktop.png) and
[mobile](../review/type-first-mobile.png) captures show the requested order,
readable native controls, a retained synthetic draft and burgundy keyboard focus.
Desktop retains two columns; mobile retains one column without visible clipping.
These are implementation captures using synthetic data, not new design comps.

[Harness](../../docs/harness.md#type-before-barcode-2026-11-01) records production
build/typecheck, lint and 33 Node checks passing; four focused Chromium and four
WebKit scenarios passed with zero failures/skips. Reviewed intake source matched
the runtime; detector findings were `[]`. The independent finish review returned
**ship**, with no actionable findings. Evidence: `.harness-results/type-first/`.
The initial missing Playwright dependency link stopped runner startup only and
was corrected before complete passing runs. API/migration/backup suites were not
repeated; physical-phone testing, live-provider checks and deployment remain
separate. This documentation pass made no runtime or provider calls.
