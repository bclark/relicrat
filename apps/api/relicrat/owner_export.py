"""Write a portable owner inventory ZIP to stdout from the operator shell."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select, text

from relicrat.database import session_factory
from relicrat.media import IMAGE_FORMATS, MAX_PHOTO_BYTES, media_root
from relicrat import models

# Explicit v1 fields keep future schema changes from silently changing the format
# or exposing new internal fields.
DATASETS = (
    ("copies", models.OwnedCopy, """
        id catalog_item_id release_id custom_collection_id provisional_title description
        collection_type edition_label record_details comic_details movie_details game_contents
        custom_details barcode identification_status ownership_status storage_location_id
        created_at updated_at deleted_at
    """),
    ("categories", models.Category, "id slug name"),
    ("catalog_items", models.CatalogItem, "id category_id canonical_name attributes"),
    ("releases", models.Release, "id catalog_item_id name release_key attributes"),
    ("custom_collection_types", models.CustomCollectionType, "id definition"),
    ("custom_collections", models.CustomCollection, "id slug type_id proposal"),
    ("storage_locations", models.StorageLocation, "id parent_id name kind description"),
    ("movement_history", models.CopyLocationEvent, """
        id owned_copy_id before_location_id after_location_id before_revision after_revision operation created_at
    """),
)
PHOTO_FIELDS = "id owned_copy_id content_type byte_size sha256 role source_provider source_id source_url created_at"


def rows(db, model, fields, *, order=None):
    table = model.__table__
    query = select(*(table.c[field] for field in fields.split())).order_by(
        *(order or (table.c.id,))
    )
    for row in db.execute(query.execution_options(yield_per=500)).mappings():
        yield dict(row)


def write_records(archive, name, records):
    with archive.open(f"{name}.json", "w", force_zip64=True) as output:
        output.write(b"[\n")
        separator = b""
        for record in records:
            output.write(separator + json.dumps(record, ensure_ascii=False, default=str).encode("utf-8"))
            separator = b",\n"
        output.write(b"\n]\n")


def photos(db, archive, root):
    extensions = dict(IMAGE_FORMATS.values())
    for photo in rows(db, models.MediaAsset, PHOTO_FIELDS + " storage_key"):
        extension = extensions.get(photo["content_type"])
        asset_id = photo["id"].hex
        key = photo.pop("storage_key")
        if not extension or key != f"{asset_id[:2]}/{asset_id}{extension}":
            raise ValueError(f"Invalid storage key or type for photo {photo['id']}")
        path = root / key
        if path.resolve() != path or not path.is_file():
            raise ValueError(f"Missing or unsafe file for photo {photo['id']}")
        with path.open("rb") as source:
            data = source.read(MAX_PHOTO_BYTES + 1)
        digest = hashlib.sha256(data).hexdigest()
        if not 0 < len(data) <= MAX_PHOTO_BYTES or len(data) != photo["byte_size"] or (
            photo["sha256"] is not None and digest != photo["sha256"]
        ):
            raise ValueError(f"Size or checksum mismatch for photo {photo['id']}")
        photo["sha256"] = digest
        photo["path"] = f"photos/{photo['id']}{extension}"
        archive.writestr(photo["path"], data)
        yield photo


def write_export(db, root: Path, output):
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        manifest = {
            "format": "relicrat-owner-export",
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for name, model, fields in DATASETS:
            order = (model.owned_copy_id, model.after_revision) if model is models.CopyLocationEvent else None
            write_records(archive, name, rows(db, model, fields, order=order))
        write_records(archive, "photos", list(photos(db, archive, root)))


def main():
    try:
        with session_factory()() as db:
            write_export(db, media_root(), sys.stdout.buffer)
        sys.stdout.buffer.flush()
    except ValueError as error:
        print(f"Owner export failed: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("Owner export failed. Check database access, media readability and output capacity.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
