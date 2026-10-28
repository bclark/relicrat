# 0002 — Single-owner password and revocable sessions

Status: Accepted for the private synthetic development trial (2026-10-28).

The owner selected one password provisioned through SSH rather than an external
identity provider. The current app needs to protect inventory, history and images
without adding signup, email delivery, roles or an identity-service dependency.

Use standard-library scrypt (N=2^17, r=8, p=1) with a random salt. A separate
random server secret binds PostgreSQL sessions to the current credential
configuration. Only SHA-256 hashes of random 256-bit opaque tokens are stored.
Absolute expiry is 12 hours, and logout revokes server-side state. Password or
secret rotation ends prior access after restart. A serialized PostgreSQL guard
limits failed logins across processes. Migration 0004 adds only auth tables.

Keep the API private and Bearer-only. Next.js translates its HttpOnly/Strict
cookie into the internal Bearer header; browser JSON never receives a token.
Pin the browser origin and require same-origin writes. HTTPS cookies are Secure
and __Host-prefixed; plain HTTP is an explicit loopback-only SSH-preview exception.
No forwarded header is an authority. All protected API requests are authorized
before body parsing. Missing configuration fails closed.

This keeps the existing monolith and adds no runtime dependency. The cost is a
single global login guard (temporary denial of access is possible), manual SSH
credential recovery, and database-backed session checks. There is no MFA or
multi-user authorization. Production ingress, availability/resource budgets,
secret management and off-host recovery remain separate requirements.

See [setup, reset, restore rotation and limitations](../owner-access.md). Password
parameters follow [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
