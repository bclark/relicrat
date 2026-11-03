# Start a figure from a missing checklist entry

Implemented for review, 2026-11-03; not deployed. Frontend only; no migration,
API, dependency, theme-token or network-access change.

Both the main collection browser and saved custom collections expose **Add this
figure** on checklist entries with no confirmed or pending linked figure. A
collected entry keeps its progress; pending figures should be reviewed first.
The action opens existing custom intake for that collection UUID, reloads its
definition, resolves the selected entry ID and prefills the figure name. Focus
moves to that name. The owner may edit it and add personal details before the
existing **Add figure** save. No inventory or checklist match is written on click.
After saving, the existing inspector still handles explicit checklist matching
and eligibility confirmation. A checklist name is a suggestion, not proof of
identity, ownership or authenticity.

An unfinished custom title, notes, observations or pending save prevents replacing
the draft, even if another collection was requested. The notice explains how to
continue. Generic intake and copy-inspector drafts stay independent. Uncertain
save retries retain the existing request ID and payload. Collection choices still
refresh after a new collection event, even when a draft prevents switching.

A missing entry, name beyond the configured limit or failed definition read does
not prefill a different entry or save anything. No truncation, generated field
values or automatic ownership/checklist inference is performed. The existing
collection definition and server validation remain authoritative.
