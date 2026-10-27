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

The photo refresh regression is deliberately marked `xfail(strict=True)` until
the pilot fixes it. `--runxfail` exposes the real failure. A normal run must
report that expected failure, never describe the entire suite as passing.
The companion failed-commit test checks that rollback still removes the file.

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
- This validates the API, not web behavior, backup/restore, or all concurrency
  invariants. The original review's other findings remain open.

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
   Run the full harness there before starting Symphony. Confirm worker sandbox
   compatibility with its isolated Docker engine; don't bypass a rejection.
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
