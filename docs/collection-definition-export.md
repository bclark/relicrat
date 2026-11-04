# Export a custom collection definition

Implemented for review, 2026-11-03; not deployed. Frontend only: no API, schema,
dependency, provider or network-access change.

Choose a saved collection under **Your custom collections**, then use **Export
collection JSON**. The browser downloads `relicrat-collection.json` in the existing
`relicrat-collection-proposal-1` format. Import through **Start a new collection**,
validate and review the definition, then explicitly create the collection.
Export never creates or changes ownership or checklist qualification.

The export reads the current saved definition, including applied field-control
revisions, rather than unsaved form changes or the original field definition.
It includes the type fields/controls/options, checklist, scope, completion rules,
sources and uncertainties. Collection and type identifiers are retained. The
normal importer still rejects conflicting definitions under existing IDs; use
new IDs for a different definition. This is portable setup JSON, not a backup
or a way to overwrite a saved collection.

Only the six proposal root fields enter the existing read-only preview validator.
The download contains its validated proposal, excluding response wrappers, owned
figures, personal observations, photos, storage, match/progress state, audit
history and owner settings. Definition text and source links are included, so
review that text before sharing it. No source URLs are fetched.

A fresh authenticated read and schema validation must succeed before download.
Read/validation failures create no file and preserve saved data and drafts.
Changing collections cancels an in-flight export. Busy controls prevent duplicate
requests. Files normally use indented JSON; large definitions use compact JSON
so they stay within the existing 64 KiB import limit. An oversized canonical
result fails explicitly instead of producing a file the importer cannot read.

Existing native buttons, messages and theme tokens are reused. This increment
adds no new sharing service, automatic import, ownership transfer, or provider.
