# Dedicated Technodrome worker

The worker is an Ubuntu 24.04 KVM guest inside a narrowly configured QEMU
container. Its guest has its own kernel, 40 GB sparse disk, and Docker engine.
It receives two vCPUs and 4 GB RAM; the outer container is capped at two CPUs
and 5 GB. The only forwarded service is SSH bound to NAS loopback port 22222.
No NAS application volumes or Docker socket are mounted into the guest.

The NAS account remains a trusted operator: its Docker privileges can control
the VM. This is isolation for development, not protection against a compromised
NAS operator. Guest outbound networking is enabled for package downloads and
authentication; it is not an egress firewall.

## Provision and connect

From the repository on the Mac:

```sh
python3 scripts/provision-worker.py
sh scripts/worker-ssh.sh
```

First boot installs packages and the pinned, checksum-verified Codex 0.165.0
and Symphony 0.0.3 executables. Wait for `cloud-init status` to show `done`.
The Ubuntu base image is checksum-pinned too. If its upstream `current` URL
changes, verify the replacement against Ubuntu's published checksum before
updating the pin; do not remove the checksum check.
Provisioning files live under `/home/bclark/relicrat-worker` on the NAS, and the
guest disk is the dedicated `relicrat-worker_disk` Docker volume. The operator
key is generated on the NAS and stays there; only its public key enters the
guest. No existing Mac or NAS account credentials are copied into the guest.

The NAS rejects SSH TCP forwarding. The connection helper uses two authenticated
sessions: Mac → NAS → guest. The second SSH session uses a binary stdin/stdout
relay inside the existing VM container to reach QEMU's loopback SSH listener.
QEMU then sees its own gateway as the source, so a guest Docker test network
cannot capture replies to the NAS container's address. The relay uses Python's
standard library; Python is explicitly installed in the VM container image.
No new listener, SSH agent forwarding or NAS SSH configuration change is needed.
The same guest identity, known-host file and port alias remain in use. On the
first guest connection its host key is pinned under the dedicated NAS worker
directory; later mismatches must be investigated, not silently accepted.

## Codex login

In the guest terminal:

```sh
codex login --device-auth
codex login status
```

Open the displayed OpenAI link in your Mac browser and enter the one-time code.
If device login is disabled, enable it in ChatGPT security settings (or ask the
workspace administrator for a managed account). Keep the login code and tokens
out of chat, Git, and issue descriptions. Credentials are created on this guest.

## GitHub login

Create a fine-grained personal access token in GitHub settings:

- Resource owner: `bclark`.
- Repository access: only `relicrat`.
- Expiration: 30 days for this initial pilot.
- Initially grant **Contents: read-only** for environment setup and validation.
  An operator can publish the harness using their own GitHub connection without
  expanding the worker's permissions.
- Before starting the agent pilot, replace
  it with a token granting Contents, Issues, and Pull requests read/write for
  this one repository. Do not grant repository administration or Workflows.

In the guest terminal, run:

```sh
relicrat-github-login
git ls-remote https://github.com/bclark/relicrat.git HEAD
```

Paste the token at the hidden terminal prompt, not into chat. The helper verifies
repository read access and saves it at `~/.config/relicrat/github-token` with mode
0600. The Git credential helper returns it only for this repository over HTTPS.
The token is accessible to this worker user, including its coding agent; this
pilot does not provide a separate secrets broker. Repository scope and short
expiration limit its reach. Revoke it in GitHub when the pilot is retired.

## Verification

From the Mac, test the current API snapshot inside the guest's Docker engine:

```sh
python3 scripts/test-api-remote.py relicrat-worker
```

Results use the existing local `.harness-results` logs. The special worker target
uses the two-hop connection helper; ordinary SSH aliases still work unchanged.
The helper programs have focused credential-scope and private-file-permission
checks in `infra/worker/tests/test_credentials.py`, run against installed helpers
on the guest without real credentials or external requests.

Verified on 2026-10-27: cloud-init completed without errors and passed its schema
check; Codex 0.165.0 and Symphony 0.0.3 launched; four credential-helper tests
passed. `python3 scripts/test-api-remote.py relicrat-worker` reported 24 passed,
one expected failure, zero skipped, and a successful migration round trip.
Test resources were removed. The expected failure remains the photo bug reserved
for the pilot. Guest OS updates were applied before authentication. Codex login
and GitHub repository read access have been verified; worker write permissions
have not been validated. Symphony is not running.

## Operation and boundaries

### Sandbox preflight

