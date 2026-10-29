# 0003 — Copy-first title and edition labels

Status: Accepted for the private synthetic trial; implementation requires review,
merge and a verified migration before deployment.

The owner repeatedly found shared catalog matching confusing even after its
labels were clarified. A saved physical copy already has a title. Editing it
must not require creating another logical collectible or learning release keys.

Keep the existing provisional title and add a personal edition label to the
owned copy. Present both in one prefilled form with one save action. Catalog
matching remains optional, closed under Advanced. Basic edits never create or
merge shared identities or ownership. Identity, photos, storage, disposition,
creation time and all earlier history remain on the same physical-copy UUID.

A NULL edition label follows the linked release when available. A string is a
manual label; an empty string explicitly means unknown. Unchanged inherited
editions stay inherited during title edits. Explicit labels survive later
reconciliation and remain visibly personal when a release is also linked. This
is descriptive provisional information, not a new release identity or a verified
match. No automatic parsing of titles or name-based identity merging is added.

Serialize edits with the existing physical-copy row lock. Check independent
copy-edit and identification revisions, and write a before/after audit event in
the same transaction. Record the observed identification revision for inherited
edition context. Current no-ops do not create events; stale revisions still fail.
Failed or uncertain writes never trigger an automatic retry.

Migration 0005 is additive and initializes every old label/revision as NULL/zero.
Its downgrade discards the new labels and edit history, so it is a disposable
rehearsal operation rather than an automatic live rollback. A verified offline
capture is required before the eventual rollout. Backups and fresh restores must
preserve actual edited labels and history, not just an empty new table.
