# Manual reconciliation

`POST /api/v1/inventory/{copy_id}/reconcile` accepts:

```json
{"catalog_item_id":"existing-uuid", "release_id":null, "expected_revision":0}
```

Catalog is required and cannot be cleared. The fields describe the complete
identification: omitted or null release means catalog-only, including removal of
an earlier release. Unknown fields, malformed UUIDs and noninteger/negative
revisions return 422 (accepted range: 0–2147483646). GET/list inventory responses expose `identification_revision`.
Existing copies start at zero, without invented historical events.

The service locks the copy row and checks the expected revision before applying
changes. Stale requests return 409, even when their target matches current state;
reload and review before retrying. Missing or soft-deleted copies and missing
catalog/release identities return 404. A release belonging to another catalog
returns 422; the existing composite database FK remains the final guard.

A change to catalog, release or identification status sets status to `identified`,
increments revision once, and commits one manual event in the same transaction.
It never sets `verified`. A request at the current revision with the same catalog,
release and `identified` status returns 200 with unchanged revision, timestamps
and history. A status-only change (including from `verified`) is an event.
UUID, provisional title/description, creation time, ownership/disposition,
location and photos are preserved. Concurrent requests with one expected revision
permit at most one actual change; identical requests can subsequently be stale.

`GET /api/v1/inventory/{copy_id}/reconciliations?limit=50&offset=0` returns events
in ascending resulting revision order. Limit is 1–100; offset is nonnegative.
Each event has copy/event UUIDs, before/after catalog, release, status and revision,
`operation: manual`, and database transaction time `created_at`. Revision gives
ordering even if timestamps coincide. No history mutation endpoints exist.
This is identification history only, without authentication, actor attribution or
protection from a privileged database editor. References restrict deletion of
identities needed by historical events.

## Migration and recovery

Apply additive `0002_reconciliation` before serving the changed API. It adds a
nonnegative, nonnull revision defaulting to zero and the event table with FKs,
status/manual/revision checks and a unique per-copy resulting revision. Migration
0001 is unchanged. Normal PostgreSQL DDL locking applies; schedule deployment
accordingly. ORM identification updates advance `updated_at`; direct SQL retains
the existing timestamp behavior and must explicitly set timestamps as needed.
Direct SQL is not a reconciliation API and does not automatically generate events.

Downgrading drops every reconciliation event and revision counter, while retaining
current identification and photos. Before any nondisposable downgrade: stop all
writers, capture and verify a quiescent full PostgreSQL dump and matching media
snapshot, and preserve the application revision and keys/configuration needed to
restore. To recover lost history, stop writers and restore that pre-downgrade dump
and media together to a separate clean database/media target using the matching
application revision; verify identities, events and downloads before switching.
Re-upgrading alone initializes revisions to zero and cannot recover history.
The harness exercises destructive downgrade only on disposable synthetic data.

The synthetic recovery rehearsal now retains two reconciliations and all referenced
identities alongside the original exact photo bytes after source destruction.
Its quiescent-writer and same-schema-version assumptions remain; this is not
production backup support. Storage assignment, search, catalog CRUD/UI,
authentication, automated matching and broader audit history remain out of scope.
