# Collection browsing journey — proposed November 4, 2026

Status: visual concept for owner review. The owner chose visual concepts before implementation. No inventory application, deployment, persisted theme or collection data is changed.

## Review of the current implementation

Reviewed merged main 5bd28f5 (#77), the shared design brief (including the designer's separate local November 2 handoff), canonical brand brief, current theme contract, grouped browsing decision, inventory-client.tsx, collection-filter.tsx, grouped-collection.tsx, collection-rows.tsx and copy-detail.tsx. The earlier synthetic three-column desktop/phone captures were inspected as incumbent composition references; their exact controls are historical, not current-main verification.

The current app supports the journey, but collection selection sits among several browse controls. List/Bricks, grouped/individual mode, collection, storage, search and page-local categories compete before the records. The desktop intake rail consumes browsing width even when adding is not the task. Opening a physical copy presents the editor, photo upload and location controls together. Existing strengths worth retaining: server-side grouping and bounded pages, config-driven types/custom collections, explicit revision-checked saves, separate physical-copy identity, retained history, and phone Back navigation.

## Proposed direction

Operate mode. A collection browser with an inspect-then-edit rhythm, retaining the approved ivory/white, charcoal, burgundy, system sans, restrained rules and soft controls. No new logo/mascot or theme role is being approved. Fixed forest navigation is intentionally avoided because the portable theme supports shared text/surface roles rather than an independent dark navigation palette.

1. Open a collection from persistent desktop navigation. Albums, Comics, Movies and named custom collections share one list; custom goals remain separate identities. Phone navigation uses a compact collection chooser. Add a find is available without an always-expanded intake form occupying the browsing rail.
2. Find an item in the selected collection. One collection-scoped search, storage filter, configured artist/series grouping and one List/Covers toggle. Show the applied scope and accurate result/page labels. No page-only count masquerades as a whole collection total. Keep the current server grouping, missing-value semantics and bounded pagination. Changing presentation must not reset the search or selected copy.
3. Open a physical copy into a readable desktop inspector, or a focused phone detail screen. Lead with title/artist, edition/format, physical location, available imagery and notes. Catalog art is labeled separately from a photo of the owner's object. An explicit Edit details action opens the configured form. Existing photo upload, immediate location save, checklist match and catalog review remain separately labeled operations.
4. Edit only after choosing Edit details. Save details and Cancel are next to the form. After confirmed success, retain the selected item and browse context and show a local confirmation. Unsaved or unconfirmed changes must survive Back; switching items/collections needs an explicit keep-editing/discard decision when it would replace the draft. Never imply an unknown or conflicted write succeeded.

## Three concept frames

- Browse: Albums selected, readable list with thumbnail cues, artist grouping and one filter row. Fictional data only.
- Inspect: a narrowed search and selected physical copy, with a read-first inspector and an explicit Edit details action. Collection/list context stays visible.
- Edit and phone: configured album fields with a clear save boundary; phone Back restores collection, query, group, page, scroll and selected-row focus. Save, failure and conflict behavior are requirements, not verified capabilities of these images.

All titles, counts, covers and locations shown in concepts are fictional illustration data. Concept imagery is not evidence of a new API, aggregate count endpoint, thumbnail pipeline, saved browse preferences, routed navigation, accessibility certification or deployed functionality. Current records without cover art need an honest quiet fallback. Custom collection progress must use actual full-goal evidence and remain unaffected by browse filters.

## Implementation after concept review

Start with one shared browse/inspect shell and Albums as the example; preserve config-driven labels and controls so Comics, Movies and custom types fit without separate hardcoded designs. Reuse current endpoints/components where possible. Named location labels and cover thumbnails in result rows require a bounded data-contract/performance review before claiming them implemented. Avoid one request per visible row. Do not add speculative counts or fabricate missing media.

Verify synthetic large inventories, pagination/search/filter return context, long names, absent art, duplicate editions and distinct physical copies, keyboard/focus, 320/390px and desktop widths, theme variants, slow/error responses, dirty-draft navigation, revision conflicts, unconfirmed writes, separate storage/photo saves and custom membership/progress. This concept phase makes no application changes and runs no application regression suite.

## Visual concepts

1. [Desktop collection browser](01-browse-PROPOSED.png)
2. [Search and read-first copy inspector](02-inspect-PROPOSED.png)
3. [Phone Find → View → Edit journey](03-mobile-journey-PROPOSED.png)

Generated with the built-in image tool. Exact prompts and image checksums are in [generation-prompts.json](generation-prompts.json). All three images were visually inspected. One browse-frame correction added a second physical edition to clarify duplicate handling. These are illustrative states, not a connected dataset or executable prototype; exact placement, cover art and field lengths must be verified in the implementation. No app tests ran because no application code changed.
