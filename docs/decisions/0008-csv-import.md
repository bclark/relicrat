# 0008 — Explicit CSV imports retain physical-copy provenance

Status: Implemented for review, not deployed by this change.

CLZ Comics and Discogs collection exports are reviewed ownership intake, not
external catalog matching. Use versioned preset mappings, standard-library CSV
parsing and existing provisional-copy validation. Preview is read-only and a
reviewed file digest binds confirmation to the original bytes. A transaction
creates all copies and provenance together. Failed validation creates nothing.

Keep each source row and CLZ quantity expansion as distinct physical objects.
Repeated external IDs do not establish object identity. Serialize an exact-file
retry through a database unique source/digest constraint, including concurrent
requests or a lost HTTP response. Do not silently reconcile changed exports.

Retain all original cells as private JSONB evidence with row/copy indices and
restrictive batch/copy references. Do not evaluate formulas or render cell HTML.
Prices, grades, dates, boxes/folders and external IDs remain original evidence;
first-class valuation, grading, storage mapping and catalog matching need later
explicit review. The first UI exposes source evidence through paginated history.

Bound upload bytes, CSV records, columns, quantities, expanded evidence and
normalized fields. Stop the whole import on any invalid row. Keep imports off
public logs and use generated synthetic fixtures for tests, including a
1,450-Comics plus 465-Albums volume scenario. No private export is a test fixture.

Migration 0009 adds only import_batches/import_copies and their constraints;
existing copies and history are unchanged. Full database backups retain source
rows. Downgrade refuses any batch rather than discarding provenance. A reviewed
release must rehearse the migration against a verified backup before live use.
No hard-delete undo or automatic cross-export deduplication is included.

Possible duplicate review uses retained CLZ comic IDs, Discogs release IDs and
Blu-ray.com product IDs to find owned copies that share a catalog reference
across distinct imports from the same source. One result groups all eligible
copies for that ID, including physical copies created from a quantity. The
comparison is read-only and uses current edition and physical storage alongside
source row provenance. The catalog reference alone cannot establish physical
identity. Matches require a shared ID in retained data, so manually entered
copies and imports without those IDs are outside this review.

Duplicate decisions apply to one pair from separate imports with a shared
source ID. **Keep both** dismisses that pair and leaves the copies active.
Other pairings remain in review until addressed. **Archive duplicate** asks
the owner which copy to keep, then sets the other copy's soft-delete timestamp
while retaining its UUID, media, storage and original source evidence. Decision
history is accessible from either import and Undo reverses the exact decision.
The API locks both copies in UUID order, verifies the reviewed timestamps, and
records a request ID so a retry cannot repeat the change.

Migration 0017 adds the decision history table and leaves existing inventory
untouched. Downgrade is allowed while the table is empty. Once it records a
decision, downgrade requires a verified pre-migration backup to preserve the
audit trail and avoid stranding archived copies.

The guided CSV preview also flags incoming rows whose retained source catalog ID
matches active owned copies from the same import source. It shows a count and up
to three examples with their current edition and storage. The owner chooses
whether to skip each flagged row or add its copies. A skip applies to the whole
row, including a CLZ quantity. A completed partial import reserves the exact
file digest and retains original row numbers for the copies it created.

The guided commit binds the original bytes and the displayed match evidence to
the review. Source-scoped transaction locks serialize imports before the
evidence is checked again. Existing digest-only API clients remain compatible.
No database migration is required.
