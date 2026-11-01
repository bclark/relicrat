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

## Collection opening refinement — 2026-11-01

User request: redesign the initial screen; confirmed the collection workspace
following sign-in. Mode: Operate. Code-led refinement of the approved factory
world; no brand proposal assets are promoted.

THESIS: Saved physical copies lead the opening; intake stays one explicit jump
away. Retain every save, conflict, uncertainty and authentication boundary.

OWN-WORLD: Inherit the approved ivory/white, charcoal and burgundy theme, system
sans, theme-controlled density/corners and plain native controls. One broad
collection register sits beside the quieter entry workbench.

STORY: Find an existing copy or add the next find. No invented analytics,
valuations, objects or implied total inventory count.

FIRST VIEWPORT: Compact brand header, 48px collection heading and Add a find
link; inline settings tools; search/register at left, entry at right. Mobile
uses that same semantic order, with the heading link and skip link focusing
intake directly. Trial notice follows the workspace.

FORM: Existing collection register refined; no new visual-world seed or concept
round applies. No new illustration, icon, external font or runtime dependency.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

### Collection opening finish evidence

Independent reviewer `/root/impeccable_finish_reviewer` returned **ship** for the
four empty/populated desktop/mobile captures and current code; no UI fix was
required. Documentation merge updates the previous layout/type descriptions.
Evidence is `.impeccable/review/collection-opening/{desktop,mobile,empty-desktop,empty-mobile}.png`.
The production build, TypeScript, 26 Node boundary checks and five selected
synthetic fixture browser scenarios passed with zero failures/skips in final runs.
See `docs/harness.md` for exact commands, initial environment failures, and limits.
No real database/session integration, deployment or backup claim is made. No new
shipping raster assets require provenance. Original surface evidence above remains
historical and is not the current capture set.

## Workspace navigation correction — 2026-11-01

This replaces the collection-opening layout direction above at the owner's
request. Keep existing palette, typography, save and theme contracts.

THESIS: Entry is a visible left-side work area on desktop. Utility controls
belong to the header; mobile uses a compact menu and a reversible entry disclosure.

OWN-WORLD: Preserve current theme roles and native text controls; no new assets.

STORY: Save copy creates one physical copy. Opening/collapsing entry or a settings
panel does not create ownership or save preferences. Drafts remain mounted.

FIRST VIEWPORT: Brand at left, Appearance/collection settings/Sign out at right.
Intake at desktop left, collection at right. Mobile has one Menu button and a
collapsed Add a find section before the collection; the unused record placeholder
is hidden. There is no separate Add a find jump button. The skip link opens intake.

FORM: Owner-specified responsive correction, code-led. Settings editors remain
inline below the opening heading. Menu supports outside click, Escape with focus
return, and dismissal when focus leaves. Closing setup restores trigger focus.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

### Workspace correction finish

Independent `/root/workspace_finish_reviewer` returned **ship**, no UI fixes or
recaptures, over all ten empty/populated 1440/768/390/320px and mobile interaction
captures under `.impeccable/review/workspace-navigation/`. Final checks: build and
TypeScript passed, 26 Node tests passed, 11 selected synthetic browser scenarios
passed with zero failures/skips. Exact commands and initial setup/capture issues
are recorded in docs/harness.md. No real session/database integration, API suite,
recovery or deployment claim applies. No shipping raster assets were added.

Owner approval, 2026-11-01: “ok let's go with theses” accepts the corrected desktop
and mobile layout after review. Status: approved and implemented locally; not
deployed. This approval does not promote unrelated proposed brand assets.


### Current-feature integration

The approved layout is now ported onto the PR59 baseline rather than replacing
newer features with the original older checkout. CSV imports, groups, Movies,
barcode lookup/covers and explicit saves remain. Mobile collapse stops camera
tracks without discarding the find draft. Focused worker/browser verification and
initial test-helper corrections are recorded in docs/harness.md; deployment
status is recorded separately. No proposed brand assets were promoted.
