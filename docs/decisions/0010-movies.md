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
preview notes. The initial Movie release did not activate an external catalog provider.

Migration 0013 is additive, preserving older records and preferences. Downgrade
refuses new observations/history/preferences/import batches rather than erasing
them. The [Movie contract](../movies.md) owns exact mapping, limits, recovery and
deployment boundaries. No new dependency or generic field/provider framework is
required.


2026-11-01 follow-up: Movie JSON now selects an installed UPCitemdb adapter for
reviewed title suggestions. This is a general retail match, not a shared movie
identity or confirmed edition; it creates no ownership until the normal save.
Brand, format, pricing and images are not mapped to saved Movie observations.
Provider/mapping changes retain the existing validated config/adapter boundary.
See the [Movie barcode lookup contract](../barcode-lookup.md#movie-title-lookup-with-upcitemdb).
This follow-up needs an API rollout, not a database migration.


2026-11-01 provider trial: GTINHub is an installed title-only alternative after
an exact Movie barcode lookup succeeded where UPCitemdb had no record. The
proposed Movie JSON selects its no-key 10/day evaluation. UPCitemdb remains
installed/selectable; no implicit fallback or paid plan is activated. Review,
identity, ownership and save boundaries remain unchanged. See the
[trial contract](../barcode-lookup.md#gtinhub-movie-trial) for limits and rollout.
