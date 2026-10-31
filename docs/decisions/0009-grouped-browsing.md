# 0009 — Read-only, config-driven collection groups

Status: Implemented for review, not deployed by this change.

A large inventory needs browsing by series or artist rather than a flat intake
feed. Default to collection-type groups, then configured groups of physical
copies: Comics by provisional series/title; Albums by saved artist. Keep the
individual-copy view and a separate exact-location filter. Other remains a flat
list because it has no configured common grouping field.

Use one shared SQL filter for summaries and members, covering search, type,
effective location and soft deletion. Count before paginating summaries; fetch
bounded member pages only when a group is opened. Use ordinary JSON/text values
as bound group keys, with null for missing values. Trim outer spaces but preserve
case distinctions; no grouping key is canonical identity and copies remain
separate even when titles/artist names match. Keep unknown values explicit.

The type JSON describes a bounded grouping field, labels and member order. The
parser accepts only deployed storage fields and ordering combinations. No
arbitrary property/SQL path, executable configuration or provider framework is
added. Album member ordering is by title; comic ordering uses leading whole
numbers and then full issue text, without rewriting special identifiers.

Changing list filters or views preserves unsaved intake/edit drafts and resets
only browse pagination. Independent AbortControllers prevent obsolete responses
from replacing newer scope. Uncertain intake writes still require review; Reload
inventory switches to the individual view when needed to inspect a possible save.
Location options have explicit paging instead of silently stopping at 100.

This release adds read-only API/UI behavior without a migration or new database
writes. Index tuning and richer issue ordering need measured requirements.
Reviewed mapping of imported storage labels, case reconciliation, catalog
merging, saved browse preferences and multi-user collections are outside scope.
