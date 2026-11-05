# Collection browse, inspect and edit

Implemented for review; not deployed. The owner approved the
[November 4 concepts](design/proposals/collection-journey-2026-11-04/README.md).

Desktop has a collection navigation rail, a bounded list/cover browser and a
read-first inspector. Phone opens on a list of collection names, including
All items and custom collections. Selecting a collection opens its saved copies
directly. Search is above the list. Storage, grouping, and List/Covers are under
Filters. The header's + Add opens intake for the selected collection; from the
collection home it opens the existing destination picker. Collection tools and
imports are available through Menu. A focused phone record screen returns to the
same page, filters and scroll position. Albums, Comics, Movies, Other and named custom collections retain
their current identities and config-driven fields. Custom choices remain paged;
an off-page selection remains visible. No fictional image or count from the
concept is installed as inventory.

Search stays within the selected collection and configured artist/series/title
grouping. Storage filtering means the exact physical location, not descendants
or imported labels. Group counts remain whole filtered groups; copy-page counts
are explicitly page-local. Switching List/Covers, opening a copy and Back do not
reset the current search, loaded group, page or browse position. Back restores
selected-row focus when it remains in the result, otherwise the browse heading.
A renamed copy can cease to match the search while its inspector remains open.

Copy details open as a summary, including configured custom observations; unknown,
No and None selected remain distinct. Edit details reveals the existing configured
editor; a confirmed Save details returns to the summary. Cancel requires an
explicit discard decision for a dirty editor. Back hides but keeps the selected
record/editor mounted and stops its camera. Choosing a different item or creating a new copy checks
for a dirty draft before replacing it; uncertain writes/conflicts require reload
and review. Photo, location, checklist and catalog operations remain independent.
Location/catalog changes are locked while copy-detail edits are dirty so they
cannot reset that form underneath the collector. A page reload can discard local
drafts; the browser receives an unload warning for unsaved selected-copy changes.
This is session-local preservation, not offline synchronization or saved routes.

Adding a find is an explicit disclosure, not a permanently expanded intake rail.
Closing intake preserves it and stops its scanner. Generic finds stay outside a
custom collection; the existing Add figure action opens that collection's own
intake. Collection authoring, saved definitions and CSV imports remain available
under Collection tools and imports; this PR does not redesign those workflows.

Result thumbnails and named locations use the bounded API display projection,
with no per-row metadata requests. Images retain owner authentication, lazy
loading and the existing media limits. Missing art has an explicit fallback.
The inspector distinguishes catalog artwork from physical-copy photos. No image
transformation pipeline, client-specific domain rule, dependency or migration is
introduced. Existing observations not currently editable by the API, including
copy notes, remain read-only in the summary; the concept's proposed notes editor
is not an implemented capability of this increment.

The core/API/web repository boundary is recorded in
[the architecture overview](architecture/overview.md#core-repository-and-client-boundary-approved-november-4-2026).
Native authentication, offline sync and immersive clients remain future work.
