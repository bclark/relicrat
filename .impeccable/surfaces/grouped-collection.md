---
version: 1
slug: "grouped-collection"
primary_target: "apps/web/app/grouped-collection.tsx"
related_targets: ["apps/web/app/inventory-client.tsx", "apps/web/app/storage-filter.tsx", "apps/web/app/collection-rows.tsx"]
---

# Grouped collection browsing

Mode: Operate. Preserve the incumbent inventory typography, theme tokens, ruled
rows and native labeled controls. Extend the collection pane rather than creating
a new dashboard or replacing branding.

Default type counts lead into series/artist groups with full-result counts.
Expanding one group exposes physical-copy rows and its own pager. Keep the
individual view, search and separate storage selector. Unknown fields are named
explicitly. Expose group loading, empty, error, selected and retry states. Keep
read scopes independent and cancel obsolete reads. Draft intake and detail forms
remain outside the browsing lifecycle.

Check the full copy workflow, then a generated large collection, phone fit,
independent group/member paging, missing artists, storage scope, stale reads and
unsaved drafts. Source values are text, not markup or catalog identity.
