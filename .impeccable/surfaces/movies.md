---
version: 1
slug: "movies"
mode: Operate
primary_target: "apps/web/app/collection-setup.tsx"
related_targets: ["apps/web/app/inventory-client.tsx", "apps/web/app/copy-details-form.tsx", "apps/web/app/copy-detail.tsx", "apps/web/app/observation-input.tsx", "apps/web/app/csv-import.tsx", "apps/web/app/grouped-collection.tsx"]
---

# Movies: setup, entry, editing, import and browsing

Status: implemented for review on 2026-11-01; not deployed. This is an ordinary
Operate extension of the existing collection workspace. The collector can choose
Movie as a new-find default, record a movie or box-set title, review a Blu-ray.com
CSV, and find the resulting physical copies by title. Exact domain and mapping
contracts remain in [the Movie contract](../../docs/movies.md) and
[ADR 0010](../../docs/decisions/0010-movies.md); the shared visual authority remains
[DESIGN.md](../../DESIGN.md) and [the design brief](../../docs/design/README.md).

## Composition and controls

Preserve the approved factory ivory/white surfaces, charcoal text, burgundy
primary actions, system sans typography, soft corners and ruled sections. Reuse
the existing desktop intake/selected-copy and collection columns; mobile stacks
in the same semantic order. Setup and import expand inline before the workspace.
No new assets, design tokens, navigation, layout system, component library or
external font is introduced. User photos remain collection data.

Collection setup retains three named steps, native checkboxes/selects and one
explicit Save setup. The preview is clearly an example that creates no copy.
Movies can be enabled, made the default, and assigned visible optional fields.
Hiding fields preserves saved observations; existing populated values remain
editable. Imports do not reclassify existing copies or change owner preferences.

Movie entry leads with Movie or box-set title. Format and Studio follow when
shown, then optional edition/packaging and notes. Format uses a native select:
Not specified preserves unknown, named choices aid entry, and Other reveals a
labeled custom-format input with focus moved there. Studio reuses the native
saved-value datalist; it never chooses a value automatically, and suggestion
failure leaves manual entry available with an explicit hint.

**The Physical Copy Rule.** A movie release or box set is one owned object.
Titles, barcodes, product IDs, disc counts and title groups do not merge, split
or establish shared catalog/release identity. Save copy and revision-checked Save
details remain explicit. Existing UUID, catalog links, photos, storage and history
survive editing; type changes retain Album, Comic and Movie observations. The
copy edit-history disclosure names changed Movie format/studio values and unknowns.
Photos and storage retain their existing separate save boundaries. Uncertain or
stale saves require reload/review; no automatic write retry is introduced.

Movie scanning records only a barcode observation. Its type config has no lookup
provider; it neither identifies a film nor fetches catalog artwork. No Movie
provider, account, credential or new network access is part of this extension.

## Reviewed CSV and title groups

Import CSV adds Blu-ray.com Movies to the existing native export selector. Keep
choose → preview → acknowledge → import. Show the copy count, mapping disclosure,
first ten examples, bounded row notes/errors, repeated-ID warning and changed-file
duplicate limitation before the unchecked acknowledgment and Import N copies.
Preview writes no inventory; confirmation binds the same file digest and commits
the whole batch transactionally. Exact-file retry returns its existing batch.

**The Source Evidence Rule.** Each export row creates one provisional copy after
confirmation, regardless of disc count. Original columns remain immutable private
provenance rendered as literal text. Unknown counts stay unknown, conflicting or
invalid barcodes stay source evidence with notes, and counts never infer 4K.
Source dates, prices and IDs do not become authoritative identity or valuation.
Import history retains paginated source rows and links to each physical copy.
The actual owner CSV stays outside Git, test fixtures, worker tests and live data;
verification uses independently generated rows.

Movies appears in the ordinary collection-type filter. Grouped collection browses
saved titles, with independent group/member paging and selected physical-copy
rows. Literal title/studio/format/barcode/notes search and storage filtering retain
the incumbent controls, statuses and draft-preservation behavior. Grouping never
merges copies or establishes a shared movie identity.

## Review evidence and limits

Opened and visually inspected all eight final full-page captures under
`.impeccable/review/`: `movie-{setup,edit,import,collection}-{desktop,mobile}.png`.
Desktop and 390px mobile preserve readable labels, native controls, explicit saves,
custom-format entry, history, import notes and unchecked confirmation. Long mobile
pages follow the incumbent order without visible clipping or horizontal overflow.
The independent finish review in `.harness-results/movies/finish-review.md` returned
ship, with no requested UI fixes or recapture; that verdict is review suitability.

Existing final receipts under `.harness-results/movies/` were inspected, not rerun
by the documenter: `api-final.log` records 322 passed and 89 warnings plus the full
migration downgrade-to-base/upgrade-through-0013 round trip. `confirm-build.log`
records production build/typecheck, lint and 33 passing Node checks.
`chromium-final.log` and `webkit-final.log` each record two passing Movie scenarios,
including 389 generated imports; `barcode-cover-final.log` records four passing
regressions and `import-final.log` one. These checks report zero failures/skips.
`runtime.json` records reviewed source/runtime matching; `design-detector.json`
is `[]`. Earlier failed receipts are superseded only by their corresponding final
receipts. No additional runtime, provider or deployment work was performed here.

The later `recovery.json` closes the finish review's then-outstanding populated
rehearsal evidence: 1,556 Movie copies/observations and source rows, eight Movie
history events, preserved settings and five media objects including one Movie
photo. A copied backup restored after the owned sources were destroyed; all row,
migration and media fingerprints matched. Restore application servers never
started, owned recovery resources were removed and the backup helper was unchanged.
This is synthetic offline recovery evidence, not a production recovery claim.
Migration 0013 is additive and refuses a lossy downgrade once Movie data, history,
custom preferences or import batches exist. Live rollout still needs a fresh
backup and reviewed schema/API/web deployment under the Movie contract.

Physical-phone camera, keyboard and permissions, live providers, owner-data import,
live migration/deployment and production recovery remain unverified; unrelated
full browser suites were not rerun. Existing PRODUCT.md is historical context,
not current deployment evidence. Preexisting stale design-sidecar metadata, unset
build-path preference and the older copy-edit brief's cobalt wording remain
unrepaired; current DESIGN.md, theme contract and rendered burgundy controls govern.
PRODUCT.md, DESIGN.md, design.json, configuration and all older surface briefs are
preserved by this documentation-only handoff.
