# Optional catalog artwork

Implemented for review; not deployed. When a configured provider returns a cover,
match review offers an unchecked **Include catalog cover** option. Choose it and
Use these details to stage the selection, then Save copy or Save details. A
selection can contain only the cover, without replacing any text. Remove selected
cover discards a pending selection. Scanning another barcode or changing collection
type clears it; merely searching or viewing a cover never saves media.

The final JSON save accepts optional `catalog_cover` with `provider` and
`candidate_id`. The server rechecks the type's installed lookup provider and
`cover_art` setting. It accepts no URL or image path from the browser. The adapter
fetches and validates the image through its existing bounded HTTPS cover handler.
Copy/details and media metadata commit together. Unavailable or invalid covers
return 422 without creating a copy or changing its details/history; the draft is
retained so the owner can remove the cover selection or retry. An uncertain save
still requires reload/review under the existing write rules.

Imported images use the same private media store, checksum and protected download
endpoint as photos, with role `catalog_cover`. Provider, candidate ID, trusted
source URL and creation time remain attached to the asset. A source link and
**Catalog artwork** label distinguish them from photographs of the physical copy.
Existing photos and previously imported covers remain intact. Reimporting the
same provider/candidate into one copy is idempotent; distinct copies stay distinct.
A cover-only attachment does not change catalog identity or label revision/history;
its immutable media record retains its own source and time. Label changes use
existing revision-checked detail history. No cover deletion/replacement is added.

`lookup.cover_art` remains the type-config switch. Installed cover adapters also
may normalize IDs with `canonical_id(candidate_id)` and provide
`source_url(candidate_id)` for a trusted release link on their registered
HTTPS origin. MusicBrainz is the first adapter. New services require reviewed
adapters, not arbitrary URLs/config code; provider secrets stay private.

## Migration and recovery

Additive migration `0012_catalog_covers` adds nullable source metadata to
`media_assets`, a source requirement for catalog covers, and uniqueness per
copy/provider/candidate. Existing photos retain role and bytes with null source
metadata. Apply before the changed API; then deploy web. No new dependency or
network access is needed beyond the existing configured-provider deployment.

Downgrade refuses while imported artwork/source metadata exists. Preserve a
verified complete database/media backup and matching application images before
any nondisposable schema change. Restore to a fresh offline target and verify
all row/migration/media fingerprints before promotion. Never delete imported
artwork or provenance just to make a downgrade succeed. Files whose commit status
cannot be confirmed are retained for inspection; cleanup removes only staged images that were never flushed to PostgreSQL.
A flushed file is retained after an error because a confirming read can race an
in-flight commit; an orphan is preferable to missing committed media.

Artwork is a catalog illustration, not ownership evidence or confirmation of the
exact pressing, issue, condition or physical object. Manual intake and physical
photos remain available without catalog lookup or artwork import.
