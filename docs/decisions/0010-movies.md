# 0010 — Movies retain physical-copy identity and import provenance

Status: implemented for review; requires merge and a verified schema/API/web rollout.

Movies extend the existing bounded type-definition, personal JSONB observations,
revision-checked edit history and setup preferences. Reuse the current inventory
model, media/storage/search and transactional CSV importer. Configuration controls
labels, field order/visibility, native form choices, grouping and optional lookup;
it does not invent writable database fields or execute provider code.

A movie release/box set is one physical item. Each Blu-ray.com export row creates
one provisional copy after explicit digest-bound confirmation. Disc counts and
external product IDs neither expand nor deduplicate ownership. Original columns
are retained as private source evidence; prices, dates and movie identities are
not inferred. Invalid/conflicting UPC/EAN observations remain source values with
preview notes. No external Movie catalog provider is activated.

Migration 0013 is additive, preserving older records and preferences. Downgrade
refuses new observations/history/preferences/import batches rather than erasing
them. The [Movie contract](../movies.md) owns exact mapping, limits, recovery and
deployment boundaries. No new dependency or generic field/provider framework is
required.
