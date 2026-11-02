# Design Implementation Plan: RelicRat collection workspace

## Summary

- **Scope:** signed-in collection workspace, desktop and mobile.
- **Target:** shared `CollectionRows`, InventoryClient, GroupedCollection and existing CSS.
- **Winner:** E, Grouped collection, refined to remove enclosing content boxes and tighten item data.
- **Approval:** 2026-11-01, owner: “i like it” after the revised preview.
- **Status:** implemented and synthetically verified. Deployment is recorded separately in the shared brief.

The collector should scan Albums, Comics, Movies and Other finds, recognize each copy by
its title and edition, and see its location state without reading repetitive
status labels. Keep the desktop entry form at left and the collection at right.
Retain header utilities and the mobile menu/collapsible entry behavior already
implemented. Save copy remains the explicit ownership-creation action.

## Approved appearance

- Remove decorative enclosing frames, background blocks and padding from intake
  and collection content. Keep ordinary input/button borders and keyboard focus.
- Use plain type-group headings and restrained horizontal rules; no filled group
  header boxes, cards around records, new icons or decorative illustration.
- Put title and optional edition adjacent, wrapping naturally as needed. Align a
  quiet location state alongside them. Keep each interactive row at least 44px.
- Omit repeated Saved copy, Open this physical copy and redundant per-row type
  labels where the surrounding list/group already supplies that information.
- Keep unknown information explicit: omit an unknown edition rather than invent
  one, and use Unassigned for a copy with no physical location.
- Keep longer notes available in the existing selected-copy view. A notes-only
  provisional copy must still have a recognizable title through `copyName`.
- Preserve approved palette, system/body/heading font settings, density controls,
  control corners and error styling. Use existing semantic theme variables.

Example of the intended grouping and proximity:

    Albums                                      2 on this page
    Glass Arcade   Blue vinyl                   Location assigned
    Night Garden   Second pressing              Unassigned

    Comics                                      1 on this page
    Moon Harbor #08   Alternate cover            Location assigned

Actual location names in the mockup were synthetic fixture data, not evidence of
a production list capability. The inventory response currently exposes only
`storage_location_id`. Reuse Location assigned/Unassigned unless a suitable
already-loaded map supplies a real name. Do not introduce one request per row,
a new API, or silently use a UUID as a display name to reproduce the mockup.

## Files to change

- [x] `apps/web/app/inventory-client.tsx`: grouped rendering of the existing page of copies; compact title/edition/location markup.
- [x] `apps/web/app/globals.css`: unboxed intake, group headings, compact rows and responsive wrapping; update existing desktop/tablet/mobile intake overrides together.
- [x] `apps/web/tests/inventory.browser.mjs`: focused grouped-list, interaction and responsive regressions using synthetic fixtures.
- [x] `apps/web/README.md`: document the changed browsing presentation and page-local counts.
- [x] `DESIGN.md` and `.impeccable/design.json`: merge descriptions after integration, reflecting actual implementation rather than promoting the old prototype.
- [x] `docs/design/README.md` and `docs/harness.md`: implementation status and actual verification evidence.

No API/model/migration, new runtime dependency, media asset, or theme schema
change is needed. The temporary lab and preview routes have been removed.

## Implementation steps

1. Recheck Git state, shared design brief, current source, theme contract and
   calling tests. Preserve the existing uncommitted navigation work and unrelated
   untracked root lockfile; do not overwrite or discard them.
2. Derive four render groups from the current `items` page: record → Albums,
   comic → Comics, movie → Movies, other → Other finds. Use loaded type-definition plural labels
   when available. Preserve order within each group and omit empty groups.
   A small local mapping/filter is sufficient; do not introduce a grouping service.
3. Keep the original `items`, selected UUID, query, offset, page size and `more`
   calculation intact. Group only the existing 20-copy response page. Counts must
   say on this page or shown, never imply whole-collection totals. Search must
   continue querying the server, with its existing literal-match behavior.
4. Reuse `copyName(copy)` so artist/album titles, comic issue numbers, notes-only
   provisional records and personal labels retain their current meanings.
   Display an existing personal edition label adjacent to that title. Do not
   relabel a tentative catalog link as verified or infer edition information.
5. Keep real inventory-row buttons, UUID keys, `aria-pressed`, disabled-in-flight
   behavior and opening/focusing the existing `CopyDetail`. Preserve all of its
   photo, edit, identification, movement and history operations. The lab's small
   editor was illustrative, not a replacement for that transactional component.
6. Remove the intake's decorative border/fill/padding at every existing breakpoint.
   Keep fields readable and labeled. Replace vertical stacks of routine row labels
   with the approved compact title/edition and location layout. Use spacing and
   rules to group sections; keep a distinct selected wash and visible focus ring.
7. Keep Appearance, collection settings and Sign out in the header; retain the
   mobile Menu, Escape/outside-click dismissal, focus restoration and initially
   collapsed intake. Opening/closing entry must preserve its mounted draft.
   Do not restore the removed Add a find jump button.
8. Preserve all loading/error/empty/uncertain-save paths and separate saves. No
   retry, new ownership write, catalog match, location change or metadata rewrite
   should be caused by grouping, selecting or browsing a category.
9. Run the checks below, inspect actual app captures, merge the design record,
   and report implementation/deployment status separately.

## Component API

- **Props:** no new public component API is required; retain InventoryClient and CopyDetail contracts.
- **Derived values:** page-local ordered type groups and optional visible-group counts.
- **State:** reuse existing copy array, selection, search, pagination, entry/menu visibility, busy and uncertain-save state.
- **Events:** retain current create, search, reload, page navigation, row selection and detail callbacks.
- **Saved data:** no changes; grouping is presentation only.

