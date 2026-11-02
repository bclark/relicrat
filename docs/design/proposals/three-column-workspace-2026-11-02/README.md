# Three-column workspace exploration

2026-11-02 · Proposed, not integrated or deployed. Fictional records only.

The owner requested intake/categories at left, a list or brick collection in the
middle, and details for the selected physical copy at right. This explores that
composition while retaining the approved unboxed, compact direction. The earlier
two-column implementation plan remains historical approved intent; this proposal
received positive owner feedback; the intake/density refinements below implement
the next requested exploration. Application integration remains separate.

## Design plan and review

Palette: ivory `#F7F3E9`, white `#FFFFFF`, charcoal `#302B28`, muted
`#595650`, rule `#C6C9C3`, burgundy `#823B3D`. Reuse the approved system sans
family: 24–28px workspace heading, 18–20px section headings, 16px item names,
14px list names and facts in the refined dense view. Left alignment throughout; no new brand assets.

The collection receives the flexible width. Intake is a narrow rail; the detail
pane is wide enough for readable facts. Separation comes from space and a single
vertical rule between working regions, not boxes around their content.

    Desktop >= 1180px
    [ intake / categories ] [ collection: list or bricks ] [ selected copy ]
            232px                    flexible                  320px

    Tablet 760–1179px
    [ intake / categories ] [ collection OR selected copy + Back ]

    Phone < 760px
    [ quick entry / scan / item type ]
    [ category filters ]
    [ collection OR selected copy + Back ]

Review against the brief: a generic masonry gallery would reintroduce card boxes
and spread item metadata out. Here the brick option uses unframed text-led tiles
with nearby edition/location information. List is the initial view because
compact scanning was the owner's strongest prior preference. Both are available
for direct comparison. No automatic animation.

## Prototype behavior and boundaries

Open `index.html` directly. List/bricks, category filtering, search, selection,
back navigation, progressive intake review and in-memory creation work. Refresh
resets the fictional collection. No network, authentication, persistent storage,
uploads, production settings, ownership writes or real editing are connected.
The detail content is a composition study, not a replacement for CopyDetail.

Category totals count this entire small fixture, not API/global inventory totals.
Actual category filtering, location-name resolution and full detail integration
must be traced against current production contracts before implementation.

Responsive choice: do not compress all three columns onto tablet/phone. Detail
replaces the collection at those widths and returns to it explicitly, preserving
search, filters, view choice and the intake draft. Desktop can compare the
selected row and detail side by side.

## Verification

Headless Playwright checked 1440, 1024, 390 and 320px widths, list/bricks,
selection/back, search, category filtering and in-memory intake. No horizontal
overflow or script errors were found. Desktop list and phone bricks screenshots
were visually inspected. The first browser launch was blocked by the filesystem
sandbox; the same check passed outside it. No app build, API or deployment checks
were needed or run for this standalone proposal. `git diff --check` passed.

## Requested refinement: quick intake and dense list

Source: owner feedback on 2026-11-02, with a macOS Finder screenshot as the
specific density reference. The owner liked the composition and asked for one
initial text field, easy barcode scanning, expansion on Enter/barcode, early item
type and a much denser list. Customization is deferred.

- Keep Title or barcode plus a 44px Lucide ScanBarcode button and Item type visible
  from the start, at all widths. Continue is a touch alternative to Enter.
- Enter expands review; an 8–14 digit candidate expands after a brief typing pause
  so a hardware scanner can finish sending all digits. This is prototype input
  recognition, not barcode validation, catalog matching or an ownership write.
- The scanner button opens an explicitly simulated sample scan. Actual camera
  permission, format validation, lookup/review and error handling need production
  integration. No camera is accessed by this concept.
- Expanded review contains title, optional notes and explicit Save copy. A barcode
  alone is not treated as meaningful identification. No record is created until
  the user supplies a title and saves. Hide details preserves the mounted fields.
- Finder-inspired list uses aligned Name/Edition/Location columns, alternating
  row fills, a clear selected row and 30px rows on a desktop pointer. Touch/mobile
  rows retain at least 44px height; narrow screens put edition below name. Brick
  view remains available. No column customization, resizing or sorting added.
- Barcode icon reused from the existing temporary Stageshow Lucide package;
  embedded SVG only, no app dependency installed.

Verification rerun: the same headless script passed all four widths and both
views, search/filter/selection/back and intake creation. Added assertions verify
Enter does not create ownership, the entire 12-digit barcode reaches review,
barcode review does not create ownership, early type visibility and scan focus.
Desktop and phone list captures were inspected. One test run failed because the
check used an unsupported Playwright `isFocused` method; it was corrected to
inspect `document.activeElement`, then passed. These are prototype checks only.

## Integration review

The approved composition is integrated onto current main for a PR review. The
application retains its existing Movie/import/group/filter/scanner/provider/cover
workflows; this earlier offline prototype remains an illustrative design artifact.
See the root DESIGN_PLAN.md and docs/harness.md for actual behavior and validation.
The layout is not deployed by this review.
