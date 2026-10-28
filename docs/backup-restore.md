# Offline backup and verified restore

This is an initial **trusted-operator, synthetic-only workflow on the dedicated
`relicrat-worker` guest**. It backs up a running single-writer db/api[/web] Compose
project. It is not production disaster recovery. Authentication, encrypted/off-host
storage, scheduling, retention and recovery across application versions remain open.

## Before capture

- Use synthetic data only. Run one operator workflow against the app at a time.
- Confirm there are no external SQL clients, jobs, imports, media editors or other
  writers. The command stops the project's running web/API containers, but cannot
  fence external writers. Its before/after fingerprint is an additional check,
  not a replacement for this offline boundary.
- Use the actual trusted Compose file and explicit project name. API must point
  to that project's `db` service. PostgreSQL data and MEDIA_ROOT must use named
  volumes. Stale Compose configurations or API image tags that differ from the
  running containers are refused before capture. Bind/tmpfs data storage and additional services are refused.
- Docker access is privileged. Run only on the isolated worker's local socket;
  the engine-name check is an operational guard, not authentication.
- Allow downtime and enough free disk for the database dump, media tar and restore.
  Copy backup directories only after capture completes. Do not edit bundles while
  restoring or run concurrent operations on the same destination.

## Capture

On the worker, from the matching source checkout:

```sh
python3 scripts/backup.py create \
  --compose /absolute/path/to/compose.yaml \
  --project YOUR_EXISTING_PROJECT \
  --offline-confirmed \
  /absolute/private/backups/NEW_BACKUP_DIRECTORY
```

The parent directory must exist; the new backup directory must not. Existing
backups are never overwritten. The command identifies actual running API/database
image IDs, takes a per-database advisory capture lock, and stops only web/API
containers that were running. No API server runs during capture. A one-off API
helper reads the database/media, while PostgreSQL's native custom-format pg_dump
captures the database and a Python tar captures the entire media volume.

The state file fingerprints every row in every public table (including timestamps,
UUIDs, ownership, Alembic revision and retained history), hashes every regular media
file, and verifies each media row's storage key/size/checksum. The source must be at
the API image's migration head. Symlinks and special media files are refused.
The same state is checked again after capture to detect changed data.

The new directory is mode 0700, files 0600 under the command's umask. It contains:

- `database.dump`: PostgreSQL custom-format archive, without cluster roles.
- `media.tar`: media files and directories, including unreferenced regular files.
- `state.json`: row fingerprints, migration revision and media hashes.
- `manifest.json`: format version, UTC capture time, exact image IDs and SHA256
  for the other three files. No Compose environment or credentials are recorded.

Success removes the INCOMPLETE marker. Ordinary failures and HUP/INT/TERM attempt
to restart the original running app containers in `finally`; incomplete artifacts
remain for inspection and cannot be restored. A restart failure makes the command
fail even if capture completed. After an interruption, inspect the exit status,
marker and original app status. SIGKILL, power loss or Docker failure cannot
promise restart or durable capture; restart the original app explicitly if needed.
The command does not claim fsync/power-loss durability or an online snapshot.

## Restore into a separate offline stack

Use only a completed bundle you trust. Checksums detect accidental damage; they
are not signatures. A PostgreSQL restore can execute SQL from its archive, and the
manifest names executable container images. This is **not an untrusted backup
importer**. Preserve private directory permissions and do not restore concurrently
with edits to the bundle.

```sh
python3 scripts/backup.py restore \
  /absolute/private/backups/COMPLETED_BACKUP_DIRECTORY \
  /absolute/private/restores/NEW_RESTORE_DIRECTORY
```

The restore directory must not exist. Both exact image IDs recorded in the backup
must already exist in the worker Docker engine; the command never pulls a tag.
Keep the matching application source and separately preserve both images using
`docker image save` if the backup must survive image-cache loss. To recover after
an engine rebuild, load those trusted saved images first. The bundle alone is
insufficient after image loss. This workflow does not migrate backups to newer code.

Restore validates required regular files and all checksums before creating any
resource. It generates an unpredictable new project name, fresh PostgreSQL/media
volumes and private configuration with a new restore-only database password. It
never accepts an existing restore project or an in-place target. There are no
published ports and its Docker network is internal. PostgreSQL restores in one
transaction with exit-on-error; all media tar members are checked before extraction.
Traversal, duplicate/ambiguous names, symlinks, hardlinks and device entries are
refused. Extraction also uses Python's data filter inside a no-network helper.

A fresh helper verifies all row fingerprints, migration head, referenced photo
integrity and the complete media file inventory against `state.json`. Only then
is `restore.json` marked `verified`. **Neither the API nor web server starts.**
Original/source data is never modified by restore. Failure leaves the fresh restore
project offline and marked incomplete for inspection; do not promote it.

The restore directory contains `compose.json` and `restore.json`; both are private.
The receipt records its project name and config path. Inspect it using:

```sh
docker compose -p PROJECT_FROM_RECEIPT -f /absolute/restore/compose.json ps -a
```

Promotion to a running app, account/auth settings and changing the preview bridge
are a separate operator decision after reviewing recovery. There is no automatic
cutover. Keep verified restore resources until inspected. To discard a disposable
restore, use **only its receipt's exact project/config** with `down --volumes`;
that irreversibly deletes that restore's DB/media. Never use global Docker prune.

## Verification and limits

```sh
python3 -m unittest discover -s scripts -p test_backup.py -v
# Dedicated worker only; creates and destroys its own synthetic projects:
python3 scripts/test-operator-backup.py
```

The integration invokes these actual commands. It verifies app restart on failed
and successful capture, refusal to overwrite an existing backup, private directory
permissions, and restoration after deleting the source DB/media. It reuses the
independent existing recovery fixture verifier to compare every seeded row/schema,
copy UUID, two reconciliations, two retained movements, nested storage and exact
API-downloaded PNG bytes. Separate checks reject a damaged dump checksum, missing
media, corrupt media (even with updated archive checksums), unsafe tar paths, and altered expected row fingerprints. An unreferenced
hard-linked regular media file is retained as independent archive bytes.
All test projects are removed; the user's trial is not a test target.

No schema migration, runtime dependency, backup HTTP endpoint or UI is added.
Tests cover small fixtures, not large inventories or disk exhaustion. The SQL row
fingerprint sorts each table on the server; capacity and downtime need measurement
before larger use. Public-schema data is supported; additional schemas/roles,
external media, external writers, hostile archive ingestion and schema-version
conversion are outside this workflow. Retaining both files on the same worker is
not protection against loss of that worker. Do not start using real collection data
on the strength of this workflow alone.
