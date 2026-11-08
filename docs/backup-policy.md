# Backup policy for v0.1.0

This policy applies to the private single-owner Linux Compose release. Use the
[replacement recovery guide](replacement-recovery.md) for a real restore.
The targets below assume a compatible host, enough staging space and an
operator who can retrieve the archive and recovery key.

| Item | Default |
| --- | --- |
| Capture | Nightly at 02:30 in the operator's local timezone. Take an extra verified backup before a bulk import or upgrade. |
| Verification | Authenticate the encrypted archive, verify exact images and source, and perform an isolated copied restore. Read back the independent off-site copy and verify that it has the same digest. Track capture, copied restore and off-site verification separately. |
| Retention | Keep 14 daily, 8 weekly and 6 monthly verified off-site points. Use the newest verified point for each time bucket and let a point fill multiple buckets. Keep each pre-upgrade point at least 30 days and until two post-upgrade off-site points are verified. |
| Acceptable data loss | Target 24 hours. Measure elapsed time from capture of the newest verified off-site point. At 26 hours the backup is critical. |
| Recovery time | Target four hours from availability of a compatible replacement host, encrypted archive and key. Finish when the owner can sign in, find a recovered copy in its box and open its photo. Record archive retrieval or host procurement time separately when either is required. |
| Recovery rehearsal | Repeat a timed replacement-host drill quarterly and after changes to the backup format or recovery tools. |

Use a destination independent of the app host and keep the decryption key in
separate protected custody. Budget space for the encrypted image, database and
photo payloads, plus staging. Review capacity monthly and after large imports.
Pruning is manual and needs explicit owner approval. Keep the last known-good
verified point even if newer captures fail.

## Alerts

- Alert immediately on authentication or checksum failure or if the app fails to
  restart. The capture and verification runners report those failures directly.
- Start the missed-run alert at **04:00 local** to allow delivery before **05:00**.
  At **26 hours** from capture, escalate the stale point to critical, even
  before the daily deadline if necessary. Missing or invalid evidence requires
  investigation.
- Send one notice per incident state and one recovery notice. Retry unsuccessful
  delivery and keep routine success quiet. An upload or a newer local-only
  archive cannot clear a missed off-site run.

Schedule the watcher at least every five minutes on an always-on host separate
from the backup runner. Run it as a private single-purpose account with read
access to the evidence and a writable private cursor directory:

```sh
python3 scripts/operations.py watch-offsite --config /private/watch.json \
  --output /private/watch-state.json
```

Example private configuration with mode 0600:

```json
{
  "timezone": "America/New_York",
  "offsite_receipt": "/private/evidence/offsite.json",
  "notify_command": ["/private/bin/notify-owner"]
}
```

The notifier reads a JSON line with `check` and `state` on stdin. Configure it
to deliver to the owner and return zero only after the delivery endpoint accepts
the notice. It receives no collection data, backup path or key. Report watcher
process failures through the host's service monitor. Test delivery to the owner
before relying on that installation.

When using `operations.py sync-evidence`, the publisher writes `offsite.json`
only when the verified copied-restore and off-site receipts match on source
and SHA-256. It includes the capture timestamp from the matching restore
receipt. If the publisher stops or loses access, the watcher can still alert
from the last delivered receipt. The older dashboard freshness display is
separate from this watcher.
