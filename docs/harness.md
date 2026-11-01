# RelicRat development harness

The harness makes repository rules executable: a known source snapshot, an
isolated PostgreSQL instance, repeatable checks, and evidence of the result.
Symphony schedules work; this harness verifies the resulting application changes.

## Run API checks

On a machine with Docker Engine and Compose v2 or later:

```sh
sh scripts/test-api.sh
```

From this Mac, using the configured SSH alias (Python 3.11+, Git, and SSH):

```sh
python3 scripts/test-api-remote.py relicrat-worker
```

The remote runner transfers current tracked and unignored API source files,
including uncommitted changes, plus the test runner and its Compose file. It
does not copy the Git repository, ignored local configuration, or collection
data. Symlink files are rejected. The snapshot SHA256 identifies the transferred
archive; each run's stdout/stderr and exit status are saved under ignored
`.harness-results/<UTC timestamp>/run.log` locally. No SSH credentials are copied.

The Docker runner builds the existing Python 3.12 API image, starts PostgreSQL
17, applies migrations, runs pytest, then downgrades to base and upgrades again
if tests pass. PostgreSQL data lives in tmpfs. Tests use temporary photo
directories. The stack publishes no host ports and uses an internal Docker
network. Its unique Compose project is removed on success or failure, including
its generated test image. Shared base images and Docker build cache remain.

Use pytest arguments after the host to narrow a reproduction:

```sh
python3 scripts/test-api-remote.py relicrat-worker tests/test_media_api.py::test_refresh_failure_preserves_committed_photo --runxfail
```

The photo refresh regression injects a post-commit read failure and uses a fresh
database session to verify that the committed metadata and exact uploaded bytes
survive. The companion failed-commit test checks that rollback still removes
the file. The pilot removed the strict expected-failure marker after verifying
the fix with `--runxfail`; the regression now runs as a normal passing test.

## Limits

- Only synthetic disposable data belongs here. Migration downgrade destroys it.
- SSH access to the current NAS account includes Docker privileges. This is a
  trusted operator test runner, not a safe sandbox for arbitrary agents.
- Ordinary exits and signals trigger cleanup. A host crash, SIGKILL, or lost
  connection may leave resources behind. Inspect the logged project name and
  remove only that project's resources; never run global Docker prune commands.
- Dependency ranges and base tags are not locked yet. Logs record resolved
  packages, Python version, and build image digest; this is repeatable setup,
  not a guarantee of identical future dependency resolution.
- The API suite validates neither web behavior nor recovery nor all concurrency
  invariants. The original review's other findings remain open.

## Synthetic inventory and photo recovery rehearsal

On the dedicated `relicrat-worker` guest, with the operator-provided disposable
`BUILDX_CONFIG` environment already set:

```sh
mkdir -p .harness-results/recovery
sh scripts/test-backup-restore.sh > .harness-results/recovery/positive.log 2>&1
# Each deliberate damage run MUST exit nonzero; inspect the error and cleanup.
sh scripts/test-backup-restore.sh --missing-media > .harness-results/recovery/missing.log 2>&1
sh scripts/test-backup-restore.sh --corrupt-media > .harness-results/recovery/corrupt.log 2>&1
```

Save each command's exit status immediately. A negative run only demonstrates
media detection if the log reaches damage injection and strict verification
fails for the expected missing download or differing bytes; an earlier build,
restore, or cleanup error is not that evidence. Logs include source revision,
local changes, unique project name, synthetic manifest, and cleanup result.
These logs are ignored local evidence, not retained backup archives. Run the
ordinary `sh scripts/test-api.sh` after the rehearsal as a regression check.
The remote API runner does not transfer or run this recovery harness.

The fixed Compose stack uses the existing API image and PostgreSQL 17 native
`pg_dump` custom format / `pg_restore`, plus Python standard-library tar archives.
No new dependency or production behavior is introduced. A provisional copy, two retained manual reconciliations, referenced synthetic
catalog/release identities, and a generated valid PNG are committed through FastAPI's TestClient with the real
session dependency. The manifest records API responses, UUIDs, ownership,
storage key, all copy/photo/history/catalog row columns, timestamps, schema definitions,
constraints, indexes, triggers, functions, and Alembic revision. The schema
comparison recognizes PostgreSQL 17's two equivalent deparsing forms for the
existing status array casts; changed values/operators remain unequal, with
positive and negative controls run by the driver. Original PNG
bytes are retained separately for exact comparison, not regenerated at restore.

**Consistency assumption:** the seeding API process exits before either backup
starts, and no application server or other writer is running. Both database and
filesystem remain quiescent throughout capture. A database dump alone cannot
make a concurrent filesystem snapshot consistent. Do not adapt this command to
online writes without designing and testing a coordinated consistency boundary.

Before restoring, the source database container (including its tmpfs database)
and source media volume are removed. Restore uses a fresh database and separate
media volume. A fresh API process/session checks the unchanged manifest, current
migration head, row/schema equality, photo ownership and metadata, and exact
API-download bytes and SHA256. Both damage modes run the identical verifier;
missing media must yield a failed download, and corruption must fail byte equality.

Trust boundaries: this accepts no database URL, input archive, Compose project,
media path or restore target. It pins the local guest Docker socket and checks
its engine name; that name is an operational guard, not authentication. Docker
access grants guest control, so only the already isolated dedicated worker is
appropriate. All credentials and records are synthetic. The project has an
unpredictable per-run name, internal networking, no published ports, and only
project-owned disposable volumes. The driver alone is mounted read-only from
the workspace. Only the archive generated by this run is extracted, under the
restored media root with Python's data filter; this is not an importer for
untrusted external backups. No NAS services, real data, or production volumes
are used.

**Destructive disposable cleanup:** ordinary success, failure, HUP, INT and TERM
remove this run's source and restore containers, volumes, generated images,
network, database dump, media archive and fixture manifest. Keep command output
outside these volumes. Cleanup checks for remaining project resources and fails
if any remain; it never globally prunes. SIGKILL, host crash, or Docker failure
can leave resources behind: use the logged project name to inspect and clean
only that run. Disposable deletion is intentional and has no recovery promise.

This is a bounded development rehearsal, not a production backup feature. It
provides no crash-consistent online snapshots, retention, encryption, scheduling,
external backup destination, disaster recovery guarantee, or evidence for a
large collection. Authentication, concurrent writers, hostile archive ingestion,
and recovery across application/schema versions are outside its scope. It does
not complete the first product vertical slice. The reconciliation capability adds migration 0002; see
[the migration and recovery contract](../apps/api/INVENTORY.md). There is no
production backup deployment support.

## Symphony pilot

The root WORKFLOW.md is prepared for Symphony v0.0.3's GitHub Issues adapter.
It requires both `relicrat-pilot` and `agent-ready` labels, limits concurrency to
one agent, and hands off a draft PR without merging or closing the issue.
Removing `agent-ready` makes the issue ineligible for another run.

The prompt's restrictions are workflow policy, not an operating-system security
boundary. Use a dedicated worker VM or equivalent isolated host with its own
Docker engine and synthetic data. Do not mount Technodrome's host Docker socket
or general-purpose SSH credentials into an unattended worker. Bound its CPU,
memory, and runtime operationally; `max_turns` is not a total cost/time limit.

Before launch:

1. Publish/review these harness changes so fresh workspaces can clone them.
2. Provision the dedicated worker with Git, Codex, Python 3.11+, and its own
   Docker/Compose. Install the pinned Symphony v0.0.3 executable for the worker
   platform and verify its published checksum. It embeds Elixir/Erlang.
3. Authenticate Codex interactively on that worker and provide repository-scoped
   Git access. Do not copy the Mac's existing authentication files to the NAS.
4. Configure GITHUB_TOKEN outside the repository with only the repository access
   needed for issues, branches, and draft PRs. Tracker credentials are supplied
   host-side; do not put literal credentials in WORKFLOW.md or logs.
5. Set SYMPHONY_WORKSPACE_ROOT to an absolute directory owned by the worker.
   Run the full harness, `sh scripts/check-worker-sandbox.sh`, and
   `python3 scripts/check-worker-protocol.py` there before
   starting Symphony. Confirm worker sandbox compatibility with its isolated
   Docker engine; don't bypass a rejection. The worker guide describes Ubuntu's
   scoped AppArmor profile required for the sandbox launcher.
