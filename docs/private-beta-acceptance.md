# Phase one: dependable private beta

Status: acceptance in progress. Automated checks establish behavior; they do not
establish that the owner finds it clear on a physical phone. Phase one remains
open until the owner completes the trial below and confirmed blockers are fixed.

## Boundaries

Test Albums, Comics, Movies and a custom collection through the existing
interface. Collection definitions and lookup results never create ownership.
Each physical copy retains its UUID, photos, location and history after edits.
Unknown values remain unknown. Unconfirmed writes require inspection before
another attempt; a failed read must not look like an empty collection.

Use synthetic records and isolated disposable services for automation. Never use
an owner's inventory, CSV exports, images, credentials or recovery restores as
fixtures. Keep receipts and screenshots private. Review and merge precede rollout.

## Acceptance coverage

| Area | Automated evidence | Owner acceptance remaining |
| --- | --- | --- |
| Sign-in and privacy | Guest denial, protected media, rejected passwords, autofill, logout, origin checks and no-JavaScript password handling | Sign in and out on the actual phone; confirm password-manager behavior |
| Capture and inspect | Title-only entry, artist-first Albums, Comics issue/publisher, Movies format/studio, custom fields, explicit saves and retained identity | Add one ordinary item of each type without coaching; judge labels and next actions |
| Find and browse | Large imports, whole-collection groups, paging, search, type/storage filters and stale-read protection | Locate a known item, switch type and storage, then return to the same draft |
| Edit and organize | Personal details, catalog/release consistency, independent copies, photos, nested storage and retained histories | Correct a detail, add a photo and move a copy; verify the result after refresh |
| Phone and keyboard | Narrow viewports, long text, larger text, theme checks, focus/Back navigation and draft preservation | Real touch targets, keyboard/autofill, scrolling and portrait/landscape comfort |
| Scan and lookup | Synthetic camera decoder, denied permissions, stopped tracks, leading zeros, provider failures, optional covers and reviewed field application | Real camera focus/lighting and recognition of a physical barcode; review before saving |
| Import and recovery | CLZ/Discogs/Blu-ray presets, large synthetic CSVs, invalid rows, exact-file duplicates, storage mapping and uncertain responses | Review an import preview and source evidence; no need to import the same real export again |
| Custom collection lifecycle | Prompt/JSON validation, empty activation, field controls, explicit checklist qualification, export and independent reimport | Export one definition and import under a new name; original figures/progress and controls must remain independent |
| Failure safety | Validation errors, stale revisions, unavailable services/providers, retry decisions and retained drafts | Report confusing messages encountered naturally; do not deliberately interrupt the private service |
| Data integrity | PostgreSQL API integration suite and migration upgrade/downgrade checks on disposable data | Existing operator recovery checks remain separate; no production-ready claim |

Tests live under `apps/web/tests/*.browser.mjs` and `apps/api/tests/`.
The [harness guide](harness.md) records commands, results and limits of each run.
A passing synthetic provider test does not certify external catalog coverage,
service uptime or a particular physical release.

## Short owner trial

After the reviewed release is deployed:

1. On your phone, sign in and choose Albums. Enter an artist and title, review,
   and save once. Open the saved item and confirm its details.
2. Add a Comic and a Movie using just a recognizable title. Add optional details
   afterward. Everything except the title should remain optional.
3. Scan an item you have in hand. Check the proposed match and optional cover.
   If lookup fails or has no match, keep the barcode and enter details manually.
4. Find a saved copy through search, then through its collection type and storage.
   Open it, correct a detail, attach a photo and assign a location. Refresh and
   confirm the same copy retains those changes.
5. Start another draft; switch browsing filters, open a saved copy and go Back.
   Confirm the unfinished draft remains. Try the same navigation with a keyboard
   on a larger screen.
6. In a custom collection, add a figure from a missing checklist entry. Confirm
   that saving ownership and marking a goal collected remain separate decisions.
7. Export the custom definition and import it as a new collection under another
   name. It should start empty. Changing its field controls must not change the
   original collection or its figures/progress.
8. Sign out. Sign back in and confirm the saved work remains.

For anything awkward, record the action, what you expected and what happened.
A screenshot can help; omit passwords and sensitive collection details from
public issues. "Passed", "confusing" or "failed" is enough for each step.

## Exit criteria

- Relevant automated suites pass with expected skips and limitations stated.
- Owner completes the cross-type trial on a physical phone and a larger screen.
- Confirmed data-loss, privacy, uncertain-save and blocked-workflow defects are
  resolved and covered by focused regressions.
- Remaining nonblocking friction is recorded with a concrete next action.
- Reviewed changes are merged and deployed with the existing recovery procedure.

Later features and general production hardening do not become complete merely
because this private-beta acceptance passes.
