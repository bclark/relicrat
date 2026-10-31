# 0006 — Comics as a supported collection type

Status: Proposed implementation; requires review, merge and a verified API/schema/web rollout.

Comics reuse one physical copy, photos, storage, search and the existing revision-
checked edit transaction. Series/title is the required browser title. Issue number,
publisher, personal edition/cover and notes are optional. Issue is bounded text,
so leading zeroes, fractions and Annual labels survive. No number or publisher is
guessed. Intake never creates a shared series/catalog identity or a release.

`comic.json` defines labels, optional fields, order, suggested visibility and
publisher autocomplete. Publisher suggestions query only non-deleted Comic
observations with literal prefixes, case-insensitive grouping and a 20-value
limit behind owner access. A fixed server-selected expression shares the existing
artist suggestion query; config cannot provide SQL or URLs.

`comic_details` is bounded JSONB (issue_number <=100 characters, publisher <=250)
with matching API and PostgreSQL checks. Comic edits use the same physical-copy
row lock and revision as title, edition and Album observations, committing one
before/after event. Type changes preserve both kinds of observations. Older
clients omitting the new metadata or preference fields preserve them. Hidden
populated fields remain editable. Existing UUIDs, media, locations, catalog links,
ownership and earlier history are retained.

Migration 0007 is additive: old copies get empty Comic observations, prior events
get NULL new fields, and preferences get Comics disabled with suggested fields.
The existing Album ID/settings stay stable. Comics has an independent optional
field selection and can be enabled/defaulted alongside Albums. Preview/skip/cancel
never create finds. Setup saves once with the existing lock/revision check.

Downgrade locks the affected tables and refuses any Comic copy, nonempty Comic
observations, retained Comic history or customized Comic preferences. It only
removes unused default columns on disposable data. Never run it as an automatic
live rollback. Before rollout, capture current data and verify an offline restore
and migration rehearsal. After Comic data exists, reverting to an older app/schema
requires an explicit recovery plan; an older app cannot represent the new type.

Independent recovery fixtures include a Comic copy, actual issue/publisher values,
edit history and configured preferences. Backups must compare all rows, migration
head, constraints and media, not merely recreate empty new columns.

Grading, pricing, barcode lookup, automatic series matching, canonical issue
catalogs, custom field installation and imported data are out of scope.