6. Use [pilot issue #6](https://github.com/bclark/relicrat/issues/6), also recorded
   in docs/symphony-pilot-issue.md. Create the two dispatch labels if absent and
   apply them only to that one issue when ready.
7. Start Symphony in the foreground with the absolute path to WORKFLOW.md and
   logs outside disposable issue workspaces. Leave its optional HTTP dashboard
   disabled initially. Observe the first run; pause it if handoff or access fails.

See [the dedicated worker guide](worker.md) for provisioning and interactive
login. Codex login and GitHub repository read access are verified. Worker write
permissions and agent sandbox execution remain to be validated. The workflow is not running.
Do not label any issue ready until setup and verification have finished.

## Verification recorded on 2026-10-27

- `python3 scripts/test-api-remote.py technodrome` before adding fault injection:
  23 passed, followed by successful migration downgrade/upgrade.
- The targeted `--runxfail` reproduction on Technodrome: one failure at the missing committed
  photo file, while a fresh database session still found the committed row.
- `python3 scripts/test-api-remote.py technodrome` with fault injection:
  24 passed, one expected failure, zero skipped; migration round trip succeeded.
- `sh -n scripts/test-api.sh`, Python compilation of the remote runner and
  media tests, and `git diff --check`: successful.
- Symphony v0.0.3 Linux x86_64 executable: published SHA256 verified on the NAS;
  `--help` printed usage and exited 1. No authenticated worker run was attempted.

The test suite emits one existing Starlette/httpx deprecation warning. No
application migrations were changed. The photo bug intentionally remains open
for the pilot; the other review findings are also outside this change.

Upstream references:

- [Symphony v0.0.3 implementation and configuration](https://github.com/openai/symphony/blob/v0.0.3/elixir/README.md)
- [Symphony v0.0.3 release and checksums](https://github.com/openai/symphony/releases/tag/v0.0.3)
- [Harness engineering](https://openai.com/index/harness-engineering/)


## GH-13 reconciliation verification (2026-10-28)

Source baseline: `74de7fa4f2789a0539aa681557312695c1f627a6`, with issue workspace
changes published in the GH-13 draft PR. Local full logs are under ignored
`.harness-results/gh-13/`. The dedicated guest engine is `relicrat-worker` and
uses the operator-supplied disposable `BUILDX_CONFIG`.

- Baseline `sh scripts/test-api.sh`: 25 passed; zero skipped/expected failures;
  downgrade to base and upgrade succeeded; project resources removed.
- Final `sh scripts/test-api.sh`: 43 passed, zero skipped/expected failures;
  exit 0, including existing-record migration round trip, deterministic competing
  row-lock requests, and the full downgrade-to-base/upgrade-to-head sequence.
  Six warnings: one existing Starlette/httpx warning and five Alembic configuration
  deprecations exposed by the migration test. Project resources removed.
- `sh scripts/test-backup-restore.sh`: exit 0 after source destruction; both
  events, referenced identities, row/schema equality and exact photo bytes verified.
- `sh scripts/test-backup-restore.sh --missing-media`: expected exit 1 after
  injection, specifically `Photo download failed: HTTP 404`.
- `sh scripts/test-backup-restore.sh --corrupt-media`: expected exit 1 after
  injection, specifically `Downloaded photo bytes differ`.
- All recovery runs reported project cleanup checked, without remaining resources.
  The damage runs are deliberate harness failures, not pytest expected failures.
- `git diff --check` and Python source compilation: exit 0.
- The first extended recovery run correctly reported a schema comparison
  difference caused by PostgreSQL 17's equivalent array cast deparsing for the
  new history status check. An exact normalization rule with changed-value and
  changed-operator negative controls covers that predicate; no schema or media
  equality assertions were removed.

The new tests use real commits and independent sessions for history persistence,
event-write rollback and competing reconciliation requests. The migration test
round-trips 0002 on synthetic pre-existing records in the disposable test database;
the full harness also downgrades through base and upgrades through 0002.

## GH-16 storage verification (2026-10-28)

Source baseline: `448a16e1896a007b6335155b8d9b30c73d455f97` plus this
issue's workspace changes. Migration head is `0003_storage`. Logs are preserved
locally under ignored `.harness-results/gh-16/`; branch/commit identifiers for
published contents are recorded in the draft PR. No dashboard files were changed.
The dedicated guest engine and operator-supplied disposable `BUILDX_CONFIG`
were used; no external data or host services were accessed.

- Baseline `sh scripts/test-api.sh`: exit 0, 43 passed, zero skipped/expected
  failures, six existing deprecation warnings. Head→base→head succeeded through
  0002; project `relicrat-test-1793156881-4` removed its database, image and network.
- Final `sh scripts/test-api.sh`: exit 0, **65 passed**, zero skipped/expected
  failures, 17 warnings (one Starlette/httpx and 16 Alembic configuration
  deprecations). Head→base→head succeeded through 0003; project
  `relicrat-test-1793157121-3` removed its database, image and network.
- `sh scripts/test-backup-restore.sh`: exit 0, project
  `relicrat-recovery-np1udximt9`. After source DB/media destruction, verified all
  row columns/schema, nested locations, current assignment, two movements,
  two reconciliations, referenced identities and exact photo bytes.
- `sh scripts/test-backup-restore.sh --missing-media`: intended exit 1 after
  injection, specifically `Photo download failed: HTTP 404`; project
  `relicrat-recovery-scg3qmz9jn` reported cleanup checked.
- `sh scripts/test-backup-restore.sh --corrupt-media`: intended exit 1 after
  injection, specifically `Downloaded photo bytes differ`; project
  `relicrat-recovery-acgx1jgsfi` reported cleanup checked.
- Positive recovery also reported cleanup checked; no remaining project resources
  were reported. Damage-mode failures are deliberate, not skipped database checks.
- `git diff --check` and Python source compilation with built-in `compile` passed.

Focused checks use real commits/fresh sessions for event persistence and rollback,
exact photo metadata/bytes and retained identification history, overlapping row-lock
requests, and independent concurrent identification/storage revisions. Direct SQL
checks cover revision/event FKs and uniqueness, self/long/multi-row cycles, a
160-level hierarchy, valid multi-row rotation and absent coordination state.
Opposing parent changes on different rows establish both snapshots before the
competing commit and wait for observed PostgreSQL lock overlap. READ COMMITTED
rejects the cycle with 23514; REPEATABLE READ rejects the stale guard write with
40001. Committed graph state remains valid. Migration tests preserve legacy
records, reject a preexisting longer cycle atomically, and round-trip 0003 with
populated movement history on disposable data.

The migration takes an exclusive location-table lock while validating/installing;
hierarchy mutations serialize on a singleton guard write and scan the final graph.
Large-collection load has not been tested. Downgrade destroys movement history and
revisions and removes cycle protection while retaining current assignments; see
[the concrete DB/media backup and recovery procedure](../apps/api/INVENTORY.md).
The recovery rehearsal remains quiescent and same-version only. Authentication,
search, usable frontend/catalog UI, operator production backups, container
reparenting/history and broader provenance remain unfinished. The first vertical
slice is incomplete.

### GH-16 independent review: schema lookup boundary

Two direct-SQL regressions reproduced temporary relation shadowing of the new
hierarchy check and coordination table. Both failed before the correction.
Migration 0003 now pins each hierarchy function to pg_catalog/public with pg_temp
last; the two regressions pass without changing or weakening the cycle checks.
Migrations 0001 and 0002 remain unchanged.

Final operator verification used the storage source plus this correction:

- `sh scripts/test-api.sh tests/test_storage.py::test_hierarchy_guard_uses_canonical_relations`:
  2 passed after the fix (2 failed before it); migration head/base/head passed.
- `sh scripts/test-api.sh`: 67 passed, zero skipped/expected failures, 17
  deprecation warnings; migration round trip through 0003 passed.
- `sh scripts/test-backup-restore.sh`: exit 0 after source destruction; hierarchy,
  guard state, assignments, movement/identification history and exact bytes passed.
- Both recovery damage modes retained their intended exit 1: missing download
  HTTP 404 and differing photo bytes, respectively.
- `git diff --check` passed. Logs are retained in the issue workspace under
  ignored `.harness-results/operator-review/`; only disposable data was used.

## Inventory text search verification (2026-10-28)

Initially built on main `448a16e1896a007b6335155b8d9b30c73d455f97`,
before storage/dashboard PRs merged. The operator ran
`python3 scripts/test-api-remote.py relicrat-worker`, which executes
`sh scripts/test-api.sh` on the isolated guest with disposable PostgreSQL 17.

- Baseline: 43 passed, zero skipped/expected failures, exit 0 and migration round trip.
- Before implementation, `python3 scripts/test-api-remote.py relicrat-worker
  tests/test_inventory_api.py::test_search_each_field_and_trim --maxfail=1`:
  expected exit 1; search returned an unrelated copy because `q` was ignored.
- Before integration with storage, full suite: 62 passed, zero skipped/expected failures, exit 0, including
  literal wildcard/backslash/quote handling, NUL/length validation, catalog-only
  exclusion, multiple-copy pagination, and unchanged history/photo bytes.
  Six existing Starlette/httpx and Alembic configuration deprecation warnings.
- That API snapshot SHA256 is
  `a6a7737e1e7969e15f1f51f410e362b18b80ef0bbd24013c66eae5e1fdc8cf22`.
  Head → base → head migrations succeeded; each run removed its own disposable
  project. Full output and exit statuses are retained in ignored local harness logs.
- `git diff --check` passed. No migration, dependency, deployment, or permission
  changes. Recovery and web checks were not run for this read-only API change;
  large-collection performance is unmeasured. Symphony remained stopped.
  These initial results precede the combined verification below.


### Combined verification after storage/dashboard merge

Integrated merged main `5ee13b8deb872895c3396a6a8b7b0f2d101ca91d`, retaining
storage and dashboard changes and resolving status-document conflicts. No deployed
migration was edited. Extended the unchanged-state search check to first assign
a storage location and then verify the same storage revision and movement event.

`python3 scripts/test-api-remote.py relicrat-worker` passed with **86 passed,
zero skipped/expected failures**, exit 0 and 17 existing deprecation warnings.
Snapshot SHA256:
`1d35384fe8e82e24c3e799866a0ba95c0c5e62e16f1aa7d1b62eddafb8415841`.
The combined suite includes storage hierarchy isolation races, shadowing guards,
reconciliation concurrency, search, and media checks. Migration head 0003 → base
→ head passed; its disposable project/container/network/image were removed.
Recovery and web checks were not rerun; no new search migration or dependency.

## Browser/API connection verification (2026-10-28)

Built on merged search main `de8ff402f846c2d07acfa83417c62e5c7571b350`.
The inventory screen remains a placeholder; this adds its same-origin server
connection and Compose media configuration, without changing API domain code.
See [web setup and trust boundaries](../apps/web/README.md).

- Host `npm test` in apps/web: 10 passed, zero failures/skips/todos; Node 26.12.1.
  `npm run lint`: exit 0. Initial host `NEXT_TELEMETRY_DISABLED=1 npm run build`
  passed; the final production build was also verified in the worker container.
- Worker `sh scripts/test-web.sh`, bounded externally by a 15-minute timeout:
  exit 0. Production Next.js 15.5.28 build passed under Node 22; all 10 boundary
  tests and TypeScript checks passed in that image. PostgreSQL 17 migrated to 0003.
- The built Next route exercised JSON intake, multipart photo upload, nested
  storage creation/assignment/history, stale-revision rejection, literal search,
  rejected cross-site writes/oversized JSON, and exact binary photo download.
  Recreating the API container retained the same copy/state/history/photo bytes.
- The first integration attempt failed a legitimate POST with 403: Next.js
  normalized its internal URL to localhost while the caller used 127.0.0.1.
  The corrected check compares Origin with actual Host and scheme, ignoring
  forwarded host headers. A regression covers the normalized URL and spoofed
  forwarded host. No cross-origin rejection assertions were relaxed.
- Final transferred source archive SHA256:
  `aaa42c8b9cc0b5859ec1c0d4a70ead4e1079249c7c8528a5034e6c9bc8f0dcde`.
  An independent comparison matched all 11 runtime/test/config file hashes to
  the tested guest snapshot. Compose config checks confirmed loopback-only
  development ports, server-only internal API origin and a named media mount;
  the integration stack had no published ports and an internal runtime network.
- Both integration projects removed their containers, volumes, networks and
  generated images, including the failed attempt. A separate resource query
  confirmed zero leftovers. Symphony stayed stopped. Full logs and hashes are
  retained in ignored `.harness-results/browser-api/` operator evidence.
- `sh -n scripts/test-web.sh` and `git diff --check`: exit 0. No API pytest suite,
  migration downgrade or recovery rehearsal was rerun for this web/Compose-only
  change. The integrated stack verifies migration upgrade and media persistence,
  not backup/restore, a browser UI, authentication or production readiness.

The committed npm lockfile records existing web dependencies; Docker uses npm ci.
No new application dependency or database migration was added. Development photo
and database volumes must be preserved together; down --volumes destroys them.
Existing unmanaged media is not automatically moved into the new named volume.

## First inventory screen verification (2026-10-28)

Built on merged browser/API main `299aeaffb9cb6b4a6eb78e9e977314b6d4d09810`.
The owner confirmed add-first and building the working screen directly. This
bounded screen covers provisional copies, photos, explicit storage, and search;
it is not catalog identification UI, authentication, or production recovery.

- Host `npm run lint` and `NEXT_TELEMETRY_DISABLED=1 npm run build`: exit 0.
  An initial CSS alignment warning was corrected before worker verification.
- Dedicated worker `sh scripts/test-web.sh`: exit 0; production Next build,
  TypeScript and **10 Node boundary tests** passed, zero skips/failures. Fresh
  PostgreSQL 17 upgraded through 0003. The HTTP smoke retained copy/history and
  exact photo bytes after API-container recreation; its own resources cleaned.
- `npm run test:browser` with isolated Chrome and an operator-provided loopback
  bridge to a fresh no-port worker stack: **7 passed, zero skipped/failures**.
  Six fixture-driven cases cover intake, duplicate submission, separate failed
  photo saves, uncertain writes, outages, unreadable/network responses, read
  races, storage conflicts, bounded paging, escaped text, keyboard focus and
  narrow-screen overflow. The seventh drove actual Chrome → production Next →
  FastAPI → PostgreSQL/media: copy, photo, nested locations, explicit assignment,
  literal search, page reload, exact photo download and retained movement.
- The real-write test refuses a nonempty inventory. The two stacks used unique
  projects, an internal network and no published ports; synthetic data only.
  The temporary Mac bridge used existing ordinary two-hop SSH sessions into
  the test web container; no NAS forwarding or permissions were changed.
- Scoped source archive SHA256:
  `32eb0c78a34e3775f489f982cd29ef6fd1553e91fbd7da9c42a4f780f8e47613`.
  Thirteen runtime/test/config file hashes independently matched the tested
  guest snapshot. The worker audit verified no published ports, exact synthetic
  fixture state and photo checksum, with Symphony stopped.
- The first browser attempt hit a test-selector ambiguity with Next's route
  announcer; the selector now names the actual form error. An early dev-server
  mobile capture was malformed; final production captures settled focus/scroll
  and were visually opened and verified before independent review.
- The layout detector ran once and returned no findings. Independent finish
  review returned **ship**, with no material UI fixes, scoped to this first
  synthetic workflow. Root design records describe the built app; the historical
  progress-dashboard design record is retained separately, with its HTML unchanged.
- `git diff --check`: exit 0. Playwright is test-only and lockfile-pinned; no
  application dependency, API domain implementation or migration changed.
  API pytest, migration downgrade and recovery rehearsal were not rerun. The
  web harness checks fresh schema upgrade/media persistence, not backup recovery.

After verification the operator stopped both disposable stacks, the temporary
bridge and the local preview; project resources and logs are checked separately.
Synthetic-only hands-on use is appropriate after review and a separately started
private preview. Unsaved drafts remain page-local; catalog identification and
production deployment are still unfinished. Local ignored evidence is retained
under `.harness-results/intake-ui/`, including exact commands, failed/final logs,
source hashes, captures and the independent review verdict.


## Offline operator backup verification

See [the backup/restore runbook](backup-restore.md) for retained synthetic bundles,
app downtime/restart, exact image requirements and fresh offline restore.
`python3 -m unittest discover -s scripts -p test_backup.py -v` exercises local
bundle/archive/capture-lock boundaries. `python3 scripts/test-operator-backup.py`
on the dedicated worker invokes the actual commands using only fresh synthetic
projects, destroys its source before restore, reuses the independent row/schema/API
verifier and rejects damaged dump/missing media/corrupt media/unsafe tar/changed row fingerprints. It removes
only its own projects. This is separate from the existing disposable rehearsal and
never targets the hands-on preview.

Verification recorded on 2026-10-28, based on merged main
`2101a56f850f00d8dc87a4904093153aeb21760d`:

- Local and worker `python3 -m unittest discover -s scripts -p test_backup.py -v`:
  **6 passed**, zero failures/skips. Covers archive/bundle damage and competing
  capture locks, including release after an exception.
- Dedicated worker `python3 scripts/test-operator-backup.py`: **exit 0**. Actual
  commands restarted the app after failed/successful capture, refused overwrite
  and stale Compose configuration before downtime, then restored after deleting
  the source DB/media. The independent fixture verifier compared all seeded
  row/schema values, UUIDs, reconciliation/movement history and exact API PNG
  download. An extra unreferenced hard-linked regular file survived as bytes.
- Five deliberate damage cases each exited **1 at the expected boundary**:
  dump checksum mismatch, missing photo, corrupt photo with updated tar checksum,
  unsafe tar member, and changed expected row fingerprint with updated checksum.
  Restore remained offline/incomplete. Checksum failure created no restore target.
- Cleanup and an independent Docker query found no test/restore containers,
  volumes or networks. The original hands-on preview's three containers remained
  running and its Mac loopback page returned HTTP 200; it was not a capture target.
- `python3 scripts/test-api-remote.py relicrat-worker`: **86 passed**, zero
  skips/expected failures, 17 existing warnings; migration downgrade to base and
  upgrade through 0003 succeeded, exit 0, isolated resources removed.
- Python compilation and `git diff --check`: exit 0. Worker hashes independently
  matched all three final runtime/test files. Local evidence is retained under
  ignored `.harness-results/operator-backup/`.
- An early transfer included macOS metadata sidecars and failed migration loading;
  a clean source transfer corrected it. A later test-only random name included an
  underscore invalid in Docker's generated image reference; hexadecimal project
  IDs fixed it. Final runs passed without reducing recovery assertions.

No web build/browser suite or standalone legacy recovery command was rerun for
this operator-tooling change. The independent legacy fixture verifier was reused
inside the new command integration. No app schema/migration or runtime dependency
changed. These results do not establish production recovery or power-loss safety.

## Manual catalog identification verification (2026-10-28)

Based on merged main `0fd90c424c50ebfe23f29cc3d88d394fa0e368df`.
This extends the existing inventory record with catalog lookup/creation and an
explicit revision-checked reconciliation; no schema migration or dependency.

- `python3 scripts/test-api-remote.py relicrat-worker`: **90 passed**, zero
  skips/expected failures, 17 existing warnings; full downgrade to base and
  upgrade through 0003 succeeded, exit 0. New PostgreSQL checks cover names and
  fields, literal catalog search and page limits, missing/foreign releases,
  similar-name identity separation, no implicit ownership, reconciliation and
  release removal preserving UUID, provisional fields, storage/history and PNG.
- Host `npm test`: **11 passed**, zero skips/failures. Fixed catalog paths retain
  same-origin POST checks, bounded bodies, header isolation and method allowlists.
  An initial sandbox run stalled on its loopback server; it was stopped and rerun
  with the required local-listener permission. `npm run lint` and the initial
  production build passed. Final worker production build/typecheck also passed.
- Dedicated worker `sh scripts/test-web.sh`: exit 0, **11 Node tests passed**,
  fresh migration through 0003, existing HTTP copy/photo/nested storage/search
  smoke and exact photo persistence after API-container recreation; cleanup passed.
- Final `npm run test:browser` with isolated Chrome, the operator's temporary
  SSH loopback bridge, `RELICRAT_REAL_UI_TEST=1` and screenshot output: **10 passed**,
  zero skips/failures. The guarded real test refused nonempty inventory and drove
  production Next/FastAPI/PostgreSQL/media: one copy/photo/nested location,
  category/item/release creation without implicit ownership/linking, explicit
  identification then release removal, preserved copy/storage, two retained
  identification events, canonical-name inventory search and exact photo bytes.
- Fixture browser cases additionally exercise catalog/release paging, independent
  selected-release lookup beyond page one, obsolete search cancellation, clearing
  a release on item changes, stale and uncertain saves requiring Reload copy,
  no automatic POST retry, escaped catalog names, and existing intake/storage
  failure, race, keyboard and mobile behavior. Creation drafts remain page-local.
- Desktop1440/mobile390 production screenshots were opened and validated. A
  bounded inspection batch removed redundant single-page controls, themed native
  radios and corrected footer claims; confirmation captures remained valid. The
  detector ran once and returned no findings. No decorative raster/icon assets.
- Ten final runtime/test file hashes independently matched the worker snapshot.
  Test stacks used an internal network and zero published ports, via ordinary SSH
  sessions without NAS forwarding changes. Symphony stayed stopped. Both test
  projects removed their containers, volumes, networks and images; independent
  queries confirmed cleanup. The separate original trial remained running and
  returned HTTP 200, without upgrading its code or changing its records.
- Python compilation and `git diff --check`: exit 0. Full local evidence is under
  ignored `.harness-results/catalog-identification/`.

Catalog editing/merging/deletion, authenticated actors, automated identification,
production recovery and real collection data remain out of scope. Manual create
keys are UUID-based; matching names do not infer uniqueness. Offset pages can shift
under concurrent creation. No backup/restore suite was rerun for this change;
existing row/history preservation is checked through API/browser integration.
The completed synthetic vertical workflow is not a production-readiness claim.

The fresh independent finish review found the inherited presentation consistent
and requested only a PRODUCT.md capability/evidence correction. The documenter
completed that update and preserved DESIGN.md/design.json byte-for-byte. The
reviewer’s verdict pass scored its sole material fix resolved, disposition ship;
that pass is scoped to the documentation fix. Human PR review/merge is separate.

## Single-owner access verification (2026-10-28)

Based on merged main `1455b4eb04c3684e41209c12ce93f73e697c06fa` (PR #25).
The owner chose an SSH-provisioned password. Migration 0004 adds revocable owner
sessions and a serialized failed-login guard; no collection rows are rewritten
and no runtime dependency is added. The existing trial has not been upgraded.

- `python3 scripts/test-api-remote.py relicrat-worker`: **97 passed**, zero skips
  or expected failures, 20 warnings; full downgrade to base and upgrade through
  0004 succeeded. Auth tests cover anonymous data/upload/docs denial, bounded
  login and sanitized validation, token-hash-only storage, logout replay,
  expiry, password/secret rotation, concurrent failed-login throttling, missing
  configuration and auth migration preservation of an existing copy. Existing
  domain tests sign in through the actual login endpoint.
- `sh scripts/test-web.sh` on the dedicated worker: production build/typecheck,
  **19 Node tests**, zero skips/failures, and fresh migrations passed. HTTP smoke
  verifies authenticated copy/photo/storage/search and exact photo persistence
  after API recreation. Both passes completed; scoped cleanup exited 0.
- Host Node tests, TypeScript check and production Next.js build also passed.
  Boundary checks cover HTTPS and loopback cookie policy, Host/Origin pinning,
  cookie-to-Bearer isolation, token-free browser JSON, login limits/errors,
  session lookup and confirmed server-side logout before cookie deletion.
- `npm run test:browser` with `RELICRAT_REAL_UI_TEST=1`, isolated Chrome and a
  loopback SSH bridge to the disposable no-port worker stack: **11 passed**, zero
  skips/failures. The existing real inventory/catalog workflow still preserves
  physical-copy UUID, photo bytes, storage and reconciliation history. The new
  flow verifies guest redirects, wrong/right password, HttpOnly/Strict cookie,
  no JavaScript token access, no-store pages, cross-origin write rejection,
  anonymous photo denial, reload persistence and logout-cookie replay denial.
- `python3 scripts/test-operator-backup.py`: positive capture/restart, source
  destruction, fresh restore and independent fixture verification passed; five
  damaged-bundle modes were rejected. Stale Compose settings still fail before
  stopping writers. The test now includes auth tables and supplies synthetic
  credentials only to its independent verifier; actual restores remain stopped
  without owner configuration. Cleanup of all owned resources passed.
- `python3 -m unittest discover -s scripts -p 'test_*.py' -v`: **11 passed**.
  Python compilation and `git diff --check` passed. Setup
  checks verify private exclusive output, no secret stdout, password verification,
  unsafe-origin refusal and refusal when hidden password entry is unavailable.
  The bridge checks host/origin/path/length guards and selective cookie forwarding.
- Desktop/mobile inventory and login-error captures were inspected. A mobile
  login capture was replaced from a fresh fixed-size context after a resize
  rendering artifact; no UI change was needed. The detector ran once and returned
  no findings. No decorative asset or design-system change was introduced.

An early web smoke failed because it checked gateway readiness before the
recreated API was ready; the final check waits for API health as well. The first
operator run exposed Compose `--hash` omitting env_file resolution; the tool now
hashes the fully resolved model through stdin, preserving stale-config rejection
without a credential-bearing temporary file. Final integrations passed.

Local logs are under ignored `.harness-results/owner-authentication/` in the
operator's main checkout. This evidence covers synthetic development only.
HTTPS ingress, public deployment, MFA, multi-user permissions, large-load budgets,
off-host backup and production recovery remain unverified/out of scope. Restore
promotion requires a fresh session secret, as documented in owner-access.md.

All 41 changed runtime/test source hashes matched the worker snapshot. Root
development Compose rendered successfully with public synthetic credentials; it
was not launched. The separate disposable browser stack and Mac bridge were
removed after verification. The existing trial on port 56742 still returned 200.

The fresh finish reviewer matched all four captures to the inherited Operate
system and requested only PRODUCT.md truth/persistence corrections. The shipped
documenter updated those claims and preserved DESIGN.md/design.json byte-for-byte.
The reviewer's verdict pass scored that sole documentation fix resolved,
`disposition: ship`; that verdict pass covers the listed fix. Human PR review,
merge, private password setup and trial upgrade remain separate next steps.

## PostCSS dependency security verification (2026-10-28)

Based on merged owner-access main `e86827727d64361b00446b8de105eb3bc51feca6`.
Next 15.5.28 pins PostCSS 8.4.31. A scoped npm override now resolves its copy to
8.5.32 without a framework upgrade, new direct dependency or schema change.
The lockfile retains the other package versions. Source-map parsing remains a
filesystem trust boundary even though this app does not accept uploaded CSS.

- The focused source-map regression was run in the old web image with no network
  and **failed as expected**, demonstrating access to a disposable external map.
  It resolves PostCSS through Next and checks absent `from`, parent traversal,
  symlink escape and retained ordinary local source-map support.
- Patched host `npm test`: **20 passed**, zero skips/failures. `npm run lint` and
  `NEXT_TELEMETRY_DISABLED=1 npm run build` passed. `npm ls postcss` confirms Next's
  actual dependency is 8.5.32. Both `npm audit` and `npm audit --omit=dev` report
  **zero vulnerabilities** against the registry's current advisory data.
- Worker `sh scripts/test-web.sh`: production build/typecheck, **20 Node tests**,
  fresh database migration and authenticated HTTP inventory/photo/storage/search
  smoke passed. Recreating the API preserved exact photo bytes and history.
- Isolated Chrome `RELICRAT_REAL_UI_TEST=1 npm run test:browser`: **11 passed**,
  zero skips/failures, against a separate production web/API/PostgreSQL/media stack.
  This includes existing catalog/intake behavior and real guest/login/reload/
  logout/captured-cookie rejection. No screenshots or design changes were needed.

The initial regression assertion was corrected to accept a fully absent map as a
valid rejection; final assertions still fail on 8.4.31 and pass on 8.5.32.
Logs are retained under the operator's ignored `.harness-results/postcss-security/`.
No full API or backup suite was rerun: this patch changes only a web dependency
and its focused regression. Audit results are dated evidence, not a promise
against undiscovered vulnerabilities. The running trial remains on merged code
until this security patch is human-reviewed and merged.

## First encrypted off-host recovery copy (2026-10-28)

The operator completed the manual procedure in [off-host recovery](off-host-backup.md)
against the merged authenticated synthetic trial at
`e86827727d64361b00446b8de105eb3bc51feca6`. Existing offline capture commands
briefly stopped/restarted only its web/API writers. Exact API/db/web images and
reviewed Git source were included without owner environment credentials.

The complete capsule was streamed over the existing SSH helper into native
OpenSSL CMS authenticated encryption on the Mac. The roughly 455 MiB archive is
outside Git in a private directory; the separate private decryption key never
went to the NAS. An encryption/decryption roundtrip and changed-ciphertext rejection
were checked with disposable bytes. The actual copied archive then authenticated,
and every member hash and all three saved image identities verified. Initial image
verification stopped on an OCI-vs-configuration-hash mismatch; using actual OCI
manifest/index digests resolved the check without changing the exported data.

The backup recovered from that Mac archive was uploaded into a separate private
location and restored to fresh offline volumes. The existing restore verifier
matched all rows, migration state and exact media checksums. The resulting
project was retained stopped, with no API/web started. Temporary decrypted Mac
data was removed. The live trial's login still returned HTTP200. Private logs
and receipts remain under ignored `.harness-results/off-host-backup/`; durable
recovery instructions and a non-secret receipt accompany the encrypted archive.

This is a verified manual off-host copy on a separate computer, not off-site
storage, automated scheduling/retention or a full replacement-host rehearsal.
Saved image identities were validated, but loading into an empty image store was
not tested. Separate protected key custody remains unconfirmed. No application,
schema, dependency, production deployment or public-network change was made for
this operational/docs milestone; no application suites were rerun for these docs.

## Daily backup task and key-custody preparation (2026-10-28)

The operator enabled a daily task in this existing local chat at 03:00 in the
operator's America/New_York timezone. It uses the current deployed-release record
and [the bounded daily contract](scheduled-backups.md), not a working branch or
previous rollout snapshot. The native task returned ACTIVE and its saved daily
hour was checked; it has not yet reached its first scheduled invocation.

Before activation, the complete operation was run manually once against the
current authenticated synthetic trial: genuinely fresh offline capture and app
restart; exact image/source export; authenticated encrypted Mac transfer; copied
artifact decryption and all member/OCI identity hashes; fresh offline restore
matching all rows, migration state and media checksums. The newly owned successful
verification project was stopped and removed, with container/volume/network
cleanup independently checked. Only that run's temporary staging/plaintext was
removed after verification; previous encrypted archives and retained manual
restores were preserved. The live login still returned HTTP200. Both machines
passed the minimum5GiB capacity preflight. Private evidence is under the original
operator checkout's ignored `.harness-results/scheduled-backups/`.

The existing Mac recovery key/certificate were packaged into a private mode0600
local import ZIP; ZIP integrity and expected entries passed. The owner selected
1Password secure-file storage for the second copy and unlocked the native app
directly. A Document named RelicRat backup recovery key was saved in the Personal
vault; upload completion was observed. The downloaded vault ZIP matched the
original byte-for-byte, and its extracted key successfully decrypted a disposable
OpenSSL CMS envelope. The temporary import kit/download/extracted copies were
removed after verification; working Mac key/certificate and the vault Document
were preserved. Independent key custody is verified. No key value was displayed
in chat, Git or NAS logs.

No app/schema/dependency change was made and no app test suites were rerun for
these operational/docs changes. The Mac and desktop app must be available for
local scheduled work; permissions or unavailable infrastructure can still fail a
run. Routine success stays quiet; new/changed failures or required actions are
reported. No automatic archive retention, off-site backup service or replacement-host/
empty-image-store recovery is claimed. The independent key copy is separately
verified as described above.

## Empty-image-store recovery verification (2026-10-28)

The actual encrypted Mac archive for deployed source `ed8d0e3` recovered into
a disposable Docker engine with an independently empty containerd content store.
Authenticated decryption, every capsule member hash and exact archived source
bytes passed before upload. The engine had zero images, containers and volumes,
a different engine ID, private mount/network/PID namespaces and no external
route. An expected restore attempt rejected the absent image before creating
resources. `docker image load --input images.tar.gz` then loaded all three saved
IDs; each matched the authenticated capsule.

The archived `scripts/backup.py` module's existing restore function ran
with only its process-local Docker target pointed at the disposable socket.
Its PostgreSQL restore verifier matched every row, migration head, referenced
photo and complete media checksum inventory in fresh volumes. The saved web
image ran `npm test` with network disabled: **20 passed, 0 failed, 0 skipped**.
No build, pull, owner credential transfer, restored API/web server or promotion
was needed. See [the rehearsal record](empty-engine-recovery.md) for isolation
and three failed environment probes corrected before the passing fresh run.

The successful project's containers/network/volumes, temporary daemons, owned
cgroup, all four attempt directories and earlier test namespace were removed.
Live trial IDs, image IDs, starts, running state and mounts matched before/after.
After cleanup, the loopback login returned HTTP200 and unauthenticated
`/api/v1/inventory` returned HTTP401. The encrypted archive checksum remained
unchanged. Private logs/receipts remain under the original operator checkout's
ignored `.harness-results/empty-engine-rehearsal/`.

This documents operational verification; there is no app, schema, dependency or
deployment change. The full API suite, web build and browser interaction suite
were not rerun. This test reused the installed worker OS/kernel and runtime
binaries, so replacement-host provisioning and off-site recovery remain untested.
Success applies to this archive/release, not every future scheduled backup.

## Immediate storage selection verification (2026-10-29)

Choosing a location now sends one revision-checked move immediately. The selector
shows only the last confirmed assignment while saving; nearby status text reports
“Saving location…” and then “Added to Comic box B.” after confirmation. Selecting
Unassigned removes the assignment with history retained. There is no separate
Save location action. Creating a location still does not move the copy or change its confirmed selection.

Host `npm run lint`, `npm test` and `npm run build` in `apps/web` passed; Node
boundary checks reported **20 passed, 0 failed, 0 skipped**. Worker
`sh scripts/test-web.sh` passed a fresh disposable production build/typecheck,
Node tests, migrations and authenticated HTTP/photo-persistence smoke checks.

`RELICRAT_REAL_UI_TEST=1 npm run test:browser` against a separate fresh production
stack passed **14 scenarios, 0 failed, 0 skipped**. The host selected its already
installed Chromium through `PLAYWRIGHT_CHROMIUM_EXECUTABLE`; the first launch
without that override failed because the expected browser binary was absent,
before any scenario ran. Screenshots were enabled through `RELICRAT_SCREENSHOTS`.
The focused regressions exercise immediate single-flight saving, unchanged
selection/no extra write on reload, rejection rollback, uncertain committed
writes requiring review, stale revisions, history-refresh failure after confirmed
success, explicit location creation, unassignment, and preserved copy/photo/history.

Desktop/mobile captures were inspected together; the confirmation sits beside
the selector, mobile has no horizontal overflow, and the existing layout remains.
One scoped Impeccable detector pass returned no findings. Private logs and
captures are under the operator checkout's ignored
`.harness-results/storage-selection-save/`. Disposable test resources were cleaned
up separately from the owner's trial. The live preview/deployment was not changed.

This is a web-only interaction change with no migration or dependency change.
The full API suite and backup/recovery rehearsal were not rerun; existing API
revision/history semantics are unchanged. Native select changes, including
keyboard changes, save immediately as described by the control's helper text.

## Three-copy collection trial regression (2026-10-29)

The real-browser scenario now creates three physical copies through the UI:
 two share one edition, and the third uses another edition of the same catalog
item. After reload, it verifies exactly three stable copy IDs, unchanged creation
times, separate photo IDs and exact bytes, independent storage, retained movement
and identification history, and rejection of a photo requested through the wrong
copy. Catalog/release creation must not add ownership. The scenario refuses a
nonempty inventory and runs only in the explicitly enabled disposable stack.

- `python3 -m unittest discover -s scripts -p 'test_*.py' -v`:
  **14 passed**, including three focused SSH relay checks.
- Worker `sh scripts/test-web.sh`: production build/typecheck, **20 Node tests**,
  fresh migrations, authenticated HTTP smoke and photo persistence after API
  recreation passed; exact disposable cleanup verified.
- `RELICRAT_REAL_UI_TEST=1 npm run test:browser`: **14 passed, 0 failed,
  0 skipped** against a separate empty stack on Mac loopback port 63112. The host
  selected its installed Chromium using `PLAYWRIGHT_CHROMIUM_EXECUTABLE`.
- The revised SSH helper also passed a deliberately recreated conflicting Docker
  subnet while the live login returned 200 and unauthenticated inventory 401.
  Interactive worker access passed. See [the worker route regression](worker.md).

The first attempt was interrupted by that routing collision before browser
validation. The final run used the fixed helper. Both the failed run's exact
resources and the successful run's containers, volumes, networks, generated
images, staging and temporary bridge were removed; retained restores and the
owner's trial were preserved. Private evidence is under the operator checkout's
ignored `.harness-results/collection-trial-regression/` and
`.harness-results/worker-recovery-20261029/`.

There is no app, schema or credential change. The full API pytest suite,
backup/recovery rehearsal and a fresh VM-container build were not rerun for this
harness/transport change. The existing VM container already supplies Python;
the Dockerfile now makes that requirement explicit for future builds.

## Collectible detail clarity (2026-10-29)

The owner completed the Copper cover exercise but found catalog/release/linking
language and separate create/save controls confusing. The record now asks “What
is this?”, uses collectible and edition/variant terminology, places edition
creation beside its selector, and presents one primary Save details action.
Saved details and pending choices are separate. Successful edition creation closes
its empty form and retains keyboard focus on the disclosure; assignment still
requires the existing explicit revision-checked save. Unknown editions, retained
history, stale revisions and uncertain-write locks keep their existing behavior.

- Host `npm run lint --prefix apps/web`, `npm test --prefix apps/web` (**20 passed**),
  browser-test syntax and `git diff --check` passed.
- Worker `sh scripts/test-web.sh` passed production build/typecheck, **20 Node
  tests**, fresh migrations and authenticated HTTP/photo-persistence smoke after
  API recreation. A final web rebuild/typecheck included the visual fix batch.
- Final `RELICRAT_REAL_UI_TEST=1 npm run test:browser` with installed Chromium:
  **16 passed, 0 failed, 0 skipped**, on a separate fresh disposable stack.
  Checks include Enter creating only the edition, pending/saved distinction,
  explicit assignment, collapsed-form keyboard focus, long untrusted names at
  1440/768/390px and doubled root text size, and existing three-copy/auth/conflict
  regressions. Relevant runtime and browser-test source hashes matched the worker.
- Initial desktop/phone captures were inspected together. One fix batch collapsed
  successful edition creation and wrapped long pending names. The focused long-name
  check failed on the previous build's desktop overflow and passed in the final
  full suite. Its first concurrent probe timed out before the UI assertion; the
  meaningful reproduction was serial. Final desktop/phone captures confirmed the
  fix. One manual design detector pass returned no findings; the incumbent visual
  system and sidecar were preserved.

Both the successful test project and its preliminary web integration project
were scoped for cleanup; the temporary bridge and uploaded staging were removed.
Private evidence remains under the operator checkout's ignored
`.harness-results/clear-collectible-details/`. The live trial's original container
IDs remained running, with no published ports. This UI-only change has no API,
schema, dependency or credential change. Full API pytest and backup/restore were
not rerun. Human review/merge and a later trial upgrade remain separate steps.

## Copy-first title and edition editing (2026-10-29)

After the clarified catalog flow still confused the owner, saved copies now begin
with their existing title and an optional edition field in one Edit this copy
form. Ordinary edits do not read catalog lists, create shared records, match
identities or add ownership. The former matching workflow remains available
under a closed Advanced disclosure. Saved-copy status replaces unmatched-as-
unfinished wording in the everyday flow. Personal labels and catalog identities
remain distinct; see ADR 0003 and the inventory contract.

- `python3 scripts/test-api-remote.py relicrat-worker`: **113 passed**, zero
  skips/expected failures, **25 deprecation warnings** (Starlette/httpx and Alembic
  path splitting), followed by successful full downgrade to base and upgrade
  through 0005. Covers atomic/no-op/stale/concurrent edits, meaningful copies,
  metadata/media preservation, literal label search, rollback and migration
  defaults/round trips. A subsequent focused run of the direct database-constraint
  case passed, including duplicate audit-revision rejection.
- Host `npm run lint --prefix apps/web`, `npm test --prefix apps/web` (**21 passed**),
  Python compilation, browser-test syntax and `git diff --check` passed.
- Worker `sh scripts/test-web.sh`: production build/typecheck, **21 Node tests**,
  fresh migrations, authenticated HTTP/photo-persistence smoke and scoped cleanup
  passed. A separate fresh production stack hosted browser verification.
- `RELICRAT_REAL_UI_TEST=1 npm run test:browser`: **21 passed, 0 failed, 0 skipped**.
  Includes real copy-title/edition persistence through subsequent reconciliation,
  exactly three physical copies, unchanged media/storage/history, no automatic
  shared-record creation, explicit advanced matching and existing owner boundaries.
  The new copy-first cases cover prefilled title, one save, edit history/reload,
  validation, stale revisions, uncertain commits and unchanged inherited editions.
  Two subsequently added edition-read checks were run with `--test-name-pattern`:
  **2 passed**, no failures/skips, covering unavailable reads and cancellation when
  changing copies. The production runtime was unchanged between these runs.
- `python3 scripts/test-operator-backup.py` on the disposable worker snapshot:
  actual capture/restart, source destruction, fresh offline restore and independent
  schema/row/media comparison passed with a real edited title, edition and audit
  event. All five damaged-bundle modes were rejected as expected; exact operator
  test resources were cleaned up. No restored API/web server was promoted.
- Desktop1440/phone390 captures were inspected together. The primary form precedes
  photos/storage; advanced matching is closed. No visual fix batch was needed.
  One mechanical design scan returned no findings. The existing design record,
  sidecar, palette and native control patterns were preserved.

Private evidence is under the original operator checkout's ignored
`.harness-results/copy-first-details/`. Browser/API/recovery work used synthetic
resources only. The owner trial was not migrated or changed. Migration 0005 is
additive, but its downgrade intentionally drops personal edition labels and edit
history; capture and verify recovery before rollout, and never automatically
use a destructive schema downgrade as a UI rollback. Empty-image-store/off-site
recovery were not repeated for this feature. Human review, merge and a deliberate
API/schema/web upgrade remain required before this is on the live trial.

### Title-only browser intake (2026-10-29)

The browser now requires a nonblank title for new finds, using native required-field
validation plus a trimmed-content check. Notes, edition, photos, storage and catalog
matching remain optional. API notes-only intake and existing records are unchanged;
there is no migration or dependency change.

- `npm run lint --prefix apps/web`: passed.
- `npm test --prefix apps/web`: 21 passed, no failures/skips.
- Worker `sh scripts/test-web.sh`: production build/typecheck, 21 Node checks,
  fresh migrations and authenticated HTTP/photo-persistence smoke passed; scoped
  cleanup passed.
- `RELICRAT_REAL_UI_TEST=1 npm run test:browser`: 23 passed, no failures/skips.
  The intake regression rejects empty/whitespace titles even with notes, saves
  exactly one copy from a title alone with other fields unset, then adds photos,
  storage and search. Optional notes and uncertain-save review remain covered.
- Desktop and phone intake captures were inspected together; no layout changes
  or visual fixes were needed. `node --check apps/web/tests/inventory.browser.mjs`
  and `git diff --check` passed.

Private evidence is in the operator checkout's ignored
`.harness-results/title-only-intake/`. All browser/integration data was disposable
and synthetic. The full PostgreSQL API suite and backup recovery were not repeated
for this browser-only change. Human review and merge precede preview deployment.

### Records setup and personal observations (2026-10-30)

The first specialized collection setup is Records; Other keeps generic entry.
Setup is optional, server-persisted, revision-checked and previews without creating
ownership. Personal artist/format/type edits retain physical identity and history.
Preferences never remove saved values or infer shared catalog matches.

Validation used disposable synthetic data only:

- `python3 scripts/test-api-remote.py relicrat-worker`: **133 passed**, no skips,
  30 existing Starlette/httpx and Alembic configuration deprecation warnings.
  Includes preference/copy concurrency, failed transaction rollback, validation,
  direct database constraints, legacy-client preservation, literal artist search,
  populated upgrade/downgrade tests and the full migration cycle.
- `npm run lint --prefix apps/web`, `npm test --prefix apps/web`: passed;
  **22 Node boundary checks**, including protected setup routes/origins.
- Worker `sh scripts/test-web.sh`: production build/typecheck, 22 Node checks,
  fresh migrations, authenticated HTTP/photo-persistence smoke and scoped cleanup
  passed. Final API/web images were subsequently rebuilt on fresh owned test data.
- `RELICRAT_REAL_UI_TEST=1 npm run test:browser`: **30 passed**, no failures/skips.
  Covers skip/cancel/back, preview without writes, adjustable fields, title-only
  records, explicit draft discard, hidden populated fields, stale/uncertain setup
  saves, generic fallback, cross-reload preferences and real artist search, plus
  all existing owner/photo/storage/catalog scenarios. Running source fingerprints
  matched the final review source.
- `python3 scripts/test-operator-backup.py`: actual capture/restart, source
  destruction and fresh offline restore preserved configured preferences, real
  artist/format/type values and before/after audit events along with all rows,
  schema and exact media. All five damaged-bundle controls were rejected as
  expected. Operator resources were cleaned; no restored API/web was promoted.
- Desktop and phone setup/preview/entry captures were inspected in bounded passes;
  native controls and the incumbent design were retained. Python compilation,
  browser syntax and `git diff --check` passed.

Initial verification exposed a test SQL binding mistake, PostgreSQL's equivalent
constraint text changing during dump/restore, and two browser timing/label
assumptions. These were corrected; constraints now use explicit text casts,
without weakening exact recovery comparisons. The final API, recovery and full
browser runs above passed. Earlier failed logs remain private for diagnosis.

Evidence is under the operator checkout's ignored `.harness-results/records-setup/`.
Migration0006 upgrade preserves legacy rows/events; its downgrade loses preferences,
record observations and record-only edit events. Never use that downgrade as an
automatic live rollback. A verified fresh recovery capture, review/merge and
API/schema/web rollout are required. The existing owner trial was not modified;
empty-image-store and off-site recovery were not repeated for this feature.

## Visual theme authoring and appearance (2026-10-31)

This change adds an owner appearance editor and an AI authoring contract. Users
choose/edit colors, body/heading fonts, spacing, corners and density; preview stays
in a labeled sample until explicit apply. The API rejects unsupported values,
unknown keys, CSS/URLs and insufficient palette contrast. Applying locks a separate
singleton row and checks an independent revision; previews never write inventory
or preferences. The AI workflow generates a prompt or downloadable Markdown
file, then validates imported JSON. No AI provider or external request is added.

Migration `0008_appearance` adds only appearance settings. Database checks bound
the document and enforce required keys, color syntax and supported options. The
API additionally enforces text contrast on preview/read/apply. There are no theme
timestamps or history. Downgrade locks and refuses a customized theme; export and
explicitly restore default before a reviewed rollback. The earlier Comics
migration test now upgrades specifically to the migration it exercises instead
of assuming it is forever the latest schema. Existing inventory and collection
preferences remain independent. See [ADR 0007](decisions/0007-appearance.md).

Validation executed against synthetic disposable data:

- `python3 scripts/test-api-remote.py relicrat-worker`: **201 passed**, zero skips
  or expected failures, 44 warnings; full downgrade to base and upgrade through
  `0008_appearance` passed and resources were removed. This includes parser,
  contrast, direct SQL constraints, rollback, concurrent saves, authentication,
  preview isolation, no-op/stale saves and guarded downgrade tests. Evidence:
  `.harness-results/20261031T151857.257652Z/run.log`.
- In `apps/web`, `npm test`: **26 passed**, zero skips/failures; `npm run lint`
  and `npm run build` passed. The disposable worker web image also passed its
  production build/typecheck. Local build warned about the pre-existing root
  lockfile; it was left untouched.
- With the disposable worker stack bridged on loopback `63122`, the focused
  browser command `PLAYWRIGHT_CHROMIUM_EXECUTABLE=<existing chromium headless shell>
  RELICRAT_TEST_WEB_URL=http://127.0.0.1:63122 RELICRAT_REAL_UI_TEST=1
  node --test --test-name-pattern='appearance|real theme'
  tests/inventory.browser.mjs` passed **3 scenarios**, zero skips/failures.
  It checks isolated drafts, manual choices, rejected imports, Markdown download,
  no inventory writes, unconfirmed-save reload, real persistence and stale saves.
- `impeccable detect --json apps/web/app/appearance.tsx
  apps/web/app/inventory-client.tsx apps/web/app/globals.css` returned `[]`.
  This mechanical result is not a whole-interface accessibility certification.

The first API run had 200 passes and one failure: the older Comics migration test
hard-coded `0007_comics` as the current head after a failed downgrade. The test
was pinned to its intended revision before the final passing run. Sandboxed local
Node servers could not complete; they were interrupted and the same Node checks
passed with loopback access. Playwright's default browser was absent; the focused
checks used the existing Chromium executable through the runner's supported
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` setting.

The guide is [packages/themes/AUTHORING-PROMPT.md](../packages/themes/AUTHORING-PROMPT.md).
One active owner theme is supported; there is no integrated model, downloaded
font, custom layout/navigation, theme history, or production rollout. Login keeps
the default appearance, and a default-to-saved-theme flash can occur after page
load. Existing full database backup logic includes all public tables; backup and
restore were not rerun for this increment. No real data or live trial was used.

The complete browser regression then passed **40 scenarios**, zero skips/failures,
including real authentication, photos/storage, Records, Comics and theme persistence.
It used the disposable no-port worker stack and the repository loopback bridge:

```sh
cd apps/web
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/Users/bryanclark/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell \
RELICRAT_TEST_WEB_URL=http://127.0.0.1:63122 \
RELICRAT_REAL_UI_TEST=1 \
RELICRAT_APPEARANCE_SCREENSHOTS=/Users/bryanclark/Developer/relicrat/.harness-results/appearance/review \
npm run test:browser
```

The final local correction makes section spacing affect the isolated sample's
padding and action separation. The worker production image was rebuilt, then the
same browser command with `node --test --test-name-pattern='appearance|real theme'
tests/inventory.browser.mjs` replacing `npm run test:browser` reruns the affected
scenarios, including a computed preview-spacing assertion and final captures.
Evidence for the full regression is
`.harness-results/appearance/relicrat-appearance-browser-final.log`; the production
build is `relicrat-appearance-build-final.log` in that same directory.

The final affected browser rerun passed **3 scenarios**, zero skips/failures.
`relicrat-appearance-browser-spacing.log` records that result. Final valid captures
are `.harness-results/appearance/review/appearance-desktop.png` (1440 px wide) and
`appearance-mobile.png` (390 px wide), opened and checked together after the last
correction. They show the isolated Archive sample alongside the unchanged app and
synthetic inventory. A fresh independent Impeccable finish review returned
**ship**, with no material fixes, for this appearance extension and both captures.
No design-system replacement or production-readiness claim is implied.

The disposable worker project `relicrat-appearance-sm5ib6uypd` was removed after
verification. Containers, volumes, networks and project-tagged images were checked
absent; temporary source files were removed and the loopback bridge stopped.
Cleanup evidence is `.harness-results/appearance/relicrat-appearance-cleanup.log`.
`git diff --check` passed. No trial deployment or backup/restore run occurred.

## CSV importer verification (2026-10-31)

The importer uses generated synthetic CLZ/Discogs fixtures. No owner exports are
committed, uploaded to tests or imported into the trial. The full API suite passed
215 tests before adding one additional direct-constraint test; the final focused
import suite exercises parsing, preview read-only behavior, status/quantity
rejection, rollback, retained evidence, exact-file replay, concurrent retries,
provenance constraints and guarded downgrade. The existing API runner also checks
empty-schema migration downgrade/upgrade. Node proxy/security checks passed 27
tests; web TypeScript, production build and HTTP/photo-persistence smoke passed.

Run the dedicated importer browser scenarios separately against an explicitly
owned disposable stack:

```sh
RELICRAT_TEST_WEB_URL=http://127.0.0.1:<disposable-test-port> \
PLAYWRIGHT_CHROMIUM_EXECUTABLE=<installed-chromium-path> \
node --test apps/web/tests/import.browser.mjs
```

Both importer scenarios passed with no skips: UI preview/confirmation/import of a
large synthetic collection, exact-file replay prevention, original-field history,
paging, scoped search, phone layout, invalid rows and uncertain-write recovery.
Screenshots were inspected for fit and readability. The normal inventory browser
suite ran with the large collection retained: 44 scenarios passed; its explicitly
empty-inventory scenario correctly refused to run. That scenario passed on a
separate fresh stack. Its first isolated attempt timed out while loading details;
API logs confirmed the synthetic save, and a fresh isolated rerun passed with no
application or guard changes. Keep this transport limitation distinct from an
application failure; do not weaken the empty-inventory safety check.

A separate named-volume synthetic capture/restore verified batch provenance,
original unknown/source fields, quantity-expanded physical-copy UUIDs, every row,
schema and media fingerprints. Restore API/web were never started. Exact owned
capture/restore resources were removed after success. This is development
verification; it is not permission to import real collections into the trial or
a production-readiness claim. Migration 0009 still needs the explicit release
backup/rehearsal plan before deployment. Source evidence survives normal full
backups; downgrade refuses retained import batches.

Final focused PostgreSQL import run: **14 passed**, two dependency/configuration
deprecation warnings, no skips. Direct SQL attempts to violate source, digest,
parser-version, counts, evidence-object and row/copy bounds were rejected;
restrictive references prevented deleting retained copies or batches.

## Grouped collection verification (2026-10-31)

The shared inventory filter/group read change passed the full PostgreSQL API suite
(**219 passed**, 46 dependency/configuration deprecation warnings, no skips).
After grouping metadata moved into the bounded type configs, the affected
inventory/group/config suite passed **60 tests**, one deprecation warning, no
skips. These cover full-result counts before pagination, exact member scope,
literal wildcard/markup keys, missing artists/series, stable ordering, separate
case values, exact storage/unassigned filters, deleted records and owner access.
No schema migration or data write was introduced.

`npm run lint --prefix apps/web` passed. Node proxy/security checks passed **28 tests**. The worker web harness passed production build, static/Node and
HTTP/photo-persistence smoke checks; final source was rebuilt after the UI fixes.
The existing inventory browser suite explicitly selects Individual copies for its
original workflows and passed **45 scenarios**, no skips/failures, on fresh
synthetic data. Both existing CSV browser scenarios then passed on the updated
browse screen. Three grouped-browser scenarios passed with the resulting large
synthetic collection retained and extended, covering independent group/member
pages, counts, search, unknown artists, draft retention, exact storage, obsolete
reads and a failed location page beyond the first 100.

A final presentation correction indents group members with the existing theme's
rule color and uses count-neutral summary wording. After the final rebuild,
**all three grouped scenarios passed again**, no skips/failures, with generated
large-volume intake. Phone overflow was checked in the browser and the final
mobile capture was inspected. Earlier desktop/mobile captures were also reviewed.

Run the focused grouped suite only on an explicitly owned disposable stack:

```sh
RELICRAT_TEST_WEB_URL=http://127.0.0.1:<disposable-test-port> \
PLAYWRIGHT_CHROMIUM_EXECUTABLE=<installed-chromium-path> \
node --test apps/web/tests/groups.browser.mjs
```

The suite generates its own source CSVs; never use owner exports or the trial URL.
No trial or collection data was used. Backup/restore was not rerun for this
read-only/no-migration increment. Runtime API/web file hashes are checked against
the reviewed source and only the owned test stack, bridge and staging are removed
after success. Build cache and previous retained recovery resources are outside
cleanup scope. Deployment remains a separate reviewed release step.

## Approved brand-derived factory theme (2026-10-31)

The owner accepted the reviewed ivory/white, charcoal and burgundy factory palette,
with sans body/headings, balanced spacing, soft corners and comfortable density.
`packages/themes/relicrat-default.json`, runtime `DEFAULT_THEME`, and all eight
initial CSS roles match. Login uses those same light tokens. The dark preset uses
forest surfaces and contrasting light-gold actions; existing saved dark values are
not silently replaced. No logos, mascot assets, layouts, navigation or theme-schema
fields were added. See the [shared decision record](design/README.md) and
[appearance ADR](decisions/0007-appearance.md).

Migration `0010_brand_default` changes the column default and adopts the new palette
only for exact legacy factory values at revision zero. Changed rows increment
revision so open clients must review stale saves. Previously saved factory choices
and custom values are preserved. Downgrade maps exact new defaults back to old
values with another revision increment, including an explicitly selected new
factory palette; other custom values survive. A re-upgrade retains the nonzero
revision and old palette until an explicit default restore/apply. Historical
migration 0008 is unchanged.

Executed validation, synthetic disposable data only:

- `python3 scripts/test-api-remote.py relicrat-worker`: **206 passed**, zero skips
  or expected failures, 68 warnings. Full downgrade to base and upgrade through
  0009 passed. Five new PostgreSQL cases cover fresh installation, column defaults,
  pristine old values, saved old values, custom values, monotonic revisions and
  downgrade/re-upgrade preservation. Evidence:
  `.harness-results/20261031T181139.144682Z/run.log`.
- In `apps/web`, `npm test`: **26 passed**, zero skips/failures. `npm run build`
  passed compilation and typechecking locally and in the disposable worker image.
  The local build's pre-existing root-lockfile warning is unrelated and unchanged.
- A standard-library AST/JSON/CSS comparison confirmed that the approved portable
  export, runtime theme and eight browser color roles agree. Existing preset tests
  validate all required text contrast pairs through the API parser. The proposed
  light/default text pairs have a minimum 6.21:1; the dark palette minimum is 6.92:1.
- `impeccable detect --json apps/web/app/globals.css` returned `[]`.
- The four affected browser scenarios passed with zero skips/failures using:

```sh
cd apps/web
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/Users/bryanclark/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell \
RELICRAT_TEST_WEB_URL=http://127.0.0.1:63123 \
RELICRAT_REAL_UI_TEST=1 \
RELICRAT_DEFAULT_SCREENSHOTS=/Users/bryanclark/Developer/relicrat/.harness-results/brand-default/review \
node --test --test-name-pattern='appearance|real theme|approved factory' tests/inventory.browser.mjs
```

The browser checks cover login/initial fallback, real light/dark appearance,
manual controls and isolated preview, unsafe import rejection, Markdown download,
unconfirmed-save reload, actual persistence and stale-save rejection. Full
inventory/browser coverage from the preceding theme increment remains historical;
this palette update did not rerun all 40 scenarios. Final screenshots are
`default-desktop.png`, `default-mobile.png`, `dark-desktop.png`, `dark-mobile.png`,
`login-desktop.png` and `login-mobile.png` under
`.harness-results/brand-default/review/`. All six were opened and inspected together.
There is no whole-interface accessibility certification. Backup/restore and live
rollout were not run.

A fresh independent Impeccable finish reviewer returned **ship** for this
palette-only update, with no material fixes, after examining all six final
captures and the synchronized token documentation. An additional enabled/focused
keyboard-pressed check confirmed `active=true`, burgundy
`rgb(130, 59, 61)` background and white text on the primary action; no further UI
correction was required. `git diff --check` passed.

Disposable project `relicrat-brand-default-ogrhuwjm2m` was removed; its containers,
volumes, network and tagged images were checked absent, temporary sources deleted,
and the loopback bridge stopped. Evidence is
`.harness-results/brand-default/relicrat-brand-default-owned-cleanup.log`. The first
reused temporary cleanup helper exited before touching resources because it
expected a different run's manifest; cleanup then used the exact project/path
manifest created for this task. No global cleanup or live services were used.

## Reviewed CLZ storage mapping (2026-10-31)

Import history now offers a CLZ-only source-label → destination → paginated
preview → explicit confirmation flow. Previewing does not write. Creating a
physical location is separate and does not place copies. Each confirmed move
reuses ordinary manual storage history in a single transaction; no schema or
migration changes. Never-placed active owned copies alone are eligible. Already
placed copies, previous manual unassignments and inactive copies are preserved.
The complete label cohort and destination are bound to the review token; a
changed copy revision/status or destination invalidates the whole confirmation.
Concurrent confirmations and races with manual placement serialize on copy locks.
Failed/unconfirmed confirmations discard the UI confirmation and require a fresh
preview; uncertain location creation requires reload/inspection before another
creation. Saves are not automatically retried. Original import rows remain intact.

Limits: one label in one CLZ batch per confirmation; common surrounding whitespace
is normalized, case/internal text remain significant; empty labels excluded and
labels longer than 500 characters explicitly unsupported. Discogs folders remain
source information. No automatic import-time placement, bulk reassignment or bulk
undo. The existing individual location control remains available for corrections.

Validation used generated fixtures and disposable worker projects only:

- `python3 scripts/test-api-remote.py relicrat-worker`: **234 passed**, zero skips
  or expected failures, 70 existing Alembic configuration deprecation warnings;
  full upgrade/downgrade round trip through 0010 passed.
- After readability-only backend formatting and the added manual-placement race:
  `python3 scripts/test-api-remote.py relicrat-worker tests/test_import_storage.py`:
  **10 passed**, zero skips/expected failures, one existing warning. Covers pure
  preview, quantity-expanded physical copies, exact batch/label scope, pagination,
  unusual text, input/auth/source boundaries, preservation, source evidence,
  replay, whole-transaction rollback and actual PostgreSQL concurrent writers.
- Disposable worker `sh scripts/test-web.sh`: production Next build, TypeScript,
  **29 Node tests** with zero skips/failures, authenticated API smoke and persisted
  photo after API recreation passed. Final-source images were rebuilt on fresh
  disposable volumes before real browser checks.
- With `RELICRAT_TEST_WEB_URL` pointing only to the disposable loopback bridge,
  `RELICRAT_REAL_UI_TEST=1 node --test apps/web/tests/inventory.browser.mjs`:
  **46 passed**; `node --test apps/web/tests/import.browser.mjs`: **2 passed**,
  including 1,915 generated physical copies. Zero skips/failures. The guarded
  empty-inventory real workflow completed before any CSV batches were seeded.
- `node --test apps/web/tests/storage-mapping.browser.mjs`: **4 passed**, zero
  skips/failures on the final rebuilt source. Covers explicit destination creation,
  copy pagination, acknowledgement/double-click protection, all mapped copy states,
  preserved placement, original evidence, stale review, ambiguous mapping and
  ambiguous location creation. Initial fixture columns and a test's page-wait scope
  were corrected; failure logs remain in ignored local evidence. The compact
  radio-control visual fix affects only the new flow; its four scenarios and build
  were rerun afterward. Existing inventory/import suites were not unnecessarily
  repeated for that styling-only adjustment.

Desktop/mobile mapping captures were opened and inspected: compact native radio
choices, wrapped copy identifiers, readable preservation counts and explicit final
confirmation. The 390px check found no horizontal overflow. This is focused visual
verification, not whole-interface accessibility certification. Local evidence is
under `.harness-results/storage-mapping/`; synthetic screenshots are in the
operator checkout's matching ignored evidence folder. No collection data was used
as test input. Backup/restore and live rollout were not run for this increment.

## Read-only barcode camera trial (2026-10-31)

The inline scanner captures video only and lazily decodes UPC-A/UPC-E/EAN-8/EAN-13
on-device. It displays a bounded string and any detected supplement; no form
prefill, persistence, provider call or ownership change. A reading stops the
camera; explicit stop/close, page exit/backgrounding, disconnect, error and a
one-minute limit stop it too. Cancelled runs dispose of late permission responses
and own distinct video elements to avoid interference with subsequent scans.
The scan/stop button stays mounted to preserve keyboard focus; a successful
reading focuses its heading. No API or migration changes.

The locally bundled ZXing browser layer 0.1.5 and decoder peer 0.21.3 replace a
custom decoder and sampling loop while supporting the existing Node 22 images.
Newer pairs requiring Node 24 were rejected before final verification. The
software decoder is needed because native BarcodeDetector is not consistently
available across browsers. No runtime CDN or provider authentication is used.
The existing owner's collection and Mac-loopback bridge were untouched. Private
HTTPS phone access and physical-device autofocus/lighting/permission validation
remain pending, not established by headless camera tests.

Executed checks, generated fixtures and disposable worker projects only:

- In `apps/web`, `npm test`: **31 passed**, zero skips/failures; `npm run lint`
  passed. The package audit reported zero known vulnerabilities for the pinned
  dependency pair. No optional install-script approval was changed.
- Final worker `sh scripts/test-web.sh`: production build/typecheck, **31 Node
  tests**, authenticated HTTP smoke, migration initialization and exact photo
  persistence after API recreation passed. Its own containers, volumes, network,
  tagged images and temporary staging were removed with exit zero.
- Existing browser selection `add-first workflow|storage selection saves once|password-manager autofill`:
  **3 passed**, zero skips/failures. Unselected scenarios were not run. The full
  API and 46-scenario inventory browser suites were not repeated for this
  frontend-only increment.
- `node --test apps/web/tests/barcode.browser.mjs`: **6 passed in Chromium and
  6 passed in WebKit**, zero skips/failures. An independently drawn synthetic
  UPC-A SVG is streamed through a canvas camera into the actual decoder. Checks
  cover leading zeroes, no post/upload/provider requests, draft preservation,
  video-only constraints, rescan, permission denial/retry, cancelled late streams,
  stop/close, page exit/backgrounding, timeout and insecure-context recovery.
  Initial test selector, cross-browser camera-mock installation and continuous
  blank-frame generation were corrected. Failure logs remain private; final tests
  assert the synthetic camera replaces the real API before any scan.
- Two targeted Chromium capture scenarios passed afterward with full-page result
  and active-camera captures at 390px and 1440px. The active feed explicitly labels
  its generated synthetic frame. All four captures were opened and inspected;
  no horizontal overflow was found. These do not establish physical-phone focus,
  lighting, permission-dialog behavior or production camera performance.
- The mechanical design detector returned `[]`. Independent finish review returned
  **ship** for this scanner-only extension and supplied synthetic evidence, with
  no material fixes. The independent documenter confirmed documentation complete;
  the incumbent design-system files were preserved.

Evidence is under `.harness-results/barcode-camera/`; review captures are in the
operator checkout's matching ignored evidence folder. Full API tests, copied
backup/restore, phone network setup and live rollout were not run for this
frontend-only prototype. No claim of phone readiness is made until private HTTPS
and a hands-on device trial are complete.

## NAS private HTTPS adapter (2026-10-31)

A separate fixed-HTTPS-origin frontend preserves the Mac loopback frontend and
cookie scope. A NAS-loopback adapter pins Host/Origin, strips client forwarding
and authorization headers, relays only the HTTPS owner cookie, and enforces
Secure/HttpOnly/SameSite/host-only response attributes using the standard cookie
parser. Tailscale Serve supplies TLS outside the isolated worker. No app API,
migration or collection behavior changed; no provider credentials are in source.
See [the operator guide](private-phone-access.md) and its configuration templates.

Executed synthetic checks:

- `python3 -m unittest discover -s scripts -p 'test_private*py' -v`: **8 passed**,
  covering original Mac bridge regressions and phone authority/framing, duplicate
  headers, body/response preservation, trusted TLS headers, cookie isolation,
  malformed upstream headers/cookies and bounded failure behavior.
- A fresh disposable worker frontend configured with a synthetic HTTPS origin
  and loopback HTTP disabled passed real sign-in, Secure host-only session cookie,
  authenticated inventory/type reads, scanner rendering, hostile Host/Origin
  rejection, refusal of a valid token under the Mac cookie name, and logout
  revocation. No real owner credentials, images or collection rows were used.
- The disposable web harness production build/typecheck, 31 Node checks,
  authenticated smoke and photo persistence after API recreation passed before
  the HTTPS-origin test stack was created. The app source is unchanged from PR50.

Private activation, TLS and resource-cleanup receipts are operational evidence,
separate from these tests. Phone autofocus/lighting and actual browser permission
behavior still require an owner device trial; headless synthetic results do not
establish those. No full API suite was repeated for this adapter-only increment.

The privacy pass removes machine aliases, relay-container names, SSH ports,
identity/known-host paths and engine names from the adapter source. They live in
an owner-only local transport file. The adapter enforces strict SSH host-key
checking and no agent forwarding, and refuses symlinked, foreign-owned,
world/group-accessible or malformed transport files. The final bridge suite is
**10 passed**. This generic configuration does not expose operator values through
HTTP or Git. Public certificate-name disclosure is a separate owner choice.

## Reviewed barcode observations (2026-11-01)

A scanned UPC/EAN remains page-local until **Use barcode**, followed by the
ordinary **Save copy** or **Save details**. Type configs declare the supported
formats. Scans do not identify editions, fill titles or create ownership; camera
frames stay on-device. Saved observations can be replaced/removed, with retained
before/after value, format and supplement in revision-checked edit history.
Main digits participate in the existing literal inventory/group search. Unknown
is empty, leading zeroes survive, and several physical copies may share a code.

Migration `0011_copy_barcodes` is additive. Its database constraint bounds the
observation independently of API validation; upgrade preserves all older columns
and initializes unknown barcodes. Downgrade locks both relevant tables before
checking and refuses current or historical barcode loss, including barcode-only
edit events. Apply migrations and deploy API/web together after a verified backup;
never erase history to bypass the guard. Old clients omitting barcode preserve it.

Executed with generated data and isolated disposable projects only:

- `python3 scripts/test-api-remote.py relicrat-worker`: **258 passed**, 76 existing
  dependency/configuration warnings, no skips/expected failures; full downgrade
  to base and upgrade through 0011 passed. Tests cover strict strings/formats,
  supplements, SQL constraints, private reads/writes, duplicate physical copies,
  search, unchanged identities, corrections/no-ops/removal, stale revisions and
  upgrade/downgrade guards. Older migration tests now account for the extra empty
  column and nullable legacy history fields. Final writer-lock adjustment:
  `python3 scripts/test-api-remote.py relicrat-worker tests/test_barcodes_migration.py`:
  **1 passed**, six existing warnings, full migration round trip passed.
- In `apps/web`, `npm test`: **31 passed** and `npm run lint` passed. The worker
  `sh scripts/test-web.sh` passed production build/typecheck, Node checks,
  authenticated HTTP smoke and exact photo persistence after API recreation.
  Final source was rebuilt after disclosure cleanup and compact spacing changes;
  runtime file hashes for both test images matched the reviewed files.
- `node --test apps/web/tests/barcode.browser.mjs`: initial Chromium **8 passed**.
  After the final small presentation changes, both new intake/edit and failed-save
  scenarios passed again; the additional config-disable/format-rejection scenario
  passed separately. The final **9 scenarios passed in WebKit**, zero skips or
  failures. All use generated camera frames, not a real camera or owner data.
  Tests verify explicit attachment/save, draft retention, reload persistence,
  barcode search/removal history, type-change confirmation and camera shutdown
  when the saved-copy disclosure closes, as well as the existing camera lifecycle.
- `python3 -m unittest discover -s scripts -p test_backup.py -v`: **6 passed**.
  Worker `python3 scripts/test-operator-backup.py` passed a genuine synthetic
  capture, writer restart, source destruction, fresh offline copied restore and
  independent all-row/schema/history/media comparison, including corrected barcode
  and supplement values. All **five damage modes** failed at their intended
  boundaries; exact owned cleanup passed. The restored API/web never started.

Recovery verification exposed two existing issues: an equivalent PostgreSQL
varchar-array cast spelling for the import-source constraint, and an early Unix
socket readiness signal from PostgreSQL's initialization server. The fixture now
recognizes only that exact equivalent import predicate with changed-value/operator
negative controls; restore probes the TCP endpoint actually used by `pg_restore`.
The test now releases each receipt-owned disposable restore before starting the
next to avoid exhausting Docker's network pool alongside retained owner restores.
Earlier failed logs remain private; no broad cleanup or retained-restore removal
was used. The first local Node invocation required loopback access outside the
sandbox; its hung test processes were stopped and the rerun passed. WebKit was
installed into a task-local test directory before its passing run.

All four final full-page intake/saved-copy captures at desktop1440 and phone390
were opened and inspected. The mechanical detector returned `[]`; an independent
finish reviewer returned **ship**, no material findings, at this extension's
scope. Independent documentation added the barcode surface brief and preserved
existing design-system files and historical metadata drift. Physical-phone focus,
lighting, permissions and supplement capture remain unverified. Full inventory,
CSV and storage browser suites were not repeated. Evidence is under ignored
`.harness-results/barcode-intake/`; no owner deployment was performed.

### Configurable album barcode lookup (2026-11-01)

The type-definition config selects an installed provider, bounded mappings/value
translations, result count and cover previews. Album initially uses MusicBrainz;
Comics/Other retain manual intake. Suggestions are read-only until the collector
selects fields into a draft and uses the ordinary final copy/details save.

Validation used disposable synthetic PostgreSQL/media and generated camera/cover
fixtures, never owner exports, photos or scanned owner barcodes:

- `python3 scripts/test-api-remote.py relicrat-worker`: 269 passed, 76 warnings;
  full Alembic downgrade/upgrade passed. After adding extra redirect, compression
  and source-URL boundary checks, the focused command
  `python3 scripts/test-api-remote.py relicrat-worker tests/test_barcode_lookup.py tests/test_collection_types.py`
  passed 44 checks, one warning, plus the migration round trip.
- `npm test --prefix apps/web`: 32 passed; `npm run lint --prefix apps/web`
  passed. Worker `sh scripts/test-web.sh` passed the production build/typecheck,
  Node checks and existing auth/photo smoke. Final source was rebuilt afterward.
- `RELICRAT_TEST_WEB_URL=<private synthetic bridge> node --test apps/web/tests/barcode.browser.mjs`:
  Chromium 15/15 before the final focus guard; final WebKit 15/15, including the
  focus/stale-draft and rescan guards. The six lookup cases were also confirmed
  on Chromium after the draft-focus edits. The independent finish reviewer then
  identified a missing focus handoff in existing-copy editing; intake and
  existing-copy cases passed 2/2 after that correction, including an explicit
  active-focus assertion. No skipped/expected-failing cases in these runs.

An earlier concurrent WebKit run failed three cases during temporary bridge
errors and a draft-focus race. Checks were rerun sequentially after guarding
deferred focus against ongoing manual edits. Earlier logs remain private.
Public protocol probes used a synthetic all-zero barcode and an official API
cover example; both adapter search and cover decoding passed from a disposable
worker container after transient search timeouts. This is protocol evidence,
not guaranteed catalog coverage, service availability or physical-phone proof.

No migration or dependency is introduced. The existing backup/recovery suite and
unrelated inventory/CSV/storage browser suites were not repeated. The optional
API-only egress overlay has not been applied to the live private trial. Full
lookup behavior on that deployment remains a separate rollout check after merge.
Evidence is in ignored `.harness-results/barcode-lookup/`.

All four final intake and two existing-copy full-page desktop/mobile captures
were opened. The detector returned `[]`; the independent reviewer scored its
sole keyboard-focus finding **resolved** and returned **ship** in a verdict-only
recheck. Final runtime hashes matched reviewed API/web sources with no published
ports. The exact disposable test project, images, volumes, network, remote source
and temporary bridge were removed; retained restores and the owner trial were
untouched. Independent surface documentation preserves incumbent design files.

### Direct scan-to-lookup refinement (2026-11-01)

A supported scan for a type with a configured provider now starts lookup without
a barcode-confirmation click, through the same shared scanner in intake and
saved-copy editing. No-provider types retain Use barcode. Match/field review,
manual-text preservation, fallback and final saving remain explicit.

The worker built the production web/API images, ran `npm test` (32 passed) and
`npm run lint` (passed) inside the synthetic web image. Browser validation uses
`RELICRAT_TEST_WEB_URL=<disposable-loopback-bridge> node --test apps/web/tests/barcode.browser.mjs`
with the task's installed Chromium or WebKit executable/cache. Chromium and
WebKit each passed all 16 cases, with zero failures/skips. The independent
finish review returned **ship** with no material findings. The suite
checks automatic lookup in both forms, exactly one request per deliberate
scan/rescan, unsupported formats, canceled scans, provider failure/manual entry,
late responses, unchanged barcode-only flow and save/history boundaries.

Only generated synthetic camera/cover fixtures and disposable data were used.
Eight full-page desktop/mobile captures show automatic results, field review,
filled intake and filled existing-copy forms. The detector returned `[]`; running
images matched changed source files and exposed no host ports. API and recovery
suites were not repeated because API/schema/storage/networking are unchanged.
Physical-phone validation remains after merge/deployment; this change is not
deployed. Evidence: ignored `.harness-results/scan-direct/`.

The first disposable-stack attempt stopped before tests when Docker's predefined
address pool was exhausted. A nonoverlapping explicit private subnet, checked
against existing Docker networks and worker routes, was assigned only to this
test stack. No prior network, archive or retained recovery resource was removed.

### Optional catalog covers (2026-11-01)

Match review offers an unchecked Include catalog cover option. The ordinary final
save commits validated image/source metadata with copy/details, with no automatic
identity link, ownership change, photo replacement or duplicate source import.
See [cover contract](catalog-covers.md) for schema 0012 and downgrade refusal.

Validation used only generated fixtures and disposable databases/media:

- `python3 scripts/test-api-remote.py relicrat-worker`: 288 passed, 81 warnings,
  plus full migration downgrade/upgrade. The initial run exposed an older barcode
  migration test's hard-coded head; it now targets its own 0011 revision.
- Final focused API command with `tests/test_catalog_covers.py
  tests/test_catalog_covers_migration.py tests/test_media_api.py`: 22 passed,
  six warnings, plus migration round trip. Includes real commit acknowledgement
  loss, unflushed-failure cleanup, canonical provider IDs, source/origin checks,
  unavailable covers, stale edits, idempotency and database constraints.
- Worker production build/typecheck, `npm test` (32 passed) and `npm run lint`
  passed. Final API image was rebuilt after conservative file-cleanup changes;
  reviewed final API/web file hashes matched isolated image reads.
- Chromium full browser run: 19 passed, one test selector failed because its link
  accessible name also included image alt text. After correcting the selector,
  the six affected intake/edit/cover cases passed in Chromium and WebKit, with
  zero failures/skips. Full camera regressions passed in the initial run.
- Six desktop/mobile captures of cover review, pending selection and saved
  artwork were opened. Detector: `[]`. Independent finish review: ship, no
  blocking findings. Independent surface documentation preserves global design
  files and clearly marks this increment not deployed.

A copied-backup rehearsal moved the browser fixture into an isolated named-volume
database and proved its complete row/media state equal before capture. The
unmodified backup helper captured six imported covers and physical photos. After
destroying both synthetic sources, the copied backup restored offline with exact
row, migration and media fingerprints; restore application servers never started.
All owned recovery resources were removed. This schema/media rehearsal preceded
the final failure-cleanup-only correction, which passed the focused API checks.
The first harness attempts used the wrong helper function name and then correctly
refused the browser's tmpfs database; no invalid capture was accepted.

Private test-only subnet overrides worked around the exhausted automatic address
pool without deleting old networks/restores or changing deployment networking.
The browser API used a generated-image adapter override in its private test
Compose command; no production test hook or owner/export data was added. API and
backup helper source were otherwise unmodified by these fixture overrides.
Physical-phone validation and deployment remain separate. Private evidence is
under ignored `.harness-results/optional-cover/`.

### Lookup failure recovery (2026-11-01)

This increment keeps search separate from inventory writes: busy, timeout and
network failures explain recovery while preserving the editable draft. The
MusicBrainz adapter permits an eight-second read operation, with a twelve-second
elapsed budget checked at request, header and chunk boundaries. This is not a
hard whole-request timer; an in-flight operation can finish after the budget
before rejection. No automatic retry or new dependency is introduced.

Validation on disposable synthetic data:

- `python3 scripts/test-api-remote.py relicrat-worker tests/test_barcode_lookup.py tests/test_catalog_covers.py tests/test_media_api.py`: 41 passed, one warning; migration downgrade/upgrade roundtrip passed.
- Worker production build/typecheck, `npm test` (32 passed) and `npm run lint` passed.
- Chromium and WebKit, `node --test --test-name-pattern='lookup explains|lookup failure|a changed draft|late lookup|review an album match' apps/web/tests/barcode.browser.mjs`: five passed in each browser, zero failures/skips. Includes retained drafts, busy/timeout/network errors, late-response isolation and explicit final save.
- Source hashes matched the tested runtime. Design detector reported no findings; busy/timeout desktop/mobile captures retain the current theme and layout.

Private evidence is under `.harness-results/lookup-resilience/`. Full API and
backup/restore suites were not repeated: schema and storage are unchanged.
Live diagnostics observed intermittent provider failures; the reported example
later resolved successfully. That does not establish the cause of every earlier
failure or guarantee provider availability. No owner barcode or collection data
is included in fixtures. This change requires a web/API rollout after review;
it needs no migration, credential or network change.

### Mounted provider configuration (2026-11-01)

Observable behavior: an operator can mount complete per-type JSON definitions,
select an installed adapter and its field mappings, restart API and refresh web,
without rebuilding an image. Unknown/malformed/oversized configurations fail
startup instead of silently reverting to another service. Lookup suggestions
remain read-only and ownership remains an explicit save. Shared adapter failure
types no longer require routes or artwork saving to import MusicBrainz.

Validation: `python3 scripts/test-api-remote.py relicrat-worker
tests/test_collection_type_overrides.py tests/test_collection_types.py
tests/test_barcode_lookup.py tests/test_catalog_covers.py tests/test_media_api.py`
reported **84 passed, one warning**, followed by a migration downgrade/upgrade
roundtrip. New checks cover process-startup loading, one-type override/default
restoration, synthetic second-provider dispatch/mapping and no inventory writes,
safe failures, and rejected paths, filenames, IDs, credentials, URLs, duplicate
keys and uninstalled adapters. A task-only private subnet override avoided the
exhausted Docker address pool; it was restored after the disposable stack cleanup.

The optional Compose overlay's resolved model was checked on the worker with
synthetic settings: only API receives the read-only bind and config-directory
variable, host-path creation is disabled, and other services/networks/ports/media
mounts remain unchanged. The first model assertion expected an explicit false
value; Compose omits it during normalization. The corrected assertion checks its
false default. No application containers were started by that model check.

Private evidence: `.harness-results/provider-swapping/`. No provider calls, owner
fixtures, UI edits, browser reruns, full API suite or backup/restore rehearsals were
used for this increment. Config activation on the private trial requires a
reviewed rollout and recovery capture of the mounted definitions. No schema, new
dependency, credentials, provider selection or live deployment is changed here.
MusicBrainz remains the only bundled live-service adapter; synthetic swapping
proves the contract, not a Discogs integration.

### Movies and Blu-ray.com imports (2026-11-01)

Movie observations/preferences/history extend the existing physical-copy model;
`movie.json` defines title-first optional entry and title grouping. The Blu-ray.com
CSV preset previews its digest-bound mapping, preserves every original cell and
creates one owned item per row after confirmation. Disc counts do not expand
ownership. Unknown counts stay unknown; invalid or conflicting UPC/EAN codes
produce notes and remain source evidence. Read [the Movie contract](movies.md)
for exact mapping and migration/recovery requirements. No private export or live
owner inventory was used as a fixture or transferred to the test worker.

Executed checks on disposable synthetic data:

- `python3 scripts/test-api-remote.py relicrat-worker`: **322 passed, 89 warnings**,
  followed by the full migration downgrade/upgrade roundtrip. Includes new Movie
  create/edit/stale-save/history/legacy-omission, preferences/studio suggestions,
  SQL JSON/type/source constraints, barcode checksums/conflicts, transactional
  import retry/provenance and guarded `0013_movies` upgrade/downgrade cases.
- Corrected worker production build/typecheck, `npm test` (**33 passed**) and
  `npm run lint` passed. The fixed private proxy permits only the owner-protected
  studio GET route and bounded Movie lookup/cover paths.
- Chromium and WebKit: `node --test apps/web/tests/movies.browser.mjs`, **two
  passed each, zero failures/skips**. Each exercises Movie setup, title-only
  intake, custom format, retained edits/type changes, a 389-row generated import,
  warning review, retained source rows, exact-file retry and Movie filtering.
- Existing Chromium barcode suite initially passed 19 cases; two artwork-import
  cases required a generated-image server fixture because this isolated stack has
  no external network. With that fixture only in its private Compose command,
  `node --test --test-name-pattern='optional catalog cover|cover-only existing-copy|missing cover|lookup explains' apps/web/tests/barcode.browser.mjs` passed **four**.
- `node --test --test-name-pattern='invalid rows' apps/web/tests/import.browser.mjs`
  passed **one**, covering blocked invalid imports, changed-source preview and
  ambiguous-save recovery. Browser correction runs used separate generated data.
- Final API/web runtime hashes matched reviewed production files. Eight final
  full-page desktop/mobile captures were opened after one studio-proxy correction.
  Detector: `[]`. Independent finish review: **ship**, no actionable findings.

The first focused API run stopped at a preview assertion that expected an absent
optional field rather than its explicit null in the preview. The initial full
run found legacy migration tests assuming the previous column set, a brand test
that should target its own revision and logging disabled by earlier Alembic tests;
those checks were corrected without changing deployed migration history. The
initial WebKit history selector matched multiple synthetic batches; the final
selector opens the latest batch. A local sandbox-bound Node runner was stopped;
the completed Node evidence is the worker run, not the interrupted local run.

A copied-backup rehearsal retained a generated fixture with **1,556** Movie
observations and source rows, **eight** Movie history events, enabled preferences,
and **five** media files including a generated Movie photo. The browser tmpfs
state was first copied to a separate named-volume fixture and proved equal. The
unchanged backup helper captured it; both source projects were destroyed before
restoring the copied bundle offline. Every row, migration and media fingerprint
matched. Restore API/web servers never started, and all owned recovery resources
were removed. A local helper quoting error was fixed before any remote rehearsal
mutation. Explicit nonoverlapping internal test subnets avoided the exhausted
automatic address pool; live networks and retained manual restores were untouched.

Private evidence is under `.harness-results/movies/`. No live Movie import,
provider lookup, physical-phone test or deployment occurred. Migration 0013 needs
a fresh pre-rollout backup and offline restored-copy rehearsal before the live
schema/API/web release; populated Movie evidence prevents automatic downgrade.

### Type before barcode (2026-11-01)

Intake now presents What are you adding? before Scan barcode, within the existing
find form. Scanner/review actions retain explicit button types; only Save copy
submits ownership. No schema, provider selection, theme tokens or API behavior
changes. Existing type-change draft confirmation and scanner cleanup still apply.

Worker production build/typecheck, 33 Node checks and lint passed. Focused
Chromium/WebKit checks use `node --test --test-name-pattern='actual decoder|use a
scan explicitly|a failed copy save|review an album match'
apps/web/tests/barcode.browser.mjs`: four passed in each browser, zero
failures/skips. They exercise actual decoding with no writes, explicit copy save,
failed-save/type-change draft handling and reviewed Album filling. Changed web
source matched the runtime image; desktop/mobile screenshots were opened and
the single design detector returned `[]`. The initial browser launch stopped
before testing because its local Playwright dependency link was missing; the
completed runs use the existing installation. Private evidence is under
`.harness-results/type-first/`. API and backup/migration suites were not repeated
for this change to the form order; physical-phone testing and deployment are separate.

## Collection opening refinement (2026-11-01)

The signed-in initial workspace now leads with saved copies/search and keeps
intake beside it on desktop and after it on mobile. Add a find and the skip link
focus the intake heading. This frontend-only change preserves API/save behavior,
owner theme tokens and ownership semantics; no migration or dependency is added.

Commands actually run from `apps/web`:

- `npm test`: 26 passed, zero failures/skips after rerunning outside the sandbox
  so disposable loopback servers could bind. The first sandbox run stalled and
  was interrupted; it is not passing evidence.
- `npm run lint`: passed TypeScript checking.
- `NEXT_TELEMETRY_DISABLED=1 npm run build`: passed. Next warned about the existing
  untracked root lockfile; it was left untouched. Generated `next-env.d.ts` churn
  was reverted.
- `node --test --test-name-pattern='collection opening|add-first workflow|unreadable/network errors|aborted detail|a saved copy edits' tests/inventory.browser.mjs`:
  five passed, zero failures/skips with the installed Chromium path supplied via
  `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. The first browser attempt could not find its
  expected browser revision; using installed Chromium resolved that setup issue.

Browser checks used the production web build on loopback port 63112, a temporary
synthetic-only upstream on loopback port 63113, and existing intercepted domain
fixtures. The new check covers desktop/mobile intake-jump focus, visible keyboard
focus, horizontal overflow and zero ownership writes from navigation. Existing
checks covered intake/photo/storage/search, stale reads/pagination, untrusted long
text and copy editing. These are frontend fixture checks, **not** real owner
session/database integration. No API, remote worker, backup/restore or full browser
suite was rerun. No expected failures apply to the five selected cases.

Full-page empty/populated desktop/mobile captures are local ignored evidence under
`.impeccable/review/collection-opening/`. All four were opened and reviewed. The
independent finish review returned **ship** at visual/code scope, with no required
UI fixes, and requested updating the stale design descriptions. Existing design
hooks reported no deterministic findings. No shipping raster assets were added.
This records local implementation evidence, not deployment or production recovery.

## Workspace navigation correction (2026-11-01)

Supersedes the previous collection-opening composition at the owner's request.
Desktop intake is left, collection right; utilities are in the header. Mobile
uses Menu and a collapsed entry disclosure. The redundant intake jump button is
removed. Expanding/collapsing preserves the mounted draft; only Save copy creates
ownership. Settings visibility is lifted to the workspace while persistence,
preview, conflict and authentication paths remain unchanged. Skip for now is
available inside collection setup. No dependency, migration or API change.

Validation from `apps/web`:

- `npm run lint`: passed.
- `NEXT_TELEMETRY_DISABLED=1 npm run build`: passed, including TypeScript. The
  existing untracked root lockfile still triggers the workspace-root warning;
  it remains untouched. Generated `next-env.d.ts` churn was reverted.
- `npm test`: 26 passed, zero failures/skips (outside the sandbox for loopback).
- With the installed Chromium executable in `PLAYWRIGHT_CHROMIUM_EXECUTABLE`,
  `RELICRAT_SCREENSHOTS` set to the local evidence directory, and the same
  temporary loopback synthetic upstream/web preview described above:
  `node --test --test-name-pattern='collection opening|add-first workflow|unreadable/network errors|aborted detail|a saved copy edits|Records setup previews|skip and cancel|Comics setup previews|setup conflict|setup uncertain|unavailable settings' tests/inventory.browser.mjs`
  passed **11 tests, zero failures/skips**. The earlier eight-case run was
  interrupted after seven passes because its existing Comics screenshot helper
  tried capturing the now-collapsed mobile form; the helper now expands it first.
  An initial lint invocation from the repository root failed because package.json
  lives in apps/web; the correctly scoped command passed.

The focused opening scenario checks the left-hand desktop form, mobile disclosure,
unchanged intake and Appearance drafts across closing/reopening, menu Escape,
outside-click and focus behavior, setup cancellation, the skip link, zero writes
from navigation and overflow at 1440, 768, 390 and 320px. Other selected scenarios
exercise saves, photos/storage/search, copy editing, Records/Comics setup and
settings conflict/uncertain recovery. Synthetic fixture checks do not verify real
owner sessions, PostgreSQL or recovery. No API suite, remote worker checks,
backup/restore or full browser suite ran for this frontend-only correction.

Evidence is `.impeccable/review/workspace-navigation/`: empty/populated captures
at all four sizes, plus mobile expanded-entry and open-menu captures. All ten
were opened and independently reviewed. Reviewer `/root/workspace_finish_reviewer`
returned **ship**, with no material UI findings, and confirmed the two additional
empty tablet/narrow captures. The design record is merged to reflect this current
layout; earlier evidence above remains historical. No deployment is implied.


## Workspace layout on the current feature baseline (2026-11-01)

The original local design checkout preceded CSV imports, grouping, Movies and
barcode lookup. Its layout changes were integrated onto the merged PR59 tree
in an isolated worktree rather than deploying that older checkout. API, schema,
dependencies, owner settings and save payloads are unchanged. Mobile intake stays
mounted when collapsed; the existing scanner disabled path stops its camera.

Validation uses only a disposable worker database/media/network and synthetic
records, never the owner's exports or live inventory:

- `npm test`: 33 passed; `npm run lint`: passed. The worker production build also
  passed compilation/typechecking. Initial lint invocations from the repository
  root failed because package.json is under apps/web; scoped invocations passed.
- Selected `inventory.browser.mjs` navigation, save/error, copy-edit, Album/Comic
  setup and Appearance scenarios: 13 passed after correcting the setup screenshot
  locator to target its named region rather than the class shared with CSV import.
- Selected `barcode.browser.mjs`: five passed, including decoding, explicit save,
  failed-save/type-change draft preservation, reviewed Album lookup and the new
  mobile-collapse camera-stop/draft-preservation check. Its mobile setup now
  explicitly expands intake.
- Both `movies.browser.mjs` scenarios passed, including the 389-row synthetic
  import; its collection locator now follows the approved Saved copies heading.
- All three `groups.browser.mjs` scenarios passed with Movie as the default find
  type, using 1,450 synthetic Comics and 465 Albums. The title-field assertion now
  includes Movie's label. Its earlier run timed out on the older three-type regex.
- WebKit responsive navigation passed using its native all-controls Option-Tab
  traversal. The original ordinary-Tab assertion skipped buttons under this
  runner's WebKit keyboard preference; the Chromium checks keep ordinary Tab.
- Three selected WebKit barcode scenarios also passed: actual decoding, reviewed
  Album lookup/final save, and camera stop with draft preservation on collapse.
- The manual design detector returned `[]`; desktop/mobile captures were inspected.
  Navigation also checked overflow at 1440, 768, 390 and 320px.

Commands and initial/retry logs are retained privately under
`.harness-results/workspace-layout-deployment/`. No API suite or new backup/restore
was run for this frontend-only integration. A subsequent deployment must verify
source/image identity, preserve the existing API/database containers and complete
row/media fingerprints, check Mac/private HTTPS access, and retain prior recovery
resources. This section records verification, not an implicit rollout claim.


## Configured Movie barcode lookup (2026-11-01)

Movie's config selects UPCitemdb through the existing registry and reviewed-fill
UI. Only title is exported/mapped; provider brand is not studio, format/edition
are not inferred, and external images/offers/prices are ignored. Review fills a
draft; only the existing final save creates or edits a physical copy. No schema,
dependency, frontend-runtime or live-network change is included.

Verification:

- `python3 scripts/test-api-remote.py relicrat-worker`: **349 passed**, zero
  failures/skips; 89 existing Starlette/httpx and Alembic deprecation warnings.
  Full downgrade to base and upgrade through 0013_movies passed. The disposable
  Compose snapshot used a checked nonoverlapping internal subnet because the
  worker's automatic address pools are exhausted; that temporary test-only edit
  was restored byte-for-byte and is not part of the change.
- Twenty-seven generated-provider cases cover exact UPC/EAN matching, conflicting
  identifiers, leading zeros, canonical deduplication, malformed/bounded fields,
  safe source links, pinned HTTPS transport, redirect/compression/type/size limits,
  timeouts, no-match versus invalid 404s, concurrency/rate/cooldown, swappable type
  configuration, owner-only access, safe errors and unchanged database row counts.
- The independent worker web-test build/typecheck, lint and all **33 Node tests**
  passed. Each of Chromium and WebKit passed **four selected browser scenarios**:
  Movie scan → automatic lookup → reviewed title → one explicit save, provider
  quota/no-match recovery preserving manual text, the existing Album reviewed-fill
  flow, and mobile collapse stopping the camera while preserving the draft.
- These browser scenarios intercept provider replies with generated fixtures;
  neither tests nor fixtures use owner exports or call a live provider. A separate
  one-request protocol probe from a disposable no-port container matched a publicly
  listed Movie barcode. It retained only a sanitized success/count receipt and
  did not create inventory or fetch artwork. This is not a coverage/availability
  guarantee or a physical-phone test.
- Hashes of every changed API runtime/config file matched the reviewed local
  source. `git diff --check` passed. No production UI styles/components changed.

Private evidence is under `.harness-results/movie-barcodes/`. The first browser
stack launcher stopped before transfer because its local evidence path was
relative to the wrong worktree; it resumed with the exact owned directory and
correct absolute evidence path. The API snapshot log is also retained there.
Only the exact owned test projects, their resources/source and temporary bridge
were removed after verification. Live inventory, owner settings, all recovery
resources and the original design checkout were untouched. No new backup/restore
or live deployment was performed; API rollout and phone use follow merge.
