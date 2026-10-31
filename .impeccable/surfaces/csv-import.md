---
version: 1
slug: "csv-import"
primary_target: "apps/web/app/csv-import.tsx"
related_targets: ["apps/web/app/inventory-client.tsx"]
---

# CSV import

Mode: Operate. Extend the incumbent inventory UI with native file/select/checkbox
controls, semantic headings, the existing ruled setup section and theme tokens.
This is a bounded intake task, not a branding redesign.

Compact Import CSV disclosure opens choose → preview → acknowledge → import.
Preview is read-only. Counts and first ten examples precede confirmation. Make
retained fields, mapping, duplicate limitations and blocked errors explicit.
Preserve intake drafts and list filters. Do not silently retry uncertain writes;
a new preview can recognize an already-completed exact file. History and retained
source rows are paginated, private, escaped text with explicit copy links.

Check desktop/mobile fit, keyboard labels and status announcements, plus real
synthetic volume, duplicate-file prevention and ambiguous-write recovery.
