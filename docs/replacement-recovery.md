# Recovering RelicRat on a replacement environment

This is an owner recovery guide, separate from the disposable rehearsal. Keep
using the working app while preparing recovery elsewhere. A verification restore
is not permission to promote it or remove the original inventory.

## What you need

- A verified encrypted recovery archive and its verification receipt. The Mac
  backup folder has the latest pointer; Google Drive has the independent encrypted
  copy in numbered parts with its checksum manifest. They may be different points.
- The existing recovery key and recipient certificate. The working key is on the
  Mac; the independent secure Document is in the owner's password manager. This
  key is different from the inventory sign-in password.
- A compatible fresh Linux/amd64 Docker host, Compose, Python 3.11+ and OpenSSL
  with authenticated CMS AES-256-GCM support. The rehearsal used a new Ubuntu VM.
  Match saved OCI identities; configure a compatible image store on the **new**
  host before loading images. Never change the live engine to do a test.

The archive contains database/media, exact API/database/web images and matching
public source. It deliberately excludes owner settings, SSH keys, provider
credentials and private decryption keys. These access settings are recreated
separately; old captured sessions must not become the restored login setup.

## Recovery sequence

1. **Choose the recovery point.** Read the verified receipt's date, source release,
   checksum and scope. A NAS capture alone has not passed copied restore. A recent
   Mac receipt does not prove the same archive was copied to Drive.
2. **Obtain the encrypted bytes.** For Drive parts, download every numbered part
   and manifest, verify/rejoin them, and match the complete archive SHA256 to the
   trusted receipt. Keep the key separate from cloud storage. Preserve originals.
3. **Authenticate on a trusted Mac.** Use `scripts/recovery-capsule.py` with the
   archive, certificate/key, expected archive SHA256, reviewed source commit/hash
   and a new private destination. Authentication must finish before extraction.
   A checksum/decryption/member/image/source failure stops recovery; do not use a
   partial output or modify the expected hash to make it pass. The private key
   does not need to be transferred to the NAS.
4. **Restore offline on the new host.** Transfer only the verified capsule to a
   private directory. Load its saved images and inspect their exact IDs. Use the
   matching archived source's `scripts/backup.py restore` with a new destination.
   It creates fresh volumes and compares every row, migration and media checksum.
   It starts only the database and verification helpers. Keep any failure private
   and offline; preserve its receipt and the original encrypted archive.
5. **Prepare access separately.** After offline verification, create a new owner
   password hash and session secret with the matching source's owner setup tool.
   Recreate private Compose/HTTPS/SSH access deliberately. Do not use captured
   sessions, expose development services publicly, or migrate the only recovery
   copy as an experiment. Missing optional catalog providers need not block manual
   inventory access.
6. **Review before promotion.** Verify sign-in, blocked guest access, expected
   images, persistent volumes, storage and media, plus the private ingress. Retain
   the original app and recovery artifacts until the owner explicitly approves
   the replacement. Promotion, DNS/access changes and live credential changes are
   separate actions.

The detailed capsule and offline-restore commands are in
[off-host backup](off-host-backup.md) and [backup/restore](backup-restore.md).
Actual private locations, receipts and tested operator commands are recorded in
the operator runbook; nothing in this public guide embeds the owner's addresses,
passwords, keys or collection contents.

## What the rehearsal established

The tested replacement VM had a fresh OS disk and kernel boot, an independently
empty image/container/volume store and no external default route before restore.
Missing images were deliberately rejected. Exact saved images were loaded;
rows/migration/media matched. A private app test used fresh temporary owner
configuration and returned login 200, guest inventory 401 and signed-in inventory
200. No live data volume was mounted and no app port was published.

The tested restart policy preserved an intentional stop across a daemon restart
while running services recovered. All disposable restored resources, the VM disk
and its temporary key were removed after success. This is not a physical
replacement-hardware test or proof that every future archive will restore.

For another **disposable rehearsal**, use `scripts/rehearse-recovery.py` only with
an explicitly identified empty offline engine. It cleans up its restored volumes
on success. For an actual recovery to retain, use the offline restore command
and retain its exact receipt instead.
