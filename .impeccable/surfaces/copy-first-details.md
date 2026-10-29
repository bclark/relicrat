---
mode: Operate
primary_target: apps/web/app/copy-details-form.tsx
related_targets: [apps/web/app/copy-detail.tsx, apps/web/app/inventory-client.tsx, apps/web/app/identification.tsx, apps/web/app/globals.css]
---

# Copy-first detail editing

The owner sees “Harbor Lights - blue vinyl” already saved and should not have to
recreate it as a catalog identity. Present its existing title and optional edition
as ordinary editable fields, followed by one Save details action. Saved-copy
status is valid without a catalog match. Retain the established paper/rules,
system typography, cobalt actions, native controls and desktop/mobile layout.

The primary form appears before photos and storage in the selected record.
Personal edition labels are explicit when a shared release is also linked.
Copy edit history is a lazy, paginated disclosure. Catalog matching is closed
under Advanced and starts reading only after first opening; closing it keeps any
in-flight work mounted. Its separate Save catalog match action cannot silently
edit personal labels or create ownership.

Preserve per-copy identity, media, storage, disposition and history. Failed
edition-prefill requests disable the form; delayed reads are cancelled when
copies change. Stale/uncertain writes require Reload copy; no POST retry or false
success/unsaved claim. Existing titles are prefilled rather than inferred or
split from their text. Unknown editions remain optional and are not zero.

Initial desktop1440/phone390 captures were inspected together. The simpler form
requires no visual fix batch and uses no new design tokens, assets or dependencies.
The root design record and sidecar remain unchanged. Detailed validation and
migration/recovery evidence belongs in docs/harness.md.
