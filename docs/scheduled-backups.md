# Daily encrypted backup operation

A daily task in the existing operator chat runs the verified off-host procedure
at 03:00 America/New_York. It uses the current deployed release record, not the
current Git branch or an old upgrade snapshot. This is an agent-operated local
schedule, not a NAS service or a guarantee of unattended availability.

The Mac must remain powered on and the desktop app running. The configured
source checkout, SSH access and backup/key directories must remain available.
Normal permission boundaries still apply; an unattended approval failure is a
failed backup, never permission to bypass a boundary.

## Per-run contract

1. Read the private deployment record and confirm the exact configured trial,
   worker engine, Compose configuration, current release and image identities.
   Confirm no public ports and no external writers or running Symphony task.
   Refuse stale/missing state; never fall back to another project or old source.
2. Confirm private directory/key permissions and at least 5 GiB free on both
   computers, allowing more if the current backup size requires it. If storage
   is tight, stop and report rather than deleting previous backups.
3. Use a new private UTC-stamped run directory. Invoke the deployed release's
   existing `backup.py create` with the current owner settings only in its
   subprocess environment. This must be a **fresh capture**, not a copy of an
   earlier rollout backup. Brief web/API downtime is authorized for this daily
   single-writer capture. Verify the original app restarts on success or failure.
4. Package the exact current API/db/web images and matching reviewed Git source
   with the captured database/media and capsule checksums. Exclude owner config,
   SSH/provider credentials and private decryption keys. Never deploy code or
   change ownership data, passwords, network access or migrations during a run.
5. Stream through the existing SSH helper into a new encrypted Mac archive using
   the established OpenSSL CMS recipient certificate. Keep incomplete outputs
   clearly partial; require successful transfer and encryption before publishing.
6. Authenticate decryption of the actual copied artifact into a private temporary
   directory before extraction. Verify all fixed capsule members, hashes, source
   commit and saved image identities, including OCI index/manifest digests where
   applicable. Reject unexpected members, traversal, links and special files.
7. Upload only that verified copied backup into a new private worker location.
   Use the existing restore verifier with fresh volumes, no ports and no API/web
   startup. Compare every row, migration head and media checksum. A copy alone
   does not count as a verified backup.
8. Save a private durable receipt identifying the data snapshot, encrypted
   archive/hash, release/image IDs and restore verification. Update the latest
   pointer only after every check succeeds. Keep all earlier encrypted archives.
9. Remove only this run's successful disposable restore resources and temporary
   plaintext/staging, using exact run-owned paths and the restore receipt's
   project/config. Preserve earlier backups and retained manual restores. Keep
   failed restore resources offline for inspection; never mark a failed run as
   verified. No global prune, inferred targets or broad wildcard deletion.

One successful scheduled run per local calendar day is sufficient; do not repeat
a completed run because the chat wakes twice. Routine success stays quiet. Report
backup/verification/restart failures, missing permissions, capacity problems or
configuration changes requiring owner attention. Never print secrets or images.

## Recovery-key custody

The existing recipient private key decrypts every encrypted recovery archive;
it is separate from the application owner password. Its primary copy remains in
a private Mac configuration directory. A second copy on the same Mac is only a
staging copy and must not be reported as independent protection.

The owner must choose a separate protected destination, such as a password-manager
secure file or encrypted removable drive. Do not send a private key through chat,
email, a repository, or an unapproved provider. If no suitable connected tool
exists, prepare a private local import kit and guide the owner through the final
transfer. Keep custody marked pending until the owner confirms independent storage
and, ideally, verifies that the stored copy can decrypt a disposable test archive.
Do not delete or rotate the working key as part of scheduling.

Daily scheduling does not provide off-site storage, automatic archive retention,
independent key custody or a full replacement-host rehearsal. These remain
distinct recovery requirements; a separate [empty-store image/data recovery
rehearsal](empty-engine-recovery.md) has passed for the tested archive/release.
Current use remains synthetic-only.

See [manual encrypted recovery](off-host-backup.md) for capsule format and recovery
steps, and the [official local scheduling requirements](https://learn.chatgpt.com/docs/automations?surface=app).

## Verified key-copy completion — 2026-10-28

After the owner unlocked 1Password directly, the prepared recovery ZIP was saved
as **RelicRat backup recovery key** in the **Personal** vault. Upload completion
was observed. A downloaded vault copy matched the original bytes and its key
decrypted a disposable authenticated test envelope. Temporary import/download
copies were removed; the working Mac key and vault Document were preserved.
Routine backup runs need no vault access or repeated custody confirmation.
