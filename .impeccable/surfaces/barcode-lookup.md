---
version: 1
slug: barcode-lookup
primary_target: apps/web/app/barcode-lookup.tsx
related_targets: [apps/web/app/barcode-input.tsx, apps/web/app/barcode-scanner.tsx, apps/web/app/inventory-client.tsx, apps/web/app/copy-details-form.tsx, apps/web/app/copy-detail.tsx, apps/web/app/globals.css]
---

# Reviewed barcode lookup

Status: implemented for review, not deployed (2026-11-01). Mode: Operate;
ordinary extension of the existing inventory workbench. The current
[DESIGN.md](../../DESIGN.md), [sidecar](../design.json) and
[shared design brief](../../docs/design/README.md) govern appearance. Preserve
approved ivory/white surfaces, charcoal text, burgundy actions, system type,
native controls and the existing responsive layout. No new tokens, assets,
fonts, navigation or theme schema are introduced. The authoritative configuration,
privacy and rollout contract is [barcode lookup](../../docs/barcode-lookup.md).

## Job and save boundary

Help a collector review possible album releases from a barcode and choose which
details to fill. Type configuration selects an installed provider adapter,
bounded options and field mappings; Album currently uses MusicBrainz for title,
artist and format. Types without lookup configuration retain ordinary manual
entry and barcode observation controls. Changing a provider requires an installed
adapter rather than arbitrary executable configuration.

For a configured type, the sequence is: scan → camera stops and barcode attaches
to the draft → lookup starts immediately → choose a possible match → review
selected fields → Use these details → review/edit the draft → Save copy or Save
details. There is no intermediate barcode-confirmation click. Find album details
remains available to search again from an attached barcode. Types without lookup
retain Use barcode (or Replace draft barcode) before attaching the reading.
Reading, searching, reviewing and filling
do not save ownership or link a catalog item/release. Existing-copy changes use
the ordinary revision-checked details save and retained edit history; physical-copy
identity is preserved. Missing data remains unknown and a shared barcode does not
confirm an edition. Provider references remain visible during review. If the collector explicitly
includes a catalog cover and completes the final form save, its provider, candidate
ID, trusted source URL and creation time are retained with the private media asset.
Text-only filling does not create that artwork provenance record.

## Interaction and fallback

Lookup appears inline below the draft/saved barcode. Candidate buttons show title
and distinguishing metadata. Review uses native labeled checkboxes in the type's
entry order, showing each suggested value beside its current value. Nonempty
manual fields start unchecked; the collector can explicitly select replacements.
If the draft changes during review, filling is disabled until renewed review.
Use these details removes the candidate review, fills only checked fields and
announces that the form still needs saving. Cancel review returns focus to the
lookup action. A saved-copy lookup lives inside Barcode (optional), leaving its
separate Save details action and unsaved-change wording intact.

Busy, unavailable and empty states use readable status/error text and keep manual
entry available. Starting a scan deliberately authorizes one lookup for its
successful reading; rescanning the same barcode deliberately requests a fresh
lookup. There is no automatic retry. Opening a rescan hides the prior lookup;
closing it before a reading does not repeat a provider request. Unsupported
formats are rejected before lookup, preserving the prior draft.
Scanner lifecycle and observed-digit behavior remain in the
[barcode intake brief](barcode-intake.md); its older barcode-only scope predates
this optional lookup extension.

Cover images start as contained source previews with descriptive alternative text
and a text fallback when unavailable. Previewing does not import an image. The
optional retention path below keeps catalog artwork separate from physical-copy
photos. The source
link opens the provider release with no referrer. Camera frames stay on-device;
the API sends the barcode and cover identifier to the configured public services,
not collection records or owner credentials.

## Optional catalog cover (2026-11-01)

Implemented for review, not deployed. This narrow Operate extension preserves the
current theme, native controls, layout and navigation. The authoritative media,
source, migration and recovery contract is [catalog covers](../../docs/catalog-covers.md).

Review offers **Include catalog cover**, initially unchecked for every candidate.
It remains disabled while the preview loads; a failed preview removes the option
and clears its selection. The collector can choose fields, the cover, or both.
**Use these details** stages the selected cover alongside chosen draft fields;
it does not retain media. Focus returns to the stable title input and the status
states that the form still needs saving. The staged notice names the cover,
links its source and offers **Remove selected cover**. Changing the barcode or
collection type clears the pending choice. Drafts remain local until **Save copy**
or **Save details**; removing a pending cover does not delete saved artwork.

The final save sends provider/candidate references, never a client-supplied source
URL. The server validates and stores artwork with the ordinary copy/details save.
Unavailable artwork fails the save without partial copy/details/history changes;
the draft remains available for correction. Uncertain writes still require reload
and review. A cover-only attachment preserves text, catalog identity and existing
photos; existing artwork is retained rather than replaced.

Saved images appear in **Catalog artwork**, with a source link and explicit wording
that they are not photographs of the physical copy. **Photos** remains a separate
section and upload/save flow. Both reuse existing contained media frames and theme
styles. Catalog artwork does not prove ownership, an exact edition, pressing or
condition. The provider source records where the illustration came from, not a
verified identification of this object.