Codex 0.165.0's Linux sandbox needs `bubblewrap`. Ubuntu 24.04 also requires an
application-specific AppArmor user-namespace allowance for this launcher. The
bootstrap installs the native package and defines `relicrat-codex-bwrap`, attached
only to the root-owned `/usr/bin/bwrap`. The global user-namespace restriction
stays enabled. See [Ubuntu's documented per-application profile approach](https://documentation.ubuntu.com/release-notes/24.04/#unprivileged-user-namespace-restrictions).

On an existing worker, review the profile in the cloud-init template before an
operator installs it at `/etc/apparmor.d/relicrat-codex-bwrap` and loads it with
`sudo apparmor_parser -r /etc/apparmor.d/relicrat-codex-bwrap`. Do not disable
AppArmor globally or change Codex to unrestricted execution to pass this check.

Run from a checkout inside the guest:

```sh
sh scripts/check-worker-sandbox.sh
python3 scripts/check-worker-protocol.py
```

The protocol check first verifies the adjacent `codex-code-mode-host` executable
from the version-matched full Codex package can start. It validates both workflow policy payloads against schemas
generated by the installed Codex binary, then starts an ephemeral thread without
sending a model turn. Codex 0.165.0 uses `granular` approval controls: `false`
automatically rejects requests in that category. The older `reject` object is
not accepted. WORKFLOW.md sets every granular flag to false, preserving the
unattended rejection policy while leaving the workspace-write sandbox unchanged.
Python `yaml` and `jsonschema` are already supplied by the guest's cloud-init
installation; no API application dependencies are added.

This checks direct workspace writes, denial of a direct write outside the
workspace, and access to the guest Docker daemon using Codex's configured
sandbox without launching an agent. Docker access itself grants control of the
guest; these checks do not prevent Docker-mediated guest filesystem access.
The separate VM is the containment boundary for Docker-capable work.

After PR #8 merged and the worker token was updated, the sandbox check and
`git push --dry-run` passed. The scoped AppArmor profile is active; the global
user namespace restriction remains enabled. Initial pilot attempts exposed an
incompatible policy object, a missing Codex companion, and Docker build metadata
writes outside the workspace. The protocol and package corrections above address
the first two failures.

Before starting Symphony, give Docker build metadata its own disposable cache:

```sh
export BUILDX_CONFIG=$(mktemp -d /tmp/relicrat-buildx.XXXXXXXXXX)
# Run the sandboxed harness and Symphony with this environment.
# After Symphony and its child processes stop:
rm -rf -- "$BUILDX_CONFIG"
unset BUILDX_CONFIG
```

The monitored pilot launcher does this per run. `/tmp` is writable under the
existing sandbox; no extra writable roots are needed. Verify the full harness
inside `codex sandbox` with this environment before dispatch, since a Docker
daemon connectivity check alone does not exercise client-side build writes.

- No Symphony service is enabled or started automatically. Installing binaries
  and signing in do not dispatch work or authorize publishing.
- The current WORKFLOW.md clones over HTTPS using the scoped credential helper.
  [Pilot issue #6](https://github.com/bclark/relicrat/issues/6) is the only issue
  authorized for the monitored pilot. Its dispatch label is removed on handoff
  or a blocker.
- Cloud-init configuration changes do not retrofit an initialized guest. Apply
  deliberate updates inside the guest or rebuild only after preserving any
  required work and revoking credentials. Re-provisioning is not a data reset.
- Shut down gracefully from the guest with `sudo shutdown -h now` before
  rebuilding/recreating the outer container. Treat direct container termination
  as a power cut to the VM.
- To start a stopped VM on the NAS, run `docker compose -p relicrat-worker -f
  /home/bclark/relicrat-worker/compose.yaml up -d`. Do not use `down --volumes`
  unless intentionally destroying this worker and its stored credentials.
- A pre-login bootstrap disk may be retained as `pre-login-v1.qcow2` in the
  dedicated volume. It contains synthetic setup state, not user collection data.

Sources:

- [Ubuntu cloud-init/QEMU setup](https://ubuntu.com/docs/public-images/public-images-how-to/use-local-cloud-init-ds/)
- [Codex headless authentication](https://learn.chatgpt.com/docs/auth#login-on-headless-devices)
- [GitHub fine-grained token setup](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

## Worker route regression (2026-10-29)

A disposable browser test allocated a guest Docker subnet matching the NAS VM
container's source network. SSH replies followed that guest bridge instead of
QEMU's gateway; rebooting did not fix the route. Removing only the confirmed
empty test-owned network restored access. Existing trial containers, images,
volumes and owner settings were retained and restarted; 13 synthetic copies,
copy A's two photos, Box B assignment and movement history were visible afterward.

The revised helper was verified while an explicitly owned empty internal test
network recreated the conflicting subnet. SSH remained available, the preview
login returned 200 and unauthenticated inventory returned 401. That exact network
was removed afterward. No guest routing, credentials, access policy or published
ports changed. Host tests exercise binary traffic, stdin half-close, remote EOF,
interactive/command argument construction and retained SSH security options:

```sh
python3 -m unittest discover -s scripts -p test_worker_ssh.py -v
```

The Python package declaration affects future VM-container builds. The existing
container already has Python, so no VM image rebuild or disk replacement was
needed. Private operational evidence remains outside Git.
