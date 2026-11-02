# Design memory

Updated 2026-11-02. Approved direction; local implementation and deployment are separate statuses.

The authoritative sources remain [the shared design brief](docs/design/README.md),
[the implemented design record](DESIGN.md), [the brand brief](docs/brand/RELICRAT_BRAND.md)
and [the theme contract](docs/decisions/0007-appearance.md). Do not duplicate or
silently override their tokens, boundaries or capability claims.

## Latest approved choice

The owner approved the three-column workspace and its refinement on 2026-11-02:

- Quick intake and categories left; dense List or unboxed Bricks in the middle;
  selected-copy information at right. Below desktop widths, details replace the
  collection with Back; phone details also replace the intake/category rail.
- Start intake with one Title or barcode field and easy Scan access. Show Item
  type early. Enter/barcode expands review; Save copy creates ownership.
- List should resemble Finder's density: aligned columns, short rows and quiet
  alternating fills. Retain larger touch targets. Customization comes later.
- Preserve the earlier E preference: unboxed content, compact useful facts, no
  redundant Saved copy label under each item, explicit unknown location state.

Source: “this looks good let's go with it for now,” following the updated preview.
Local application integration is implemented, not deployed. See DESIGN_PLAN.md
and docs/harness.md for behavior, verification and limits. Prototype scans were
simulated; the integration retains the existing camera decoder, configured lookup providers
and optional cover review. Codes remain structured observations, separate from
notes. Typed quick input supports UPC-A/EAN-13; scan eight-digit codes to preserve
their format. Existing Movie, CSV, storage and whole-collection browsing remain.

## Established preferences to retain

- Collector-focused, trustworthy, approachable and meticulous.
- Approved ivory/white, charcoal and burgundy factory theme; existing sans stacks,
  owner customization and forest/gold dark companion remain authoritative.
- Desktop entry/categories left, collection middle, selected copy right; utilities in the header.
- Mobile utility menu and initially collapsed intake details; the quick field and type stay visible. Hiding entry or returning from details preserves drafts.
- Explicit Save copy for physical-copy creation; photo, catalog and storage saves
  retain their own boundaries. Never infer ownership or verified identification.
- Native React/HTML, plain CSS and current semantic theme variables; no new
  dependency or speculative component framework for this presentation change.

The earlier boxed/roomier E prototype, flat list and two-column layout are historical inputs;
the latest approved three-column refinement guides the collection workspace. Other
screens and proposed brand assets do not inherit approval automatically.
