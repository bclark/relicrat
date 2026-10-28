# Developer scripts

- `sh scripts/test-backup-restore.sh [--missing-media|--corrupt-media]`: synthetic recovery on the dedicated guest; damage modes must fail. See the harness guide for evidence and destructive cleanup.
- `sh scripts/test-api.sh`: disposable PostgreSQL 17 API tests and migration round trip on a Docker host.
- `python3 scripts/test-api-remote.py technodrome [pytest arguments...]`: transfer the current API snapshot over SSH, run those checks, and retain results locally. Requires Python 3.11+.
- `python3 scripts/provision-worker.py`: provision the dedicated KVM worker on Technodrome.
- `sh scripts/worker-ssh.sh`: open an interactive guest session through the NAS.
- `python3 scripts/test-api-remote.py relicrat-worker`: run the API suite using the guest's own Docker engine.
- `sh scripts/check-worker-sandbox.sh`: inside the guest, verify workspace-write behavior and guest Docker access without starting an agent.
- `python3 scripts/check-worker-protocol.py`: inside the guest, validate workflow policy schemas and start an ephemeral Codex thread without sending a model turn.

See [the harness guide](../docs/harness.md) for isolation, evidence, cleanup, and the Symphony pilot.
