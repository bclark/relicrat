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

The sequence is explicit: scan or use an attached barcode → Find album details →
choose a possible match → review selected fields → Use these details → review/edit
the draft → Save copy or Save details. Reading, searching, reviewing and filling
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
entry available. Lookup is an explicit action with no automatic retry. Opening a
rescan hides the prior lookup; closing it does not repeat a provider request.
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
browser scenarios, current design records and lookup contract. All six final
full-page synthetic captures were visually inspected at desktop/mobile widths:

- [Review desktop](../review/review-desktop.png) and [review mobile](../review/review-mobile.png): manual artist unchecked, suggested fields selected, source/cover uncertainty and separate save visible.
- [Filled desktop](../review/filled-desktop.png) and [filled mobile](../review/filled-mobile.png): preserved manual artist, filled title/format, title focus and separate Save copy.
- [Existing-copy desktop](../review/existing-filled-desktop.png) and [existing-copy mobile](../review/existing-filled-mobile.png): title focus, unsaved-change wording and separate Save details.

These captures preserve the current factory visual system; they are implementation
evidence, not approved comps. Cover artwork is a generated synthetic test fixture,
not a shipping brand asset. The manual detector reports `[]`. The independent
finish review requested one existing-copy focus correction; the subsequent
verdict reports **ship**, with that sole finding resolved. Evidence is recorded
under `.harness-results/barcode-lookup/finish-review.md` and `finish-verdict.md`.
Inspected logs report WebKit recheck 15 passed, Chromium confirmation 6 passed and
final focus regression 2 passed, each with zero failures/skips. Earlier WebKit
failures remain in their historical log and are not the passing evidence.

This documentation pass did not rerun browsers, provider calls, camera tests or
deployments. Physical-phone capture, assistive-technology testing, live catalog
coverage and deployment are outside the finish verdict. Live provider availability
and an explicitly reviewed outbound API path remain rollout considerations.
Root PRODUCT.md, DESIGN.md and design.json are preserved. Their dated historical
status/scope metadata is not proof of current deployment or a standing build-path
preference; no global design refresh is implied by this ordinary extension.
