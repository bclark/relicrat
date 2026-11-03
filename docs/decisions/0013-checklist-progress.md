# 0013 — Owner-reviewed checklist matches and progress

Status: implemented for review, 2026-11-03; not deployed. Requires additive
migration `0016_checklist_progress` and matching API/web. Extends the bounded
figure-style custom collection pilot; it does not install a general completion
rule engine or authenticate an original edition.

## Behavior and identity

A saved physical figure can be explicitly linked to one entry in its existing
custom collection. Selecting an entry leaves eligibility unreviewed. A separate
owner confirmation states that this figure meets the collection's eligibility
rules; only that confirmation counts toward completion. Changing entry resets
the confirmation in the UI. Clearing a match preserves history. No names,
barcodes, provider results, catalog identity, variants, accessories or packaging
silently establish a match, eligibility or ownership.

Collection progress counts entries with at least one confirmed, active, currently
owned copy. Duplicates/variants contribute at most one completed goal per entry;
the display also reports qualifying and pending copy counts. Sold, traded, lost
or soft-deleted copies do not count. Their matches/history remain retained, and
become effective again if that same copy returns to active ownership. Confirmation
is a retained owner assertion: later personal-detail or catalog edits do not
automatically revoke it; review the match explicitly when new evidence changes
its eligibility. Missing
entries include those with pending but no qualifying confirmed copies.

All counts use one aggregate query across the whole collection, independent of
inventory pagination. Definitions and the checklist remain immutable. Matches
do not change copy UUIDs, catalog/release links, collection membership, storage,
photos, personal observations or those facilities' independent save revisions.
The pilot still restricts a figure to its existing custom collection; overlapping
collection membership and box-set/multiple-goal matches remain separate work.

## Storage and consistency

`checklist_matches` retains each copy's current entry (nullable), confirmation,
revision and update timestamp. Missing state means unmatched at revision zero.
A physical copy has at most one current entry. An unmatched row cannot be
confirmed. Identity is immutable and deletes are rejected; clearing appends a
new revision rather than removing the row.

PostgreSQL validates copy/collection membership, checklist entry existence,
active ownership when assigning, and sequential meaningful revisions. API writes
lock the copy and compare expected_revision before modifying the match. The
trigger also locks the copy for direct database writes. Concurrent normal API
reviews serialize; a stale writer gets409 and must reload/review, rather than
silently overwrite another review. Disposition/deletion updates and matching
are serialized through the same copy row; progress always filters current state.

A database after-write trigger atomically appends `checklist_match_events`, with
before/after entries, confirmations, revision and server timestamp. Events cannot
be updated or deleted. Even a direct SQL match change receives a history row.
The single authenticated owner is the reviewer; no provider/model writes matches.

## Interface and API boundary

Saved collections show progress and a filter for entries without confirmed
figures. A figure inspector has a distinct Save checklist match action beside
its eligibility text. Unchecked means needs review, not proof of disqualification.
The history is paginated. An uncertain save or409 keeps the draft and blocks
another write until Reload saved checklist match reads the authoritative state;
there is no automatic retry. Reload explicitly replaces only the checklist draft.

Fixed authenticated routes expose progress, a member copy's current match,
revision-checked POST and paginated history. Web writes retain same-origin checks
and actual-byte bounds. Unknown/cross-collection entries are rejected by API and
DB; input is never SQL. Existing clients do not overwrite matches when saving
other copy fields. The existing theme and native form controls are reused.

## Recovery and rollout

The backup helper enumerates public tables, so current matches and immutable
history are included automatically. Verify full row/migration/media equality in
a fresh offline copied restore using the matching0016 API image. Empty
upgrade/downgrade is supported. Downgrade refuses either populated new table,
including cleared matches, because losing review history is destructive. Preserve
matching source/images and a fresh pre-upgrade backup before rollout. No deployed
migration is rewritten, and this ADR does not authorize a live upgrade.
