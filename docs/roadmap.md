# Roadmap and release progress

Updated November 19, 2026. The goal is a private, single-owner collection server
that a collector can install, use offline, recover, move their data out of and
personalize. A percentage describes the acceptance gates in one bounded theme;
it is not a percentage of every feature RelicRat might eventually support.

## Completed milestones

These are completed batches and their recorded release evidence, not a claim
that every future deployment has been tested or that ongoing maintenance is done.

| Theme | Delivered epics | Completion and evidence |
| --- | --- | --- |
| Collection and physical organization | Title-first copies, photos, catalog/release identity, collection-first search, nested shelves/boxes, QR labels, audits, finding resolution/history and resumable audits | 100% of the approved workflow batches; release PRs through #114. [Collection journey](collection-journey.md), [storage and audits](architecture/overview.md). |
| Read-only agent access | Revocable credential, collection/location/findings API, read-only MCP tools | 100% of the approved read-only scope; [agent guide](../apps/mcp/README.md). Write tools remain outside this milestone. |
| Supported install and recovery foundation | Pinned private Linux Compose, local owner setup, offline collection workflow, independent encrypted replacement restore, backup policy and missed-run alerts | 100% of the v0.1.0 launch gates. [Named release evidence](release-readiness.md), [backup policy](backup-policy.md). New releases still need upgrade verification. |
| Owner data portability | Versioned ZIP export with copy/release IDs, photos, nested boxes and movement history inspectable with standard tools | 100% of the approved export scope; #134. [Owner export](owner-export.md). This is distinct from disaster recovery. |
| Appearance and sharing | Portable Blueprint theme, two-install transfer, persistence, factory reset and upgrade preservation | 100% of the approved sharing scope; #136. [Theme contract](../packages/themes/AUTHORING-PROMPT.md). Layout plugins are not part of themes. |
| CSV import milestone | Reviewed presets including CLZ Games, custom recipes, downloadable agent prompt, Copy prompt and explicit ownership preview | 100% of the approved CSV milestone; #140. [Import recipes](import-recipes.md). No access to the owner's private CSV was needed for synthetic regression. |
| First-time collection setup | Desktop/phone clean-install journey, title/photo intake, CSV preview/import, location assignment and search; phone import shortcut | 100% of the approved batch; #143. [Linux install](linux-compose-install.md), [browser regression](../apps/web/tests/linux-install.browser.mjs). |

Video games are also implemented: title-only ownership, release platform/region/
edition, per-copy contents, optional IGDB title lookup, barcode fallback and a
saved-copy/box check before adding another. External catalog coverage is never
promised for every barcode. See [lookup guide](barcode-lookup.md).

## Release confidence after v0.1.0 — complete

The four gates (roadmap, clean install, populated v0.1.0 upgrade and reviewed
release handoff) are complete. [Release PR #146](https://github.com/bclark/relicrat/pull/146)
remains the owner's main-merge decision. [Dated evidence](release-readiness.md)
keeps the historical test results and limitations separate from deployment.

## Current theme: everyday collection management

The currently approved scope is moving selected physical copies into a box.
Additional everyday-management batches are not yet scoped and do not enter this
percentage. The three acceptance gates below define this bounded milestone.

| Gate | Acceptance | Status |
| --- | --- | --- |
| Select and review | Select copies from a visible collection/search page; show their locations and destination; explicit confirmation on desktop and mobile | Implemented; final browser review pending |
| Safe movement and history | Atomic revision checks, retained per-copy history and identity, no extra events for unchanged copies; reject stale or inactive selections | Implemented; final PostgreSQL checks pending |
| Verified develop handoff | Desktop/mobile success, reload, stale-selection and lost-response regressions; green checks and merge into develop | Pending |

**Current completion: 0% verified (0/3 gates).** Implementation alone does not
close a gate. See the [bulk-move contract](bulk-copy-moves.md) and
[PR #147](https://github.com/bclark/relicrat/pull/147). Main merge and deployment
remain separate owner actions. The earlier release-confidence milestone remains
100% complete.

## After this theme

1. Gather first-run feedback from a collector following the published guide;
   fix observed installation/import/browsing friction in a bounded batch.
2. Choose the next concrete collection problem from that feedback. Improve
   finding and managing existing copies before adding another intake pathway.
3. Keep upgrades, recovery and backup-alert drills as recurring release checks.
   Capacity and failed off-site copies remain operational work, not new features.

Checklist packs, including the proposed 1988 TMNT pack, are **deferred by the
owner**. Household roles, public hosting, native clients, writable agents and a
plugin marketplace have no approved implementation milestone. Do not silently
add them to the denominator of a completed theme.
