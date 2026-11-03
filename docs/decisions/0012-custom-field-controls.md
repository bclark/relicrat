# 0012 — Configured custom field controls and compatible revisions

Status: implemented for review, 2026-11-03; not deployed. Extends
[ADR0011](0011-custom-collections.md) with additive migration
`0015_custom_field_controls`. Existing ownership, membership, checklist and
catalog/release boundaries remain unchanged.

## Config contract

Each optional field declares `input` and, for choice controls, `options`:

| input | Saved value | Behavior |
| --- | --- | --- |
| text | string | Free text bounded by max_length |
| select | string | One dropdown choice |
| radio | string | One radio-button choice |
| checkbox | boolean | Explicit Yes or No |
| checkboxes | string array | Zero or more distinct choices |

For example, Head Variant is mutually exclusive:

```json
{"id":"head_variant","label":"Head Variant","input":"radio","max_length":50,"options":["Soft","Hard"]}
```

Unknown is an absent property, shown as Not recorded. It is distinct from
`false` (No) and `[]` (None selected). A clear action restores unknown.
Choices are 1–20 unique nonempty strings, bounded by the field's max_length;
text and a single boolean checkbox cannot declare options. Field IDs remain
stable; title is still the only required observation. The external-agent prompt
embeds the generated validator schema and explains these choices. No executable
code, new lookup provider or ownership record is installed by configuration.

The same native-control renderer serves preview, intake and Save details.
Existing text-only JSON remains accepted and exact original-import retries
still reopen their original collection. Old clients omitting custom observations
preserve them; optional expected_type_revision allows legacy clients while
current clients reject stale controls before a write with HTTP 412.

## Safe definition updates

Configure field controls edits the existing fields' control and choices.
Review validates every saved copy sharing the type, including retained inactive
copies; Apply explicitly acknowledges all affected collections. Values are never
coerced, rewritten or discarded. Converting text Soft to radio Soft/Hard works;
a stored Soft head value blocks that conversion until the owner reviews it.
Used fields cannot be removed or narrowed incompatibly through the API.

Original type definitions and imported collection proposals stay immutable.
`custom_type_revisions` appends sequential immutable snapshots. Revision zero
is the original type; collection reads overlay its latest definition and return
`type_revision`. Definition history is paginated. Multiple goals sharing a type
use the same latest definition. Concurrent Apply requests use expected_revision;
only one can append, and stale requests return 409. Lost-response recovery uses
Reload field controls and history, rather than an automatic second write.

API operations and database triggers serialize copy writes and revisions using
a transaction advisory lock per type. PostgreSQL validates field/value shapes,
choices, sequence and compatibility, including direct SQL writes. The ordinary
copy details revision and before/after history retain typed observations. Exact
original intake retries still recover after a later definition revision.

## Recovery and limits

Migration 0015 adds a table and replaces the custom-copy validator without
rewriting existing inventory or deployed migrations. Backups enumerate all public
tables and capture revisions, typed JSON and history with matching source/images.
Empty upgrade/downgrade is supported. Downgrade refuses any revision, nontext
base definition, or typed observation/history; use verified recovery instead.
Deploy API/migration with the matching web build after review and a fresh backup.

This remains the bounded figure-style proposal format. The UI does not rename,
add or remove fields yet; an agent-authored proposal can define new collections
with any supported control. Checklist completion, membership changes and merging
custom collections into the built-in type selector are separate work.
