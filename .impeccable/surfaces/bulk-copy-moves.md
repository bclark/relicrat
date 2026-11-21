---
name: Bulk physical copy moves
mode: Operate
target: apps/web/app/bulk-move-copies.tsx
---

# Direction contract

THESIS: Explicit selection and review of physical copies; every copy keeps its
identity and movement history. Inherit the collection workbench.
OWN-WORLD: Existing factory/theme colors, system type, native controls and
collection rows. No brand, theme-schema, asset or navigation redesign.
STORY: Select a visible page's copies, choose a physical destination, review old
and new locations, confirm, then inspect saved history. Stale selections and lost
responses stop confirmation until reload and a fresh review.
FIRST VIEWPORT: The selection action sits outside Filters above the results.
Selection counts and cancellation precede copy checkboxes. Review replaces those
rows with per-copy origin/edition/identity and an explicit confirmation.
FORM: Ordinary extension of the incumbent Operate surface, not a new visual world.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish
review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
No shipping raster or comp is added; synthetic screenshot artifacts are evidence.


## Implemented extension and finish evidence · 2026-11-20

Status: implemented for review; independent finish disposition **SHIP** from
`/root/bulk_finish_reviewer`. Merge and deployment status are separate.
The source of the behavior is [the bulk-move contract](../../docs/bulk-copy-moves.md),
`apps/web/app/bulk-move-copies.tsx`, `collection-rows.tsx`, `inventory-client.tsx`
and the scoped bulk selectors in `globals.css`.

The built selection action sits above results outside Filters. Selection uses
the incumbent copy rows with native checkboxes inside 44px labels. The review
lists title, edition, shortened copy identity and previous location, names the
destination in its heading, and requires an explicit review checkbox before the
move. Actions wrap at narrow widths; long review text wraps rather than widening
the page. Selection/review headings receive focus on entry, and a save failure
focuses its alert. Revision conflicts and unconfirmed responses disable further
confirmation until reload and a new review. These are bulk-specific behaviors;
individual-copy location selection retains its existing immediate save.

The extension reuses the current theme's typography, accent, paper, muted text,
error treatment, control corners and focus outlines. Its 12px action gaps and
44px checkbox targets extend existing control patterns; it adds no palette,
font, theme-schema, asset, navigation or system-wide rule. `DESIGN.md` and
`.impeccable/design.json` therefore remain unchanged.

Final synthetic review captures: `.impeccable/review/bulk-desktop-selection.png`,
`bulk-desktop-review.png`, `bulk-desktop-stale.png`, `bulk-mobile-selection.png`,
`bulk-mobile-review.png` and `bulk-mobile-stale.png` (the same directory).
The independent reviewer rechecked all six against the final runtime source at
1440px desktop and 320px mobile and returned SHIP. These are review evidence,
not shipping artwork, approved comps or real inventory. No new raster needs an
asset provenance record. The one detector pass returned no findings (`[]`).

Reported validation for CI run 44842891042: 447 API checks, 37 web checks and the
complete desktop/mobile bulk journey passed, including retained per-copy history,
focus, atomic stale rejection and the unconfirmed-response block. The test-only fixed-width capture helper avoids Chromium breakpoint changes;
final checks and develop integration are recorded in [PR #147](https://github.com/bclark/relicrat/pull/147).
That capture helper changes no runtime UI source. No migration, new
runtime dependency or deployment is included.
