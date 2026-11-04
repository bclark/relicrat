# Import a definition as a new collection

Implemented for review, 2026-11-03; not deployed. Frontend only: no API, schema,
dependency, provider or network-access change.

Upload or paste collection JSON under **Start a new collection**. Select **Import
as a new collection**, enter its name, then **Validate and preview**. Review its
fields, scope, checklist and sources, acknowledge the review, then explicitly
**Create collection**. This creates an empty collection with independently
editable field controls. Existing collections, owned figures, checklist matches
and personal history are preserved.

Normal import remains the default. The new option validates the original raw
JSON through the existing parser before transforming anything. Duplicate keys,
invalid fields and oversized documents cannot bypass that boundary. From the
validated proposal, it changes only the collection name, collection ID, type ID
and corresponding collection type reference. Checklist entry/source IDs, field
controls/options, scope, completion rules, evidence and uncertainties are retained.
A second preview validates the transformed document, including its 64 KiB limit.
Source-link correction notices from the first validation remain visible.
No raw client JSON parser, new endpoint or automatic conflict fallback is added.

Collection and type identifiers use separate fixed prefixes plus a generated
UUID, within the existing identifier bounds. They stay stable across unchanged
revalidation and creation retries. Renaming, changing mode or editing source JSON
invalidates the preview and acknowledgement. The original JSON remains visible
and unchanged. Name/mode edits during file reading preserve the selected upload;
later source edits or another file still supersede an older file read.

An uncertain Create response locks definition changes and offers **Retry
collection creation** with the exact same reviewed proposal. The existing
transactional activation operation reopens that identical definition, preventing
an extra collection after a lost response. A confirmed rejection permits editing
again. This is setup-definition reuse, not ownership transfer or a recovery copy.
