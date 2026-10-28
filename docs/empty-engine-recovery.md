# Empty-image-store recovery rehearsal

## Verified scope — 2026-10-28

A disposable engine recovered the authenticated synthetic trial from its actual
encrypted Mac archive with no preloaded images or content blobs. It loaded the
saved API, PostgreSQL and web images, then restored and verified every database
row, migration head, referenced photo and complete media checksum inventory.
The saved web image also passed all 20 Node boundary/security checks.

The input was the existing archive for deployed source
`ed8d0e34931d6370fcc8e8103db0168289dcac40`. Its encrypted-file checksum matched its
private receipt; authenticated decryption succeeded before extraction. All fixed
capsule members and their hashes passed, and the archived source bytes matched
`git archive` of that reviewed commit. No new app images were built or downloaded
for the recovery. Owner environment credentials and the private decryption key
were not transferred to the recovery engine.

This closes the untested image-cache dependency from the initial off-host check.
It is **not** a bare-metal or new-OS installation test: the rehearsal reused the
worker's Linux kernel and installed Docker/containerd/Compose/Python binaries.
Replacement hardware, OS provisioning, off-site archive access, performance at
large collection size and production readiness remain separate requirements.

## Isolation and evidence

The operator created a daemon with a new socket, configuration, data/exec roots,
and an independently started containerd with new root/state/content/snapshot
storage. Both ran in private mount, network and PID namespaces. The rehearsal
engine ID differed from the live engine. Images, containers, volumes and physical
containerd content blobs were empty before import. Its network namespace had no
external route; only a private internal network was later created for the restore.
There were no published ports or live data-volume mounts.

The source recovery helper was extracted from the authenticated capsule without
modification. The operator imported that module and injected the disposable
Docker CLI target into its process-local `DOCKER` value. Its existing `restore`
function and all checksum/row/media verification logic ran unchanged. This
routing override is test-driver configuration, not an application code change.

Before loading images, restore was deliberately attempted. It failed because the
required image was absent, before creating its destination or any container or
volume. That expected failure proves the test was not silently borrowing the
live cache. `docker image load --input images.tar.gz` then imported all three
exact saved IDs; each was inspected and matched before restore continued.

Only the restored database service started. The API image ran the existing
filesystem/database verification helpers; the web image ran `npm test` with no
network. No API/web server was started, no restored session was used, and no
promotion or bridge cutover occurred.

The live trial's container IDs, images, running/start state and volume mounts
were compared before/after and remained unchanged. Its actual private login URL
returned 200 and unauthenticated inventory returned 401 after cleanup.

## Harness corrections that mattered

Initial probes were retained as failures and do not count as a successful
empty-store rehearsal. Three environment issues were corrected before the final
run; the archived source, images and backup bytes were not changed:

1. This distribution's Docker defaults to the system containerd socket. A new
   Docker namespace alone therefore did not supply an independent content store,
   and the host runtime could not see the private mount layout. The passing run
   used an explicit private containerd socket and independently empty storage.
2. Host systemd cannot manage PID-namespace-local process IDs as host IDs. The
   disposable daemon used its own `native.cgroupdriver=cgroupfs` configuration and
   a unique test cgroup parent. Live engine/cgroup configuration stayed unchanged.
3. The control process's private umask made unpacked container root directories
   mode 0700, preventing PostgreSQL's user switch from executing its entrypoint.
   The disposable daemon processes used the normal 0022 umask inside the enclosing
   private 0700 run directory. Backup files, credentials and the live engine's
   permissions were not relaxed.

All stores in the final run were fresh after those corrections. Readiness checks
also verified separate PID/network namespaces and absence of content blobs.
Docker documents [independent daemon configuration and cgroup-driver options](https://docs.docker.com/reference/cli/dockerd/).
Multiple-daemon testing is experimental; these scoped operator settings are not
recommended production deployment changes.

## Cleanup and limits

The successful restore project was stopped and its disposable containers,
network and volumes removed. Both temporary daemons exited; the private PID
namespace was checked for surviving processes. The run-owned cgroup, engine/
containerd data and temporary plaintext/source copies were removed. Earlier
failed test stores and their unique leftover test namespace were separately
cleaned with explicit ownership checks, preserving live resources and earlier
backups. There was no global prune or archive/key deletion.

Private driver logs, authenticated-input evidence, daemon diagnostics and final
receipts remain under the operator checkout's ignored
`.harness-results/empty-engine-rehearsal/`. The encrypted Mac archive and its
working/independent 1Password recovery keys are unchanged. Successful verification
is tied to this tested archive/release, not every future backup or image version.

For a real replacement host, follow [manual off-host recovery](off-host-backup.md):
provide compatible Linux/Docker prerequisites, authenticate and inspect the
capsule, load its saved images, verify exact IDs, and run the matching source's
offline restore. Generate fresh owner configuration and a **new session secret**
before any reviewed promotion. Do not start old captured sessions or expose the
restored development stack publicly.
