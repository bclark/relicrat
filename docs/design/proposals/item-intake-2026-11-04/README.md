# Add an item — visual concept, November 4, 2026

Status: proposed for owner review. No application code, API, schema, owner data or deployment changed. This is a standalone interactive concept using fictional data and simulated camera/catalog/save outcomes. It does not access a camera, a provider, the inventory API or browser storage.

Open [the concept](index.html). Try Albums, Comics, Movies, the fictional Orbit Rangers collection and Other. The concept controls at the bottom select simulated scan/save outcomes.

## Evidence and problem

Based on merged main `3fb956b` (#79), the shared design brief, current theme contract, architecture boundaries, `inventory-client.tsx`, `custom-collections.tsx`, `barcode-input.tsx`, `barcode-lookup.tsx`, `observation-input.tsx`, `custom-field.tsx` and built-in type JSON. The app now has one browse list but intake still has separate generic quick-entry and expanded forms, barcode/candidate/apply review, plus a second custom-figure intake under collection tools. A custom collection can also expose the generic entry, where saving does not add a member to that custom collection. These are verified implementation observations, not assertions about private records.

The concept extends the approved visual world: supported ivory/white surfaces, charcoal text, burgundy actions, system sans and existing focus/control shapes. It is an Operate surface. It introduces no logo, palette, theme role or broad browsing redesign. Root PRODUCT/DESIGN contain historical implementation statements; current code and exact merged source take precedence for capability claims.

## Proposed flow

- Open Add an item from any collection, retaining the originating collection/filter/page/scroll context. Use a focused inline/full-width task area with Back; do not put intake, browse and the inspector in competition. The prototype's desktop navigation is context; phone uses the collection selector within the task.
- The selected browse collection sets the destination. From Movies, the heading is **Add to Movies** and scanning/title entry comes first, with no repeated collection picker. The same rule applies to Albums, Comics, Other and named custom collections on desktop and phone. Only entry from **All items** shows a flat destination picker, initialized from the saved default; the destination remains explicit before saving. Never silently save a custom member to Other. Selection changes that would replace a dirty draft require Keep editing or Discard and switch; Back preserves the draft. Existing independent drafts must survive integration, rather than being silently merged or discarded.
- Scan when the definition supports barcode formats, or enter the configured fields immediately. Title is the only required field. Album keeps artist before album title. Use configured ordering, limits, autocomplete and bounded choices with Other where already supported. Custom radio, select, multiselect and text follow the saved definition; unknown remains distinct from false/empty.
- Successful scanning starts lookup automatically when configured, without a barcode-confirmation gate. With no provider, keep the barcode and allow manual entry. Permission denial exposes typed-barcode fallback. No match and provider failure keep the draft usable. Stop camera tracks on leaving/hiding the task; abort stale requests.
- Choose a possible match to review it in the final form. Blank fields may be provisionally filled; existing manual values are kept unless the owner explicitly selects the corresponding suggestion. Per-field choices are editable/reversible. The optional catalog cover starts unchecked, retains provider/candidate provenance and remains distinct from photos of the owner's object. This proposes replacing the separate Use these details step with the same reviewed final form; it does not remove candidate choice or overwrite review.
- Save item is the only ownership-creation action. Show Saving and lock duplicate submissions/navigation that could replace the save target. On confirmed success: “North Window added.” and “Saved in Albums.” Offer Add another item and View item. Photos/storage remain separately saved after creation. Custom creation must retain the current request identity and definition revision; checklist matching/eligibility stays explicit after creation.

## Configuration and capability boundaries

The [config snapshot](config-snapshot.json) copies the shipping built-in definitions and adds one clearly fictional custom definition for the visual example. Existing APIs deliver two definition shapes; implementation should use a small presentation normalization and existing components, not introduce a runtime plugin/provider framework or require a schema migration merely to draw one form.

- Albums: MusicBrainz provider, artist/title/format mapping, optional artwork supported.
- Movies: UPCitemdb provider with **title only**, no configured cover. The concept must not imply automatic studio/format filling or artwork support.
- Comics: barcode capture supported, **no configured lookup**. Enter series, issue and publisher manually, with existing observation suggestions.
- Custom collection: title/typed optional fields, **no installed lookup/scanning capability** in the current authoring schema. Do not invent barcode/provider configuration for this path.
- Other: generic definition and supported barcode capture, without implying lookup.

The prototype is deliberately not an API-contract test. Its barcode values and lookup results are fictional demonstrations, not checked identifiers or provider responses. The typographic sleeve is explicitly fictional artwork. Add another clears only the confirmed saved draft, not unrelated work.

## Failure and navigation requirements for implementation

Preserve dirty form text, field-control values, barcode, match selections and cover choice through Back within the mounted session. Reload/offline persistence remains out of scope unless separately designed. Discard should invalidate pending scan/lookup responses and never let old results populate the new destination. Outdated definition revisions/conflicts require reload/review while retaining entered values.

Known rejected saves retain the draft and allow explicit retry. Unknown saves must not display success or offer a blind new creation. Ordinary intake uses its current inspect-before-retry protection; custom intake preserves request identity and supports only its existing safe same-save flow. The concept's Check collection simulates the case where the original save is found; production must also handle absent, ambiguous and unavailable checks and must not infer creation from a similar title. Failed cover ingestion follows the API's transactional outcome; it must not silently duplicate an item or silently drop opted-in artwork.

After concept approval, one focused implementation PR should integrate the shared entry destination and review surface using current endpoints. Keep collection administration/imports outside the creation form. No deployment is authorized by concept review alone.

## Verification scope

Concept verification uses desktop and 390px phone rendering, all five destination configs, title-only save, optional fields, simulated album/movie lookup, Comics scan-only fallback, custom controls, optional art, dirty switching/Back, save rejection and unknown outcome. No application/API suite is claimed. Detailed production tests must cover actual synthetic endpoints, configured field selection, provenance, maximum lengths, stale responses, provider/cover failures, definition conflicts, duplicate prevention, draft preservation and narrow/theme/keyboard layouts before implementation is reviewable.

### Concept check results

`node /private/tmp/check-intake-concept.cjs` completed 10 scenario groups at 1440px and 390px, with no browser errors or page overflow. The initial harness attempt tried to select a hidden simulation control; the recheck opens Concept controls first. Desktop/manual entry, album review and optional cover, custom controls/confirmation, Comics scan-only, movie title-only, manual-value protection, Back/dirty switching, three scan failure paths, known save rejection and unknown-result inspection passed in the final run. These are tests of this simulated artifact, not the shipping app or real providers. Screenshot review used one initial batch and one confirmation batch after clarifying the exact suggested values beside their opt-in controls.

- [Desktop start](01-desktop-start-PROPOSED.png)
- [Desktop review](02-desktop-review-PROPOSED.png)
- [Phone review](03-phone-review-PROPOSED.png)
- [Phone custom collection](04-phone-custom-PROPOSED.png)
- [Phone confirmed save](05-phone-saved-PROPOSED.png)
- [Machine-readable concept verification](verification.json)

### Owner correction — selected collection is already known

The owner found the repeated Collection dropdown redundant after choosing Movies in navigation. Updated the concept to inherit that scope, use “Add to Movies” (or the selected name), and omit the form picker. All items retains the picker because a physical copy needs a destination. Back returns to its originating scope; browsing and intake destination are separate state. This correction remains a concept change only.

Correction verification: `node /private/tmp/check-intake-destination.cjs` passed six focused checks at desktop/390px. Albums/Movies and phone custom intake have no repeated picker; All items retains its destination selector and Back preserves its destination/draft. Album review/artwork and named custom saves still work. No browser errors or phone page overflow. Updated desktop/phone screenshots were inspected together; [Movies example](06-movies-scoped-PROPOSED.png) and [correction receipt](destination-verification.json). Earlier verification.json records the preceding concept revision.