## Required UI states

- **Loading:** existing announced loading text and static skeletons, without fabricated records or group totals.
- **Empty:** first-find guidance for an empty collection; different guidance for no search matches and an empty later page.
- **Error:** explicit read failure with Reload inventory; do not show a stale group count as a confirmed result.
- **Disabled:** existing save locks and pagination boundaries, while retaining minimum target sizes.
- **Validation:** title requirement and field constraints remain intact; first invalid input receives focus.
- **Success:** show the existing save confirmation at the action boundary; do not repeat Saved copy under every item.
- **Uncertainty/conflict:** require reload/review as before; do not automatically retry a write.
- **Long content:** titles, editions and location state wrap without overlap; optional details cannot displace the title completely.

## Accessibility checklist

- [x] Group headings label semantic sections; list rows remain actual buttons.
- [x] Title/edition text and row accessible names still identify the intended physical copy.
- [x] Keyboard sequence follows the visual order; row selection focuses the existing copy heading.
- [x] Focus rings remain visible; selected state is represented with `aria-pressed`.
- [x] Touch targets stay at least 44px, including compact density and mobile intake controls.
- [x] Approved and custom light/dark themes retain contrast and readable fields.
- [x] Text zoom, long labels and 320px layouts have no horizontal overflow or hidden essential actions.
- [x] Reduced-motion preferences remain respected; no automatic ornamental motion is added.
- [x] Announced loading, validation errors and save confirmations remain understandable with a screen reader.

## Testing checklist

- [x] Add mixed Album/Comic/Movie/Other fixtures; verify every copy appears exactly once in the correct nonempty group.
- [x] Verify stable selection/editing across search, reload and group/pagination changes, retaining the same copy UUID.
- [x] Verify group counts describe the current page; a type appearing on multiple pages is not presented as a complete inventory total.
- [x] Verify generic/notes-only titles, artist/comic naming, missing edition, missing location and long text.
- [x] Verify no repeated Saved copy row text while legitimate action confirmations remain.
- [x] Verify creating a copy, uploading a photo and choosing storage still save separately with existing conflicts/uncertain outcomes.
- [x] Verify header utilities, mobile menu, collapsed-entry draft preservation, keyboard focus and no overflow at desktop/tablet/390px/320px.
- [x] Run `npm test`, `npm run lint` and `NEXT_TELEMETRY_DISABLED=1 npm run build` from `apps/web`.
- [x] Run affected real-browser checks on the disposable synthetic stack; report exact selections and any skipped integration cases.
- [x] Inspect actual desktop/mobile, empty/populated and supported theme captures. The prototype had static/build checks, not browser verification.

API/worker tests are required if implementation expands into API/domain changes;
that expansion is not part of this plan. No tests or images may reuse real data.

## Design tokens

Reuse page, paper, ink, muted, rule, accent, accent-text and soft roles from the
existing theme. Keep current font, density, spacing and control-radius variables.
Unboxed content does not remove control boundaries or expand the import schema.
No new semantic color, external font, layout provider or component library.

## Migration, rollout and remaining risks

No database migration is proposed. This is a frontend presentation change; build
and review it before considering deployment. Existing authentication, backup and
production-hosting limitations are unaffected. Review merged/deployed state
independently of these local files.

The key integration risks are misleading page counts, reordering/dropping copies,
losing selection or unsaved drafts, cramped controls under custom themes, and
mistaking synthetic location labels for available API fields. The tests above
address these boundaries. Prototype-only feedback storage and mock saves must not
ship with the application.

## Out of scope

New category filters, global category totals, sorting APIs, image grids,
valuation, new catalog behavior, automated matching, changing ownership filters,
new storage-name endpoints, and deployment are deferred. No permanent new mascot
or logo asset was approved by this exploration.

## Evidence and lifecycle

The owner selected E, requested unboxed/tighter rows and removal of redundant
status, then accepted that refinement. The lab's builds/TypeScript and bounded
feedback-parser/export checks passed; a static E render verified all five fixture
rows, group labels and useful edition/location text without repeated Saved copy.
No lab server or browser was opened under the supplied workflow. Those checks do
not establish actual app integration, visual approval of implementation, or API
correctness.

On final acceptance, 42 manifest-listed temporary files were removed from
`apps/web/.claude-design/`, `apps/web/app/design-lab/` and
`apps/web/app/design-preview/`. Only lab-created untracked files were deleted;
pre-existing work was preserved. Offline lab links and temporary routes therefore
no longer exist. The separate Stageshow demo was not part of this cleanup.

Generated following the supplied Design Lab workflow; application implementation
remains pending.

Post-cleanup verification: `NEXT_TELEMETRY_DISABLED=1 npm run build` from
`apps/web` passed production compilation and TypeScript. Its route table no
longer includes /design-lab or /design-preview. Static checks confirmed both route
directories and the temporary lab directories are absent; `git diff --check`
passed. The existing root-lockfile warning remains; generated next-env.d.ts churn
was reverted. No browser, API, worker or recovery tests were rerun for cleanup.

## Verification record

See the 2026-11-01 unboxed-workspace entry in docs/harness.md for exact executed
checks, initial failures and limits. Checklist items describe the covered regression
contract, not a claim of physical-phone or assistive-technology manual testing.
Existing whole-collection server groups and Movie support are preserved from main;
Other uses its configured plural label (currently Other).
