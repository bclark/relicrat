# Design memory

Updated 2026-11-01. Approved direction, not proof of implementation or deployment.

The authoritative sources remain [the shared design brief](docs/design/README.md),
[the implemented design record](DESIGN.md), [the brand brief](docs/brand/RELICRAT_BRAND.md)
and [the theme contract](docs/decisions/0007-appearance.md). Do not duplicate or
silently override their tokens, boundaries or capability claims.

## Latest approved choice

The owner chose **E: Grouped collection**, then accepted this refinement:

- Unboxed content; avoid decorative frames and filled blocks around intake,
  headings and item data. Keep normal form/control boundaries and focus rings.
- Group visible copies into Albums, Comics, Movies and Other finds.
- Keep title and optional edition close; place location state alongside them.
  Use compact rows with at least 44px interaction targets.
- Do not repeat Saved copy or the type under each item when the list/group already
  provides that context. Save confirmations still belong beside their action.
- Keep unknowns explicit, including Unassigned location; show useful information
  rather than filler. Longer notes remain available in the selected copy.

Source: current Design Lab conversation, “i like it,” after the updated preview.
See [DESIGN_PLAN.md](DESIGN_PLAN.md) for the concrete implementation and checks.
This refinement is integrated in the isolated implementation branch; deployment is recorded separately.

## Established preferences to retain

- Collector-focused, trustworthy, approachable and meticulous.
- Approved ivory/white, charcoal and burgundy factory theme; existing sans stacks,
  owner customization and forest/gold dark companion remain authoritative.
- Desktop entry left, collection right; utilities in the header.
- Mobile utility menu and initially collapsed entry; hiding entry preserves drafts.
- Explicit Save copy for physical-copy creation; photo, catalog and storage saves
  retain their own boundaries. Never infer ownership or verified identification.
- Native React/HTML, plain CSS and current semantic theme variables; no new
  dependency or speculative component framework for this presentation change.

The earlier boxed/roomier E prototype and flat-list approval are historical inputs;
this approved refinement guides future collection-workspace integration. Other
screens and proposed brand assets do not inherit approval automatically.
