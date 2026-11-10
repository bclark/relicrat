# Owner inventory export

The owner export is a ZIP with UTF-8 JSON files and the original image bytes.
Open it with a standard archive tool and read the JSON in a text editor.
Treat it as private inventory data. The ZIP is unencrypted.

From the [Linux Compose install](linux-compose-install.md) checkout for a
release that includes owner export, load the same release pin and use the same
`compose` function as for normal operation. Run this from the server shell
while the API and database are running:

```sh
(
  set -eu
  umask 077
  output="relicrat-owner-$(date -u +%Y%m%dT%H%M%SZ).zip"
  temporary=$(mktemp './.relicrat-owner.XXXXXXXX')
  trap 'rm -f "$temporary"' EXIT
  trap 'exit 1' HUP INT TERM
  compose exec -T api python -m relicrat.owner_export > "$temporary"
  ln "$temporary" "$output"
  printf '%s\n' "$output"
)
```

The command publishes the ZIP only after export succeeds and refuses to
overwrite an existing file. Export reads one consistent database snapshot. A
missing, unsafe, or damaged referenced image fails the command.

| ZIP member | Contents |
| --- | --- |
| `manifest.json` | Format identifier `relicrat-owner-export`, integer version `1`, and UTC export time |
| `copies.json` | Physical copies with stable UUIDs, including provisional and archived copies. A non-null `deleted_at` marks an archived copy. |
| `catalog_items.json`, `releases.json`, `categories.json` | Catalog and edition records. Join a copy's `catalog_item_id` or `release_id` to `id`. Unidentified copies may have null links. |
| `custom_collections.json`, `custom_collection_types.json` | Custom collection and field definitions for interpreting copy details |
| `storage_locations.json` | Location records. Start at a copy's `storage_location_id` and follow `parent_id` to reconstruct the current hierarchy. |
| `movement_history.json` | Moves keyed by `owned_copy_id`, ordered by `after_revision` per copy. A null location represents an unassigned copy. Location names and nesting reflect the current location records. |
| `photos.json`, `photos/` | Photos and saved covers keyed by `owned_copy_id`. Each `path` is relative to the ZIP root, with the byte size and SHA-256 in the metadata. |

This format covers inventory inspection and use by external tools. Use the
[backup and restore procedure](backup-restore.md) to recover a working
installation, including application settings and database history beyond copy
movements.
