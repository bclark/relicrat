# Viewing and editing an owned item

Implemented for review, November 4, 2026. Deployment is separate.

Opening a copy gives its record the browser's content area. Collection navigation
remains on desktop; phone uses the same reading order. Saved observations are
readable before editing, including values hidden from new-entry preferences.
Catalog artwork remains identified separately from photos of the physical copy.

**Edit details** opens a focused editor. Labels, order, autocomplete, format choices
and custom controls reuse existing type definitions and owner preferences. Only
supported fields are editable; existing legacy title-less provisional copies keep
their API rules. Built-in type correction is a separate disclosure. Named custom
membership cannot be changed with that control. Barcode, reviewed provider
suggestions and optional catalog-cover behavior use the existing implementation.

**Save changes** uses the existing details endpoint and revision checks. Confirmed
success returns to reading with Changes saved. Cancel asks before discarding a
dirty draft. Back to item retains the mounted draft and offers Continue editing.
Back to collection preserves search, filters, pagination, selection and scroll;
replacing an item still checks its unsaved/uncertain guard. Drafts are page-local,
not refresh-safe or offline storage.

Storage selection still saves immediately and confirms its destination. Photo
uploads remain separately labeled writes. Neither is bundled into the details
payload. While the details draft is being edited, those operations are hidden;
storage is disabled when returning to read with dirty details. Notes remain
read-only under the existing API. Physical-copy identity, ownership, catalog
relationships and history remain authoritative; no checklist qualification is
implied by editing observations.

A conflicting or unconfirmed save locks further writes and keeps the draft.
Inspect saved details performs a read into a separate comparison; it does not
replace the draft, infer success, or retry. Reload copy explicitly warns before
discarding the local draft. A known custom-definition rejection allows reloading
field controls while keeping entered values for review under the new revision.

This change adds no API route, schema migration, dependency or theme capability.
The approved synthetic concept is historical design evidence under
`docs/design/proposals/item-edit-2026-11-04/`, not the actual application's fixture
or a source of configuration. See the harness guide for executed checks and limits.
