# 0005 — Bundled collection type definitions

Status: Proposed implementation for review; requires API and web rollout together.

Records setup established useful behavior but repeated labels and fields across
forms. Each supported type now has a versioned JSON definition bundled with the
API. A strict Pydantic loader validates it at startup; malformed configuration
fails startup. The read-only owner endpoint supplies definitions to setup,
intake and copy editing. Existing settings GET/POST shapes remain unchanged.
No new dependency, table or migration is needed.

Version 1 describes the existing Other and Record storage only. Stable field IDs
bind to explicit application behavior; labels, placeholders, optional-field order
and suggested visibility are data. Suggestions initialize untouched setup only;
owner settings continue to decide visibility, and populated hidden observations
remain editable. Title remains the only required browser intake field.

The loader enforces storage limits so JSON edits cannot widen database bounds or
invent a field that cannot be saved, searched, audited and recovered. New types
still need complete domain support and tests. Config contains no executable rules,
SQL, remote references, path selection or arbitrary formatting expressions.
There is no runtime config editor or pack import yet.

A failed definitions/settings read keeps the existing explicit generic-entry
fallback. It must not reset saved preferences or silently discard a draft.
No config read writes ownership, settings, shared catalog data or audit history.
Existing copies and old titles are never parsed or reclassified automatically.

Deploy the API before or with the web because the new web loads the definitions
endpoint. Old web remains compatible with the new API. Source definitions travel
in the existing image and git-archived recovery capsule; no external runtime
configuration is needed for restore. Reverting this release needs no database
rollback because persisted data shapes are unchanged.


## Entry assistance

The definition may set `entry_order`; version-1 definitions that omit it retain
title-first order. Records now puts optional artist before required album title.
Bounded control metadata selects native text/autocomplete or a Format select.
Only artist can query saved-value suggestions; only Format has a configured
choice list, always allowing Other and unknown. Unsupported control/field
combinations, duplicate or overlong choices and duplicate/missing order keys
fail definition validation. No code, query expressions or URL is configurable.

Artist suggestions are a protected, read-only, bounded database query over
non-deleted Record observations, independent of inventory pagination. Native
input/datalist preserves arbitrary typed artists and keyboard use. Requests are
debounced and aborted when obsolete. Failure leaves free typing and saving
available. Suggestions are never selected or persisted automatically.
Custom formats stay editable, including when owner preferences hide the field.
Selecting Other opens text entry; a failed save keeps that draft. Saving a new
find resets the dropdown to unknown. No acquisition/catalog/ownership inference
or migration accompanies these controls.

## Barcode observations

Bundled definitions may declare `barcode_formats` using the four supported
UPC/EAN decoder names. Duplicate, unknown or overlong lists are rejected. An
omitted/empty list disables new scans without hiding or discarding existing
observations. Barcode use remains an explicit draft action, followed by the
ordinary copy save; config never creates ownership or invokes a provider.
The stored observation, retained edit history and additive migration 0011 are
documented in the inventory API contract. No arbitrary identifier/provider
framework or configurable remote URL is introduced.
