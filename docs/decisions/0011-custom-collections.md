# 0011 — Explicit custom collection activation and figure intake

Status: implemented for review; not deployed. Requires API/web and additive
migration `0014_custom_collections`. No live migration is authorized by this file.

The owner approved creating an empty collection from the reviewed TMNT JSON,
then explicitly adding owned figures. Definitions and checklist goals never
create ownership, catalog items, releases, valuations or completion claims.

## Storage and identity

`custom_collection_types` retains the validated type definition by stable text
ID. `custom_collections` has a UUID, unique source slug, type foreign key, complete
proposal/checklist/evidence and creation timestamps. Both are immutable in this
first version; database triggers reject updates/deletes. An identical import
reopens the saved collection; a different definition under the same type ID or
checklist under the same collection slug returns 409. A type can serve multiple
collections when its definition is identical. No in-place revision UI yet.

Figures use existing `owned_copies` UUIDs, notes, media, storage, reconciliation
and personal-detail history. The built-in discriminator remains `other` for
legacy-client compatibility; `custom_collection_id` is the authoritative custom
membership and determines the saved type. It is not a catalog/release link.
Membership/intake identity is immutable; there is no conversion or reassignment
workflow in this increment. Saved collections have their own selector and paged
figures. The built-in category/group controls remain unchanged.

`custom_details` holds bounded optional text observations. The creation service
and database trigger enforce definition field IDs/lengths and a required bounded
title; missing values mean unknown. Title and custom fields share the existing
revision-checked Save details operation and before/after history. Old-client
omission preserves custom observations. Search includes escaped, parameterized
custom text; inventory can filter by collection UUID. No custom value becomes SQL.

A client UUID plus a retained original intake fingerprint makes physical-copy
creation retry-safe. A transaction-scoped PostgreSQL advisory lock serializes
that UUID, and the copy primary key remains the final uniqueness boundary.
An exact retry returns the same current copy without overwriting later edits.
Changed payload/collection returns 409. UI retries retain their original target
collection even if another collection is created; unsaved drafts are not moved.

## Trust and scope

The same bounded raw-JSON parser/model serves preview and activation. The agent
prompt embeds its generated schema and explicitly requests plain HTTPS URLs,
without Markdown link syntax. Evidence stays untrusted text and is never fetched.
Owner authentication, fixed web routes, same-origin POST and actual-byte limits
apply to all writes. The owner reviews scope/fields/checklist before Create
collection; Add figure is a separate ownership action.

The pilot still supports figure-style scope, optional text fields, and no lookup
adapter. It does not compute completion, authenticate original editions, assign
copies to checklist entries, revise definitions, import arbitrary field controls,
or implement universal custom type/provider support. Notes/photos/storage remain
shared inventory facilities, rather than independently implemented pack fields.

## Recovery and rollout

The existing backup helper enumerates all public tables and JSON columns, so it
captures definitions, checklist proposals, custom details and history. Preserve
matching source/images in recovery capsules. Downgrade explicitly refuses any
custom definition, collection, copy or retained custom history; use verified
recovery rather than dropping it. Verify empty upgrade/downgrade and populated
copied restore on disposable data before rollout. Deploy API before/with web;
keep existing owner settings and backup/network isolation rules unchanged.
