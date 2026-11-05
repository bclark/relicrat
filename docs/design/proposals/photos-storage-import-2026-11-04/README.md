# Photos, storage and CSV import — interactive proposal

November 4, 2026. The owner requested all three follow-ups: deploy merged PR82,
simplify photos/storage, and redesign CSV importing. PR82's rollout is separate
from these two proposed journeys. This concept follows the owner's established
visual-first review preference; it does not install either interface in the app.

[Open the interactive concept](index.html). Serve this directory on loopback
to use file preview and the exact-file digest demonstration. The concept contains
two journeys, selected in the left navigation or phone chooser:

1. **Photos & storage:** select a photo, inspect its local preview, explicitly
   upload it; choose a physical location and immediately see confirmation.
2. **Import a collection:** choose an export preset and file, review rows/copies,
   mappings and duplicate limits, explicitly import, then inspect the result and
   retained source data. CLZ storage mapping remains a separate reviewed action.

The ivory, forest and burgundy system, native controls and bounded task panel
extend the current interface. Two columns on desktop become one reading order
on phones. The separate concept controls exercise rejection and lost responses.
All records and counts are fictional page memory. Nothing reaches an API, creates
ownership, moves actual inventory, changes a theme preference or persists after
refresh. Photos selected here stay local to this browser session. The included
PNG fixture is a labeled canvas test card, not a photograph of a real collectible.
CSV inputs recognize only the supplied fictional samples; they are not production
parser examples or a substitute for server validation.

## Try these paths

- Use **Try a fictional photo**, then **Upload photo**. Choosing alone adds nothing.
- Choose **Shelf 1 / Box B**. The confirmation appears without another Save step.
- Create **Box C** under **Shelf 1**. Creation alone does not move the copy.
- Set the next simulated save to **Saved, response lost**. Inspect the separate
  saved result before deliberately reloading; do not automatically repeat a write.
- Import the fictional CLZ export. Two rows become four distinct physical copies.
  Previewing creates nothing, and import requires acknowledgement.
- Preview the same sample again. It reopens its recorded import instead of
  creating more copies. A changed export would be a new import that can duplicate
  earlier inventory; there is no cross-export reconciliation in this design.
- Try Discogs and Blu-ray.com samples. Release IDs do not merge copies, and a
  movie box set stays one owned item regardless of its disc count.
- After a CLZ import, review its storage label. Preview and acknowledge the
  eligible copy; a copy already placed elsewhere remains preserved. Changing the
  destination invalidates the earlier review.

## Implementation boundaries

Build these as two focused application PRs after visual review, starting from
merged PR82. Reuse the existing authenticated API; no provider, plugin framework,
schema or dependency is proposed. Core ownership, storage and history validation
remain authoritative for every client.

The prototype's journey chooser is a demo control, not another collection picker
to ship. Photos/storage belong to the opened physical item; importing remains a
collection utility with a bounded task. Preserve browse context and mounted local
drafts across Back. Replacing a draft or an unconfirmed result requires deliberate
inspection/reload rather than silently resetting its file or selected destination.

**Photos/storage:** retain `copy-detail.tsx`'s independent upload and revision-
checked location operations, UUID, photos, movement history, location pagination
and explicit location creation. Catalog covers remain distinct from copy photos.
Local previews need object-URL cleanup and must not imply an accepted MIME type
or server validation. An uncertain upload is not idempotent: a filename match is
not proof it succeeded. Inspection must actually list the saved copy photographs,
not just catalog covers. Display last-confirmed state until a read establishes
the saved result. Explicit reload can replace a local file/location draft only
after warning and a successful read. Keep Back context, pending locks, stale
revisions, parent/cycle checks and unknown outcomes; never silently change copies.

**CSV:** keep the real preset mappings, bounds, all-row validation, warnings,
source/digest uniqueness, atomic copy/provenance creation and paginated batch/
source evidence. The collection comes from the supported export preset. Use
server preview counts, never client guesses. Unknown commit outcomes retain the
exact bytes for another read-only preview, not an automatic write retry. A
confirmed import followed by failed history loading remains a confirmed import.
CLZ storage mapping uses the actual eligible/preserved counts and reviewed token;
inspect a fresh plan after conflict or uncertainty. Preserve already assigned,
previously unassigned and inactive copies. Discogs folders remain source metadata.
No editable mapping engine, cross-export deduplication, automatic catalog matching,
valuation conversion, import deletion/undo or background import queue is proposed.

## Evidence

[Interaction results](verification.json) and PROPOSED desktop/phone captures cover
the concept only. They do not certify the application, an API, a real import,
phone hardware or deployment. Detailed checks and limitations belong in the
shared harness record. The incumbent DESIGN.md, PRODUCT.md and theme contract
remain unchanged; no proposed asset is promoted to a production default.