## Accessibility and responsive treatment

The surface uses a named region, semantic headings, native buttons/checkboxes,
pressed state for the selected candidate, status announcements and alert errors.
Search results and review headings are focusable programmatically. Applying
reviewed fields focuses the stable title input in both intake and existing-copy
forms. Scanner close restores its launch control. These handoffs preserve
keyboard continuity when transient controls disappear.

The extension inherits existing button targets and theme focus outlines. Ruled
rows, wrapped text and full-width candidate buttons stay within the incumbent
column; the cover uses object-fit containment. Mobile retains the existing
intake → selected copy → collection order and wraps review actions vertically as
needed. The surface CSS uses current theme variables, including checkbox accent;
there is no fixed replacement palette or new layout system.

## Evidence and limits

Documentation review read the implementation and callers above, global CSS,
browser scenarios, current design records and lookup contract. All eight current
full-page synthetic captures were visually inspected at desktop/mobile widths
for the scan-to-lookup refinement (2026-11-01):

- [Automatic lookup desktop](../review/automatic-desktop.png) and [automatic lookup mobile](../review/automatic-mobile.png): stopped scanner, attached draft barcode and possible matches without an intermediate confirmation; manual artist and final Save copy remain visible.
- [Review desktop](../review/review-desktop.png) and [review mobile](../review/review-mobile.png): manual artist unchecked, suggested fields selected, source/cover uncertainty and separate save visible.
- [Filled desktop](../review/filled-desktop.png) and [filled mobile](../review/filled-mobile.png): preserved manual artist, filled title/format, title focus and separate Save copy.
- [Existing-copy desktop](../review/existing-filled-desktop.png) and [existing-copy mobile](../review/existing-filled-mobile.png): title focus, unsaved-change wording and separate Save details.

These captures preserve the current factory visual system; they are implementation
evidence, not approved comps. Cover artwork is a generated synthetic test fixture,
not a shipping brand asset. Current evidence is under
`.harness-results/scan-direct/`: `design-detector.json` reports `[]`, and the
independent `finish-review.md` reports **ship**, with no material findings. The
inspected `chromium.log` reports 16 passed, zero failed/cancelled/skipped/todo.
The completed `webkit.log` also reports 16 passed, zero
failed/cancelled/skipped/todo; completion followed the independent finish-review
snapshot, which correctly left that result pending. The implementation handoff
reports 32 Node
checks, lint and production build/typecheck passed; this documentation pass did
not independently rerun those checks.

Historical lookup-extension evidence (before this scan refinement) remains under
`.harness-results/barcode-lookup/finish-review.md` and `finish-verdict.md`. That
review required one existing-copy focus correction, then reached ship. Its
WebKit recheck 15 passed, Chromium confirmation 6 passed and final focus regression
2 passed describe that earlier increment, not the present scan behavior. Earlier
WebKit failures remain in their historical log. The current captures above replace
the older capture set at the same paths; the automatic pair is new evidence.

This documentation pass did not rerun browsers, provider calls, camera tests or
deployments. Physical-phone capture, assistive-technology testing, live catalog
coverage and deployment are outside the finish verdict. Live provider availability
and an explicitly reviewed outbound API path remain rollout considerations.
Root PRODUCT.md, DESIGN.md and design.json are preserved. Their dated historical
status/scope metadata is not proof of current deployment or a standing build-path
preference; no global design refresh is implied by this ordinary extension.


## Optional-cover finish evidence (2026-11-01)

The independent [finish review](../../.harness-results/optional-cover/finish-review.md)
reports **ship for review**, with no blocking findings. It opened all six current
full-page captures: [review desktop](../review/cover-review-desktop.png) and
[mobile](../review/cover-review-mobile.png), [pending desktop](../review/cover-pending-desktop.png)
and [mobile](../review/cover-pending-mobile.png), and [saved desktop](../review/cover-saved-desktop.png)
and [mobile](../review/cover-saved-mobile.png). Review captures intentionally show
the selected option; the browser assertion verifies its initial unchecked state.
Saved captures render generated synthetic artwork above the separate Photos
section. These are implementation evidence, not approved comps or brand assets.

The optional-cover detector reports `[]`. The API evidence records 288 passes and
81 warnings, followed by a full migration downgrade/upgrade. The final Chromium
rerun records six passes and zero failures/skips after an exact accessible-name
selector correction in the earlier 19-pass/one-failure run. The implementation
handoff reports 32 Node checks, typecheck and production build passed. The completed WebKit log also records six passes and zero failures/skips. At this
documentation snapshot the copied-backup cover recovery rehearsal remains
pending; do not infer their completion from the ship verdict. This pass
read UI source/callers and the contract/review evidence, and ran no runtime checks.

The review is limited to the existing factory-light surface. Physical-phone,
manual screen-reader, live-provider and deployment verification remain outside
this evidence. Migration 0012 requires a verified complete database/media recovery
path before nondisposable rollout and refuses downgrade while retained artwork
or source metadata exists. Root PRODUCT.md, DESIGN.md and design.json remain
unchanged; historical global metadata drift is not repaired by this extension.
