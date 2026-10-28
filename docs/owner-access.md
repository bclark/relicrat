# Single-owner access and private setup

RelicRat now has one owner password, provisioned by a trusted operator. There is
no signup, username, email reset, external identity provider, MFA or shared-user
permission model. Keep this development trial synthetic. Authentication does not
establish hardened hosting or off-host recovery.

## Create private configuration

Run the setup command in an interactive terminal on the machine that will keep
the credentials. Python's standard library supplies scrypt; no API service or
extra package is needed. Never pass the password in a command argument, chat or
tracked file. The prompt does not echo it.

For the NAS worker, open an interactive shell from the configured Mac:

```sh
sh scripts/worker-ssh.sh
# In the worker shell, change to the reviewed source checkout first.
python3 scripts/configure-owner.py --origin http://127.0.0.1:56742 --allow-loopback-http
```

The origin is the exact address in the browser, including its port. This example
matches the current SSH-only trial; its existing Compose file must be deliberately
updated after merge, with the same data volumes and credentials passed only to
the appropriate services. Running setup alone does not upgrade that trial.
Do not substitute a test project's Compose file or run `down --volumes`.

Setup requires matching 15–256 character passwords and creates a new `.env.owner`
with mode 0600. It refuses to overwrite a file. The file contains a salted scrypt
hash, random session secret, exact browser origin and explicit HTTP exception.
The plaintext password is never written. Preserve this file privately, outside
Git and backup bundles; do not print `docker compose config` with real settings.
All committed credentials in `infra/docker/owner-test.env` are public synthetic
fixtures and must never be used for a deployment.

For a fresh local development stack only:

```sh
cp .env.example .env
python3 scripts/configure-owner.py --origin http://127.0.0.1:3000 --allow-loopback-http
docker compose --env-file .env --env-file .env.owner up -d db
docker compose --env-file .env --env-file .env.owner run --rm api alembic upgrade head
docker compose --env-file .env --env-file .env.owner up --build
```

Pass both files on every root Compose command. Compose requires owner settings
even for database commands. The API gets the password hash/session secret; the
web gets only origin/network settings. Root Compose publishes only the web on
127.0.0.1; API and PostgreSQL have no host ports. Existing volume names must be
preserved when upgrading an established stack. Take a verified offline backup
with its matching source/images before migration 0004.

## Browser and API contract

Guests go to `/login`. Successful login sets an opaque HttpOnly, SameSite=Strict,
host-only cookie for 12 hours. HTTPS uses `__Host-relicrat_session` with Secure;
explicit loopback HTTP uses `relicrat_loopback_session`. Cookies do not isolate
ports on the same host: keep unrelated localhost apps trusted and use a separate
browser profile for the trial. HTTPS requires an actual trusted TLS ingress;
setting the environment variable alone does not provide TLS. Public/LAN/tailnet
ingress is not part of this change.

The web pins the actual Host/protocol to `RELICRAT_WEB_ORIGIN`, requires matching
Origin for writes, and ignores forwarded host/protocol headers. The server
translates only the owner cookie into a Bearer header. Tokens never enter browser
JSON or localStorage. Anonymous inventory, catalog, history, storage, upload and
photo downloads are denied. Static app assets contain no collection data.
Missing/invalid owner settings or database errors fail closed.

The internal API accepts only `Authorization: Bearer TOKEN`; cookies and query
parameters are not authentication. POST `/api/v1/auth/login` takes JSON
`{"password":"..."}` (2048 actual bytes maximum), returning token, expiry and
max_age to its trusted web caller. GET `/api/v1/auth/session` checks the session;
POST `/api/v1/auth/logout` revokes it. Only GET `/health` and login are anonymous;
OpenAPI/docs routes are disabled. Validation errors never echo login input.
The API port must stay private; do not put tokens in shell history.

Five failed password checks within 15 minutes block further logins for 15 minutes
(429 with Retry-After). The guard is global and serialized in PostgreSQL; it does
not trust client IP headers. An attacker who can reach login could deny the owner
access temporarily. This is a private single-owner boundary, not an internet-scale
resource budget. There is no automatic password or write retry.

Sign out revokes the database session before clearing the cookie. A failed
revocation leaves the cookie and displays an error for retry. Replaying the old
cookie then fails. Expired sessions redirect to login on the next protected
request; unsaved page-local drafts can be lost. A page already open can retain
rendered information, and an already authorized in-flight operation may finish.
Sign out is not remote erasure of previously viewed content.

## Reset, revoke and restore

Generate a new private file using `--output .env.owner.next`, then review the
origin and replace the active configuration through the same private operator
workflow. Recreate/restart the API with the new values and the web if its origin
changed. Changing either the password hash or session secret invalidates all old
sessions once all API processes use the new configuration. Password reset is
SSH-only; losing SSH access requires infrastructure recovery.

Migration 0004 adds session and login-guard tables, without changing collection
rows. Upgrade/downgrade are tested on disposable PostgreSQL data. Downgrade drops
auth state and ends sessions; old unauthenticated code must remain offline.
Never downgrade to expose an unprotected collection.

Backups contain session hashes and throttle state, not the environment password
hash/session secret. Restores remain stopped and have no owner credentials.
Before promoting any restore, generate a **fresh session secret** (the setup
command does this) and configure it with the intended owner password/origin.
Reusing the original secret and password hash can make a pre-backup session valid
again, including one revoked after capture. Do not promote a restore until this
rotation and the normal recovery checks are complete.

`scripts/private-preview.py --project EXACT_PROJECT --port 56742` runs on the Mac
and relays the private synthetic web app through the existing two-hop SSH helper.
It binds only 127.0.0.1, forwards only the owner cookie, and does not alter NAS
ports or SSH forwarding. Use the exact reviewed running project's name. It is a
limited trusted-operator preview helper, not a hardened public HTTP server.
Do not replace the existing preview bridge until the reviewed app is upgraded
and owner setup is complete.

The password parameters follow [OWASP's scrypt guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
(N=2^17, r=8, p=1). Cookie and revocation choices follow
[OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
These are implementation choices, not a security certification.
