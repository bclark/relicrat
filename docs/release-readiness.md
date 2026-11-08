# First self-hosted release

The finish line is a private, single-owner installation that a collector can
operate from a desktop and a phone, use with outbound internet blocked, and
recover on a replacement host from an independently stored encrypted backup.

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

## Release decisions still open

- Agree on backup retention, maximum acceptable data loss, recovery time, and
  how a failed backup reaches the operator before expanding the trial.
- Pick the public release pin and publish its support scope. The evidence above
  applies to the named candidate.
- Track portable data export and shareable themes as separate epics. Native
  clients and immersive browsing can build on the API after the single-owner
  web release.

[Linux Compose install](linux-compose-install.md) ·
[Replacement recovery](replacement-recovery.md)
