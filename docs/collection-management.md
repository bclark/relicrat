# Managing collections

Implemented for review, November 4, 2026; deployment remains separate.

Manage collections replaces the scattered setup, definition-authoring and custom
administration entry points with one bounded list. Built-in types and saved custom
collections share that list. Custom choices are paginated independently; failed
pages clear stale choices and retain explicit reload. Desktop collection navigation
and the existing inventory stay available, with browsing/drafts mounted behind the
management task. CSV import remains under Collection tools and imports.

Built-in entry preferences choose which optional observations appear for new
items. A selected type's save preserves other types, enabled flags and the All-items
default. Other's basic fields are read-only. New-item defaults and supported types
retains the existing complete setup workflow, including type enabling, default,
field selections and preview. A selected collection still overrides that default.

Creation follows describe → actual downloadable/copyable agent instructions →
JSON → server validation and preview → acknowledgement → explicit empty collection
creation. The authoring contract remains the current figure-collection pilot.
There is no embedded agent or executable plugin. Only the supplied description
is appended to the actual current instructions; inventory/media are excluded.
Files remain bounded to 64 KiB with stale file-read guards. Evidence stays text;
structural validation never certifies facts, authenticity or ownership.

Review retains scope, completion/eligibility, checklist, typed entry controls,
source support text and uncertainties. Original import reopens its saved collection;
independent import retains stable new identifiers across an uncertain creation retry.
Creation never starts owned-item intake automatically. Browse collection is an
explicit next action after confirmed creation; ownership and checklist matching
remain separate reviewed operations.

Custom controls reuse server definition-preview/definition validation and revision
checks, a live illustrative control preview, explicit acknowledgement and definition
history. The server's affected-collection count is authoritative; this API does not
supply every affected name, so the interface labels that limitation rather than
inventing a complete list. Incompatible saved values block application. Changing
controls or choices invalidates the review and acknowledgement. Compatible choice
controls retain their options when switching between dropdown and radio forms.

Back retains mounted descriptions, JSON and settings drafts. Replacing a settings
editor or leaving the page checks dirty/uncertain state. Unconfirmed creation freezes
the exact preview for its existing safe retry. Conflicting/uncertain definition saves
block another write until explicit inspection/reload; saved-state inspection is a
separate read and does not replace the draft. Reload warns before discarding a draft
and only replaces it after a successful read. Settings recovery similarly reloads
saved preferences without retrying the write. These are page-local drafts, not
refresh-safe or offline storage.

Task and authoring-step transitions focus their visible heading so keyboard users
continue within the revealed task. The management desktop rail omits the inventory's
phone selector, keeping the phone collection label attached to its one visible control.

No API, schema, migration, dependency or theme capability is added. Existing details,
storage, media, ownership and provenance operations remain authoritative. The approved
fictional concept is historical evidence in `docs/design/proposals/collection-management-2026-11-04/`.
See the harness guide for executed checks, skipped coverage and private evidence.
