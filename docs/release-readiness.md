# First self-hosted release

The finish line is a private, single-owner installation that a collector can
operate from a desktop and a phone, use with outbound internet blocked, and
recover on a replacement host from an independently stored encrypted backup.

## Post-v0.1.0 release confidence · November 19, 2026

[PR #145](https://github.com/bclark/relicrat/pull/145) adds a distinct upgrade
regression and refreshes the [roadmap](roadmap.md). Application candidate
`93c4f4dd566990a1bb1b01b0026074418839d06c` was exercised on an independently
initialized Ubuntu 24.04 VM, Docker 29.1.3 and Compose 2.40.3. All records and
photos were synthetic. The live NAS application and its backups were not used.

| Gate | Result |
| --- | --- |
| Clean current install | Empty engine and new persistent volumes; desktop Chromium and Pixel 7 profiles each added a copy/photo, created a box, moved and found the copy, imported a one-copy Games CSV, and inspected the result. The four-test Linux journey passed. |
| Physical Android | Chrome 158 on Android model SM-S938U, through a USB loopback tunnel, added a copy/photo, created a box, moved and found that exact copy. The phone import shortcut produced a one-copy CSV preview, imported explicitly and opened the saved game. |
| Published baseline | Installed immutable v0.1.0 `373873e58e495e09c7e064134909b66266c9692e` into separately named empty volumes. Its original desktop and Pixel 7 browser tests passed; physical Android added a third photographed, located copy. |
| Populated upgrade | Took a pre-upgrade backup, stopped the baseline writers and migrated those same volumes from `0019_agent_credential` to `0021_game_import_recipes`. SHA-256 fingerprints of all populated pre-existing domain tables matched. The three additive Games fields are excluded; existing inventory fields are not. |
| Browse after upgrade | Desktop and Pixel 7 reopened the original copies and verified exact photo bytes. Physical Android found its original UUID, box and exact photo bytes after the upgrade. The old-fixture verification intentionally skips Games tests because v0.1.0 predates that feature. |
| Offline/private runtime | Internal Compose networks, no published service ports, `unless-stopped` policies and denied outbound API connection. Browser checks reject requests outside the loopback install. Build/download access occurred before runtime checks. |
| Repeatable CI | Separate clean Ubuntu jobs exercise fresh install and populated v0.1.0 upgrade, new features after migration, pre-recreation backups and persistence. API/migrations, web build/tests and CSV/MCP regressions also passed. [PR checks](https://github.com/bclark/relicrat/pull/145/checks). |

No application defect was found in these journeys. This batch fixes the missing
upgrade coverage and makes fingerprint SQL errors fail the check immediately.
The physical tests used browser automation; human touch/lighting, physical
barcode-camera scans, iOS and public hosting are outside this evidence. No live
deployment or new disaster-recovery drill is claimed. The v0.1.0 recovery and
backup-policy evidence below remains dated historical evidence.

## Evidence for the Linux Compose candidate

**Tested November 8, 2026.** Candidate
[`efc9f1c`](https://github.com/bclark/relicrat/commit/efc9f1c5de790d47db94334ed6f6d90e7a2b736b)
on Ubuntu 24.04 with Docker Engine 29.1.3 and Compose v2. The rehearsal used
two disposable VMs and synthetic inventory.

| Gate | Verified result |
| --- | --- |
| Clean install and offline use | Started with an empty Docker engine and installed baseline `6567453` using the candidate's Linux Compose and owner setup. With outbound traffic blocked after building the images, desktop Chromium and an emulated Pixel 7 each added a copy with a photo, put it in a box, and found it again. |
| Pre-upgrade backup and migration | Authenticated the encrypted pre-upgrade backup on the operator's Mac. Upgraded the populated install from migration `0018_location_audits` to `0019_agent_credential`. Both browser profiles found the saved copies. Row fingerprints for copies, boxes, photos and movements and the media checksums matched across the upgrade. |
| Independent replacement restore | Authenticated a fresh candidate archive on the Mac and checked the source hash and exact saved images. Stopped the source VM before restoring on a separately initialized, offline Ubuntu VM. The restore matched all captured database rows, migration state and media, including two copies, two boxes, two photos and two movement events. Fresh owner sign-in and Docker restart behavior passed. |
| Browse the recovered collection | Desktop Chromium and the emulated Pixel 7 found both saved copies and verified the photo bytes. Chrome on a physical Android phone signed in over a USB loopback tunnel, found the phone fixture in its box, and decoded the exact saved photo. |

The Mac held the encrypted archive independently of both VMs. This run
covered a synthetic dataset on Linux/amd64 and private loopback access. The
separate replacement-host rehearsal describes recovery from a Drive copy. The
phone check used browser automation over USB. Touch gestures and iOS were
outside this run.

## v0.1.0 release scope

The initial support target is private, single-owner Ubuntu 24.04 on amd64 with
Docker Engine 29.1.3 and Compose v2. After the release PR merges, compare the
release commit's application and recovery files to the tested candidate, run the
Linux install smoke test on the exact release SHA, then tag that commit
`v0.1.0`. Publish the tag and full SHA together.

The [backup policy](backup-policy.md) defines retention, freshness and recovery
targets, and the independent missed-run watcher.

## Backup policy launch checks

- **Timed restore · November 8, 2026.** A 508 MiB archive with over 2,300 copies
  and eight media files recovered in **55.4 seconds** on a fresh Ubuntu VM,
  including archive authentication, transfer to the VM, row and media
  verification, Docker restart, and signed-in access to a recovered copy, its
  box and photo. The timer started with the host, key and archive available.
  The Mac archive matched a previously verified Drive readback by SHA-256.
  The archived release predates the candidate above. The candidate's exact
  release recovery is covered by the synthetic rehearsal.
- **Missed-run drill · November 8, 2026.** An independent Linux process used
  synthetic receipts while the publisher was absent. The test exercised the
  local deadline, stale escalation, failed delivery retry, duplicate suppression,
  and recovery. The CLI delivered the critical and recovery notices to an
  isolated receiver. Operators must configure and test their own notification
  destination before relying on the watchdog.

[Linux Compose install](linux-compose-install.md) ·
[Replacement recovery](replacement-recovery.md)
