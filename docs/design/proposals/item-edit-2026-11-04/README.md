# View and edit an item — visual concept

November 4, 2026. **Proposed for owner review; not implemented or deployed.**

Open [the interactive concept](index.html), or serve this directory on Mac loopback.
All examples are fictional. Values live only in page memory; reload resets them.
No API, camera, provider, upload or real inventory is accessed. The photo control
simulates confirmation without reading or sending the selected file.

## Direction contract

- **Thesis:** understand a physical copy first, then edit only its details in one focused form.
- **Own world:** extend the approved RelicRat intake composition, ivory/white, charcoal, burgundy, system sans and native controls. After hours uses the existing API preset palette. No new brand or theme tokens.
- **Story:** collection → item → Edit details → Save changes → read-only saved confirmation. Back preserves the page-local draft and browse search/filter/scroll.
- **First viewport:** collection context, a clear item title, readable details and one Edit details action; the editor has configured labels, artist before album title, and one Save changes. No repeated collection chooser.
- **Form:** a narrow extension of the approved intake world, built directly as a browser concept. No concept roll or new visual identity is needed. Desktop retains the collection rail; phone stacks the task. Optional details remain optional.

## Try it

1. Edit the album's pressing, go Back to item, then Continue editing. Save changes.
2. Back to Albums, enter a search, open the item, then Back. Search is retained.
3. Change storage: choosing Box B confirms immediately. This preserves the owner's earlier decision.
4. Use the controls below the concept to switch Comics, Movies or a fictional custom figure collection. The custom Head variant offers one radio choice, with Not entered; its boolean answer can be explicitly cleared.
5. Simulate a known rejection, conflicting edit or unknown save. Drafts remain available. Unknown/conflict saves lock until saved-state inspection; no automatic retry. The unknown example models a committed save with a lost response, not proof about a real server.
6. Preview the existing After hours colors.

## Implementation implications to review

The current details API updates title, edition, type-specific observations, barcode,
custom values and an explicitly selected catalog cover with revision guards.
It does **not** edit notes, move storage or upload photos in the same transaction.
This proposal therefore uses **one details save**, with independent immediate
storage confirmation and a separate Upload photo. An atomic all-in-one save
would need a separately designed API contract, not a visual promise.

Current creation requires a meaningful title; editing legacy provisional copies
can retain a missing title under existing API rules. The production implementation
must preserve those legacy cases rather than blindly copy the demo's required
attribute. Notes remain read-only until a deliberate API extension.

Production must reuse the actual collection JSON, owner visibility preferences,
autocomplete and free-text Other format behavior, retained hidden values, typed
custom controls, structured barcode validation and reviewed suggestions/artwork.
The small local field arrays are illustrative, not a replacement schema. Built-in
type correction belongs under an explicit advanced action; custom membership
remains pinned. Catalog identity, edition linkage, checklist qualification,
provenance/history and physical-copy UUID must remain intact. Existing barcode,
artwork attribution and history operations must stay reachable.

Draft persistence is page-local, not offline storage or refresh-safe. The demo's
single-result browser illustrates preserved context, not real search or paging.
Successful photo uploads, network conflicts and preservation must be tested with
synthetic API integration when implemented. This concept is not that evidence.

## Verification

[Interaction checks](verification.json) cover confirmed-save feedback, draft Back,
search Back, unknown-save inspection, independent storage preservation, custom controls, dark preview and horizontal
overflow at 320/390/1440 widths. Screenshots show desktop view/edit, phone view/edit,
custom controls and recovery. An initial capture script waited on closed demo
controls; opening those controls corrected the script. No app test suite or
production rollout was run for this proposal.

Independent review found and corrected two prototype issues: detail drafts now exclude independent storage/notes, and an unconfirmed save stays visibly marked until inspection. The corrected storage sequence was checked in the browser.

Final independent verdict: ship for the scored concept fixes, including clear-answer persistence. Global design documentation required no changes. This does not approve app implementation or deployment.
