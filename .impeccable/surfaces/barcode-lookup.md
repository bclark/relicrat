---
version: 1
slug: barcode-lookup
primary_target: apps/web/app/barcode-lookup.tsx
related_targets: [apps/web/app/barcode-input.tsx, apps/web/app/barcode-scanner.tsx, apps/web/app/inventory-client.tsx, apps/web/app/copy-details-form.tsx, apps/web/app/globals.css]
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
confirm an edition. Provider references are visible during review but are not
persisted as separate provenance evidence in this increment.

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

Cover images are contained previews with descriptive alternative text and a text
fallback when unavailable. They are separate from owned-copy photos. The source
link opens the provider release with no referrer. Camera frames stay on-device;
the API sends the barcode and cover identifier to the configured public services,
not collection records or owner credentials.

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
