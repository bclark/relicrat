# Collection definitions and future Packs

Built-in entry types now have one JSON definition per type in
`apps/api/relicrat/collection_types/`: `other.json` and `record.json`.
They are bundled release source, validated at API startup and served through the
owner-only, read-only `GET /api/v1/collection-settings/types` endpoint. The web
setup and intake use the same definitions; no copied frontend registry is needed.

Each version-1 definition supplies its stable ID, singular/plural labels, title
label/placeholder, and ordered optional fields with labels, placeholders, limits
and suggested visibility. Only the browser title is required. Suggestions apply
when opening untouched setup; saved owner preferences remain authoritative.
Changing suggestions or hiding a field never deletes existing observations.
Record artist/format API bounds also come from the validated definition.

Definitions describe supported storage, rather than creating it. Validation
rejects unsupported versions, IDs, duplicate/missing/unknown fields, extra keys,
invalid labels and limits that disagree with the deployed database/API contract.
Adding Books, Comics or a new field still needs a reviewed end-to-end storage,
validation, search and history implementation and, where applicable, a migration.
Existing type IDs and field keys are durable data identities, not editable labels.

No scripts, SQL, templates, paths, remote references or runtime uploads are
accepted. Catalog identity, ownership, search query construction, audit writes,
revisions, storage assignment and backup remain explicit domain code. Editing a
label does not rename a saved title, infer an artist or create a catalog match.

Portable, installable Collection Packs remain future work. Packs may eventually
describe catalogs and completion rules but must never store or imply private
ownership. Bundled type definitions are the first bounded configuration step,
not an installer or a general custom-field engine.
