# Collectible photo storage (PR #5)

The API stores original JPEG, PNG, and WebP uploads on a filesystem volume and stores metadata in PostgreSQL's existing `media_assets` table.

- `POST /api/v1/inventory/{copy_id}/photos` — multipart field `file`, maximum 15 MiB, returns metadata.
- `GET /api/v1/inventory/{copy_id}/photos` — lists photo metadata.
- `GET /api/v1/inventory/{copy_id}/photos/{photo_id}` — streams the original image.

Set `MEDIA_ROOT` to an **absolute, writable, persistent** directory mounted into the API container. This is required only for photo operations; existing inventory endpoints remain usable without it. The database and media directory must be backed up together.

Only server-generated UUID-based relative storage keys are stored. Uploads are checked using Pillow rather than trusting filenames or request MIME types. The service stores original bytes, not thumbnails; image normalization, thumbnail generation, deduplication, and deletion are deferred.

**Security:** Authentication is not implemented. Do not expose these endpoints outside the isolated development network. Uploaded images may contain EXIF metadata and are returned unmodified. Do not put `MEDIA_ROOT` under a public static-file server.

**Validation:** Run migrations and tests against a fresh disposable PostgreSQL 17 database, set `TEST_DATABASE_URL` explicitly, and run `python -m pytest -v`. Do not use production data or expose host ports. Tests use temporary filesystem directories.
