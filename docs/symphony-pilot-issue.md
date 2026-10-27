# Symphony pilot: preserve committed photos when refresh fails

Published as [issue #6](https://github.com/bclark/relicrat/issues/6).
Awaiting harness review and explicit dispatch; no dispatch labels are applied.

## Why

Photo uploads commit a MediaAsset and then refresh it inside the same exception
handler. If refresh fails after a successful commit, cleanup deletes the stored
file even though the database row remains. This violates the storage and
data-preservation rules in AGENTS.md.

## Acceptance criteria

- Reproduce the failure with real PostgreSQL commits and a fresh database session.
- Preserve the committed MediaAsset and exact uploaded bytes after a refresh failure.
- Continue removing the file and rolling back metadata when commit fails.
- Remove the strict expected-failure marker after fixing the regression; retain
  fault injection and independent-session assertions.
- Keep schema changes and other review findings out of this task.
- Open a draft PR for human review. Do not merge or deploy.

## Validation

On the dedicated Docker worker:

```sh
sh scripts/test-api.sh tests/test_media_api.py::test_refresh_failure_preserves_committed_photo --runxfail
sh scripts/test-api.sh
```

The harness must run PostgreSQL 17 and migration upgrade/downgrade/upgrade,
preserve failure output, and remove only its own disposable resources. Include
the source revision, exact commands, before/after results, and remaining
limitations in the PR.

## Evidence

On 2026-10-27, the existing baseline passed 23 tests and migration
upgrade/downgrade/upgrade. The new fault-injection regression failed at
`Post-commit read failure must not delete the committed photo`; an independent
session still found the committed MediaAsset. Harness changes and the regression
test must be available on the worker before this issue is dispatched.
