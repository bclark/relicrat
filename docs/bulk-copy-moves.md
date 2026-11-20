# Move several physical copies

From a collection, search result, import batch or location's copy list, choose
**Select copies to move**. This opens individual-copy selection on the current
page. Choose a destination, review each copy and its previous location, tick the
review confirmation and save. This is an explicit physical move, not a catalog
change or an import mapping.

Selection is limited to the visible page (currently 20 copies). Search, filter,
page and data refresh changes clear it. Grouped browsing switches to individual
copies for selection. Opening a copy cancels selection. Leaving an existing edit
uses its existing unsaved-change guard; returning to an inspected copy after a
move loads its current location and history.

## Atomic writes and retained history

`POST /api/v1/storage-locations/{destination_id}/move-copies` accepts
`{"copies":[{"id":"copy UUID","expected_storage_revision":0}]}`.
One to 100 distinct IDs are allowed at the API boundary; the UI selects one
visible page. Extra fields, duplicate IDs and invalid revisions are rejected.

The service locks selected copy rows in UUID order and validates every revision
and active ownership before staging any movement. A missing, archived, sold or
stale copy rejects the entire request with 409 and no partial move. A missing
destination returns 404. Existing single-copy edits serialize on the same locks.
Each changed copy uses the existing location-assignment service and gets its own
before/after movement event. UUID, catalog/release links, photos, details and
earlier history remain intact. Copies already at the destination add no event.

There is no automatic retry. A stale selection requires reload and a new review.
A lost response may mean the transaction committed: inspect current locations
before another save. The UI blocks further confirmation until reload (or cancel
with a refresh). Concurrent duplicate requests cannot create duplicate movement
events because they carry the old revisions.

The web gateway accepts only POST on the fixed route. Owner authentication and
origin checks apply; read-only agent credentials cannot move copies. No migration,
new runtime dependency, pack ownership change or live deployment is included.

## Verification

`apps/api/tests/test_bulk_moves.py` runs on disposable PostgreSQL and covers
retained catalog/media/history, unchanged destinations, invalid selections,
stale/inactive/missing copies, and overlapping batches. The existing agent test
also denies the new write route.

`apps/web/tests/bulk-move.browser.mjs` uses synthetic data at desktop 1440px and
mobile 320px. It checks review before save, reopening the inspector, persistence
after reload, per-copy history, rejection after one external move, a fresh review
with one unchanged copy, and a committed request whose response is lost.
Synthetic review/conflict screenshots are retained as short-lived CI artifacts.
