# Developer scripts

- `sh scripts/test-api.sh`: disposable PostgreSQL 17 API tests and migration round trip on a Docker host.
- `python3 scripts/test-api-remote.py technodrome [pytest arguments...]`: transfer the current API snapshot over SSH, run those checks, and retain results locally. Requires Python 3.11+.
- `python3 scripts/provision-worker.py`: provision the dedicated KVM worker on Technodrome.
- `sh scripts/worker-ssh.sh`: open an interactive guest session through the NAS.
- `python3 scripts/test-api-remote.py relicrat-worker`: run the API suite using the guest's own Docker engine.
- `sh scripts/check-worker-sandbox.sh`: inside the guest, verify workspace-write behavior and guest Docker access without starting an agent.

See [the harness guide](../docs/harness.md) for isolation, evidence, cleanup, and the Symphony pilot.
