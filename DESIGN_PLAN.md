# RelicRat collection workspace implementation

Updated 2026-11-02. Owner approved the three-column quick-intake/dense-list
exploration: “this looks good let's go with it for now.” This supersedes the
previous two-column integration plan while preserving its unboxed, grouped
collection preference. Local integration is implemented; final verification and
review evidence are recorded in docs/harness.md. Not deployed.

## Observable behavior

- Desktop: quick intake and page-local categories at left, List/Bricks collection
  in the flexible middle, existing full CopyDetail at right. The shell caps at
  1700px. No decorative enclosing cards.
- Below 1180px: collection and detail share a pane with Back to collection.
  Below 760px: details occupy the content area; intake/categories return with Back.
  The same detail component remains mounted so Back preserves its unsaved draft.
- Quick intake starts with Title or barcode, a scan button and Item type. Enter
  or Review item opens the existing type-specific fields. A numeric barcode
  candidate opens review after typing pauses. Hiding review preserves its draft.
- Save copy alone creates ownership. A successful save clears intake and selects
  the new physical copy. Existing photo, catalog, edit and storage saves remain
  independent, with their existing conflict and uncertain-save locks.
- Reuse the existing BarcodeInput and camera decoder, configured providers, match
  review and optional artwork. Typed 12-digit UPC-A / 13-digit EAN-13 codes use the
  same lookup path. Eight-digit input requires scanning or expansion so UPC-E and
  EAN-8 are never guessed. Camera stops when phone details hide its rail.
- Barcode observations remain structured fields with history, separate from notes.
  Only Save copy creates ownership. No provider, schema or media change is made.
- Dense List has Name/Edition/Location columns and 30px desktop pointer rows,
  with at least 44px rows on touch/mobile. Bricks remain unboxed. Categories,
  counts and grouping apply only to the loaded 20-copy page and say so. Search
  and pagination still query the server. Order is retained within each group.
- Inventory responses have location IDs only, so the list honestly displays
  Location assigned/Unassigned. Full location names remain available in details.
- Existing themes and header/mobile utilities remain. Column customization,
  sorting, new category APIs and deployment are deferred; current provider lookup is retained.

## Changed implementation

- `apps/web/app/inventory-client.tsx`: pane composition, progressive intake,
  page-local categories/grouping, view selection and responsive Back/focus.
- `apps/web/app/globals.css`: unboxed three/two/one-pane layout, dense columns,
  touch targets, theme-based hover/selection, intake/scanner sizing.
- `apps/web/app/barcode-input.tsx`: accepts typed quick readings through the existing
  scanner/lookup/review path. The camera implementation is unchanged.
- `apps/web/app/copy-detail.tsx`: omit redundant Saved copy status; existing editor,
  photos, storage, reconciliation and history operations are retained.
- `apps/web/tests/inventory.browser.mjs`: focused new behavior and updated existing
  workflows for collapsed entry and responsive detail navigation.

Movies, CSV import, storage/type filters, whole-collection server grouping,
reviewed lookup and optional covers are retained from current main. The original
designer checkout is preserved; its older runtime replacements are not imported.

No API, database, migration, dependency or brand-asset change. No real collection
records are used by the tests or design artifacts. The accepted offline proposal
remains under docs/design/proposals/three-column-workspace-2026-11-02/.

## Verification and limits

Run `npm test`, `npm run lint`, `NEXT_TELEMETRY_DISABLED=1 npm run build` from
apps/web, then affected browser tests against synthetic loopback fixtures.
Inspect desktop/tablet/390px/320px, selected/empty/expanded entry, List/Bricks,
light/dark and long text. Review keyboard focus and draft retention across Back.
Browser tests mock camera frames and permission outcomes; physical camera and
platform support still need device verification. API/worker/recovery tests are
not required by this frontend-only change and were not rerun. Deployment remains
separate. Exact commands, outcomes and any limitations belong in docs/harness.md.
