---
version: 1
slug: "apps-web-app-page-tsx"
primary_target: "apps/web/app/page.tsx"
related_targets: ["apps/web/app/inventory-client.tsx","apps/web/app/copy-detail.tsx","apps/web/app/globals.css"]
---

# Inventory intake screen

Primary target: apps/web/app/page.tsx. Related: inventory-client.tsx, copy-detail.tsx,
globals.css. Mode: Operate. Owner confirmed add-first and direct working-interface
build; no concept approval round or comp is requested. Code-led for this task only.

Job: capture a provisional physical copy, then add photos and choose storage;
browse/search that same inventory. Synthetic-only until deployment is hardened.
Catalog identification, valuation and production backup are not implied.

Grounded directions in resonance order: accession register, darkroom contact sheet,
library circulation console, specimen drawer, record-store new-arrivals desk,
archival finding aid, shipping receiving manifest. Three material families: paper,
photographic/screen, and physical handling/retail.

## Direction contract

THESIS: A new-arrivals workbench keeps a new find and the existing collection in
one working view, rather than a statistics dashboard or gallery-first showcase.

OWN-WORLD: Daylight at a collector's sorting desk calls for white surfaces, cool
blue-gray support, navy text and cobalt actions. System sans, square ruled rows,
plain labeled controls, no decorative images or specimen-like invented data.

STORY: Write what is known, save one copy, then attach its photo and location.
Search returns physical copies; selecting one opens its working record.

FIRST VIEWPORT: Compact RelicRat header and synthetic-only notice; a generous
add form at left, searchable collection register at right. The selected record
opens below the form, in the same reading order on mobile. The signature is the
handoff from saved find to its photo/location record, with no modal or lost UUID.

FORM: Grounded candidate 5, record-store new-arrivals desk; seed 42d347d8, API roll.
Code-led under the user's explicit instruction. Darkroom overlays/video-feed/tab
boards lose task clarity for sparse, mixed-object intake; keep their discipline
of explicit conflicts, one unambiguous selection, and separable working sections
without importing hatches, swipe navigation, or hinged tabs.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Constraints: meaningful provisional information, no silent retries/ownership
changes, explicit errors and separate saves, bounded pagination, keyboard focus,
mobile reflow. User photos are data, not shipping illustrative assets. No raster
or icons are required for this functional surface. Dashboard design remains scoped.

## Finish verdict and evidence provenance

Independent finish reviewer `/root/inventory_finish_reviewer` returned **ship** for
the built surface, with no material findings or required fixes. Root DESIGN.md and
.impeccable/design.json now record the actual implementation; the frozen progress
report record is preserved separately in docs/design/project-dashboard.md and
.impeccable/project-dashboard-design.json.

Evidence: .impeccable/review/desktop.png (1440 × 2163) and mobile.png (390 × 2703)
are full-page production captures of synthetic records and a synthetic PNG photo
fixture. They are implementation evidence, not approved comps. There are no
shipping raster illustrations or icon assets; user photos are collection data.
Source base: 299aeaffb9cb6b4a6eb78e9e977314b6d4d09810 plus this working implementation.

Current branch verification reported by the implementing agent: 10 Node boundary
tests and 7 browser cases passed, with no skips; production build/typecheck and the
real disposable stack with no published ports passed. No API pytest or backup
suite rerun occurred for this change. The historical 43-test result is not current
web validation. Documentation captures the working visual system without inferring
a permanent brand/palette preference or global configuration/build-path preference.
