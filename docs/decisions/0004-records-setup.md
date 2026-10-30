# 0004 — Personal collection setup and Records details

Status: Accepted direction for the private synthetic trial; implementation awaits
human review, merge and a deliberate API/schema/web rollout.

A collector should enter an album title and optional artist, rather than combining
both into a generic title or completing shared catalog matching. The first
specialized flow is Records; Other preserves generic entry. Additional types,
arbitrary custom fields, financial tracking and Collection Pack installation are
deferred until their complete storage and validation paths exist.

One owner has durable, revision-checked setup preferences: whether Records is a
usual collection type, the default for new finds, and which optional fields to
show. Setup is skippable, revisitable, and saved once after preview. Preview and
setup never create ownership or shared catalog data. A one-off type choice does
not change the saved default. Preferences are server data, included in recovery,
not a cookie or local browser setting.

Record copies store their explicit personal type and bounded artist/format
observations. Album title reuses the existing personal title. Edition/pressing
reuses the personal edition label. These are provisional observations, not verified
catalog identities; ordinary entry never creates shared categories/items/releases.
JSONB is bounded to artist/format with API and database checks, not an unrestricted
custom-field engine. Format is optional text so unusual physical formats remain
possible without treating a guessed default as fact.

Turning fields off changes new-entry visibility only. Existing values remain
editable and searchable, and included in backups. Changing an existing copy's type
preserves its observations. Earlier combined titles are never parsed or rewritten
automatically. Copy UUIDs, media, storage, creation time, disposition and all prior
history survive. Artist/type/format edits use the existing row lock, revision
checks and atomic before/after audit events. Older clients that omit these fields
preserve them. Blank optional fields mean unknown, not a guessed value.

Migration0006 is additive and leaves legacy copies as Other with no observations.
It seeds a singleton default preference row without completing setup. Existing
edit events retain their original meaning, with NULL new columns. PostgreSQL
check definitions use explicit text casts so their schema representations remain
stable across dump/restore, allowing the independent recovery verifier to keep
its exact comparison.

Downgrade loses preferences, record observations and record-only edit events that
cannot satisfy the old title/edition-only history constraint. Mixed events retain
their title/edition history. This is a disposable rehearsal, not an automatic live
rollback. Verified recovery and a reviewed release plan must precede deployment.
