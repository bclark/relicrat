---
version: 1
slug: catalog-identification
primary_target: apps/web/app/identification.tsx
related_targets: [apps/web/app/copy-detail.tsx, apps/web/app/globals.css]
---

# Manual catalog identification extension

Mode: Operate. This is a local feature inside the established inventory record,
not a new page or visual identity. Preserve DESIGN.md's system sans, colors,
semantic forms, ruled rows, explicit save states, keyboard focus and mobile stack.
The owner requested catalog identification after trying the working inventory UI.

Purpose: search existing logical catalog entries, optionally choose an edition,
then explicitly save identification on the same physical copy. Sparse catalogs
can add a category, catalog entry and release with separate confirmed saves.
None creates ownership or silently links a copy. Similar names remain distinct.
The existing reconciliation service remains authoritative for revision locking,
retained history and catalog/release consistency. No verified-match claim.

FIRST VIEWPORT: retain add-first intake and collection register. Within the selected
record, Identification follows photos and precedes storage, using a current/selected
comparison, native radio results and release select. Creation and oldest-first
history use native disclosures; no modal, sidebar, decorative imagery or icons.

SIGNATURE INTERACTION: creating a catalog/release only selects it; Save
identification performs the reviewed link. Explicit No release specified removes
a previous edition while retaining its history. Revision conflicts and uncertain
saves lock record writes until Reload copy; there are no automatic POST retries.

Evidence uses desktop1440/mobile390 production captures with labeled synthetic
records. The first trial at 127.0.0.1:56742 is not a test target. No palette, token,
brand or standing build-path preference is changed. Finish review and documentation
comparison use the existing design system, without rewriting its historical evidence.

## Initial inspection

Desktop1440/mobile390 full-page captures were valid, with no overflow, missing
content or animation artifacts. One bounded fix batch removed pagination for
single-page catalog/category/release/history lists, applied the incumbent accent
to native radios and corrected the footer's formerly missing-identification claim.
The manual detector ran once and returned no findings. Confirmation captures and
fresh independent finish review follow that batch; no new design world or tokens.

## Implementation comparison and current evidence

The extension matches the incumbent DESIGN.md and .impeccable/design.json: system
sans, cool page/white paper, cobalt actions, ruled rows, native controls and
existing focus/feedback treatments. Catalog radio results use the existing accent;
creation/history disclosures and bounded Previous/Next controls reuse established
patterns. The responsive shell and add-first composition remain in place. No new
visual world, token, asset, dependency or durable brand/build-path preference is
introduced. DESIGN.md and its sidecar are preserved byte-for-byte.

Final valid captures are .impeccable/review/desktop.png (1440 × 2953) and mobile.png
(390 × 3644). The manual detector ran once with an empty finding list. API tests
passed 90 with zero skips and a full migration round trip; Node proxy tests passed
11 with zero skips; production build/typecheck and worker `sh scripts/test-web.sh`
passed. The final browser suite passed 10 scenarios with zero skips. Real Chrome
creation and reconciliation confirmed that catalog creation does not add ownership,
and two reconciliations plus release removal retain the copy UUID, photo and
storage. Local logs are under
/Users/bryanclark/Developer/relicrat/.harness-results/catalog-identification/.

The fresh independent finish review found the visual/behavior implementation
consistent with this inherited system and requested a PRODUCT.md capability and
evidence correction. That correction is recorded here. The reviewer’s verdict pass scored its sole
documentation fix resolved and returned disposition ship. This is a finish-review
result, not a claim of human PR approval or deployment. Catalog
editing/deleting/merging, automatic matching, authentication and production recovery
remain unfinished. The existing offline synthetic operator backup workflow is not
production recovery, and backup/restore was not rerun for this extension.

## Identification clarity refinement (2026-10-29)

The owner completed the Copper cover exercise but needed guidance to translate
catalog entry/release/identification terminology and find the separate create/save
controls. The record now asks “What is this?”, uses collectible and edition or
variant consistently, and places Add an edition or variant immediately after the
edition selector, before Save details. Saved details remain separate from the
explicit “Not saved to this copy yet” selection. Adding an edition only prepares
it; Save details remains the sole revision-checked assignment action. Native forms
remain siblings so Enter in the new-edition field cannot submit the copy's save.
Unknown editions remain allowed, removal warns that history is retained, and
conflict/uncertain-write locks are unchanged. This is a scoped flow/copy refinement
within the existing visual system; no app-wide style, token or dependency change.

The new-edition disclosure closes after confirmed creation and keeps keyboard
focus on its summary, making the pending selection and primary Save details
visible without an empty creation form between them. The selected/pending group
wraps unbroken collectible and edition names; desktop, tablet, phone and enlarged
text checks cover that boundary. DESIGN.md and its sidecar are unchanged.
