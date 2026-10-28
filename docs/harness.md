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
