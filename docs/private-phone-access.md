# Private phone access on the NAS

This optional access path keeps the isolated inventory engine, existing Mac
loopback preview and owner password. The NAS runs a dedicated Tailscale userspace
node and a loopback-only HTTPS adapter. Tailscale Serve terminates HTTPS for
connected tailnet devices; this setup does not enable Funnel.

```text
Phone on the owner's tailnet
  → Tailscale Serve HTTPS on a dedicated RelicRat node
  → NAS 127.0.0.1 adapter
  → existing authenticated worker SSH transport
  → separate web frontend, fixed HTTPS origin, internal Docker network
  → existing inventory API
```

## Boundaries

The phone frontend uses the exact same verified web image as the Mac frontend,
but has its own fixed HTTPS origin and `__Host-relicrat_session` cookie. It has
no database credentials, data/media mounts or published ports. The original
frontend and `relicrat_loopback_session` remain unchanged. Sign in on the phone
with the existing owner password; Tailscale membership alone is not app sign-in.

The adapter binds only to NAS loopback, rejects foreign/duplicate Host and Origin
headers, bounds request framing/body size, and relays only the HTTPS owner cookie.
It discards client Authorization, Forwarded, X-Forwarded-* and unrelated cookies.
It supplies the pinned HTTPS scheme/host to Next behind the TLS terminator; the
application's existing fixed-origin and CSRF checks still apply. Responses must
retain Secure, HttpOnly, SameSite=Strict and host-only owner-cookie attributes.
No collection URLs, credentials or cookies are logged. See
[`private-https-bridge.py`](../scripts/private-https-bridge.py).

The dedicated Tailscale container uses userspace networking, no TUN device, no
added capabilities, no privilege, and no host DNS, exit-node or subnet routing.
Host networking lets Serve reach the NAS loopback adapter; it does not make the
NAS's ordinary services listeners on the node's userspace Tailscale address.
Only explicitly configured Serve handlers receive app traffic. Keep Funnel off.
The NAS's other containers, reverse proxies and applications are not reconfigured.

## Operator setup

These are reviewed building blocks, not a one-command installation or permission
to guess a project, image, key path, network, certificate name or state directory.
Use private deployment receipts and refuse mismatches before activating access.

1. Verify the deployed source/image IDs, sole API writer, running db/API/web,
   internal network, zero app port mappings, stopped Symphony and fresh recovery
   evidence. Use the approved operator workflow to deploy the merged app first.
2. Create a private NAS directory and Tailscale state directory (0700), owned by
   the actual unprivileged NAS UID/GID. Pin the official image by digest in
   [the userspace-node template](../infra/docker/compose.phone-tailscale.yaml).
   Running as the directory owner avoids granting root DAC capabilities. The
   runtime socket lives in container tmpfs, not a host socket mount.
3. Authenticate the node directly using its owner login URL; do not put an auth
   key in Compose, Git or chat. Run `tailscale up` with `--accept-dns=false` and
   `--accept-routes=false`. Verify Running status and the assigned DNS name.
   Protect provider state and TLS material; exclude them from app recovery capsules.
4. On the worker, start [the second frontend](../infra/docker/compose.phone.yaml)
   with the exact current web image, external reference to the existing internal
   app network, the assigned `https://…ts.net` origin, and loopback HTTP disabled.
   This frontend accesses the existing API; it has no direct database writer.
5. On the NAS, install `private-https-bridge.py` and `private-preview.py` together in a private source directory. The adapter reads an owner-only local transport JSON file with `ssh_args`
   and `engine_name`. Machine aliases, usernames, key/known-host paths and any
   relay/container/port settings belong there or in private SSH configuration,
   never in the public source. An example uses `ssh_args: ["example-worker-alias"]`
   and `engine_name: "example-engine"`; replace these with your private values.
   SSH batch mode, strict host-key checking and no agent forwarding are enforced. It refuses a wrong
   engine, stopped/mapped frontend or mismatched web origin before listening.
6. Install [the user service](../infra/systemd/relicrat-phone-bridge.service).
   Its private `bridge.env` defines `RELICRAT_PHONE_ORIGIN`,
   `RELICRAT_PHONE_CONTAINER`, `RELICRAT_PHONE_BRIDGE_PORT` and
   `RELICRAT_PHONE_TRANSPORT_CONFIG` (the absolute path to that private JSON file). Check the existing
   user manager and lingering configuration before relying on startup. Keep
   service logs free of credentials and collection URLs.
7. Point a private **Serve** HTTPS handler at that exact NAS loopback port. Verify
   its hostname, backend, HTTPS setting and empty/false AllowFunnel configuration. Tailscale HTTPS
   certificates record device DNS names in public certificate-transparency logs;
   obtain the owner's choice before issuance when that disclosure is a concern.
   Confirm TLS with normal certificate validation and guest/login boundaries
   through the actual private endpoint. Owner testing on a connected phone is
   still required to verify physical camera focus, lighting and permissions.

Use the image-only update procedure for future releases, updating the optional
phone frontend to the same verified web image and recording its source/image in
private deployment state. Preserve the origin, cookie boundary and NAS access
configuration unless an explicit access change is requested. The helper source
has separate provenance from the app image; record both revisions.

The current offline backup stops the sole API writer. That also blocks mutations
through the phone frontend, which has no direct database connection. Neither
frontend may bypass maintenance by connecting to the database. Restores remain
offline; access services are not a reason to start or promote a recovery copy.
NAS phone access remains optional recovery configuration; it does not replace
verified database/media/image/source recovery or protect provider credentials.

## Verification

Run `python3 -m unittest discover -s scripts -p 'test_private*py' -v` for the
HTTP adapter's framing, authority, trusted-header, cookie, error and SSH-preview
regressions. Separately test real HTTPS-origin sign-in and logout against a
fresh disposable owner/database: Secure host-only cookies, foreign Host/Origin
rejection, refusal of Mac cookies, token revocation, normal API reads and scanner
rendering. Never use real owner credentials or inventory as test fixtures.

Operational activation must additionally verify exact services/images, private
permissions, Tailscale persistence, certificate validation, private Serve with
Funnel disabled, unchanged Mac access, and absence of application port mappings.
Actual addresses, IDs, receipts, keys, login links and collection evidence belong
in ignored private operator records, never a public issue or PR.

Sources: [Tailscale container parameters](https://tailscale.com/docs/features/containers/docker/docker-params),
[userspace networking](https://tailscale.com/docs/concepts/userspace-networking),
[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).
