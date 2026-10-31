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
