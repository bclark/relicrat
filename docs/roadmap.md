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

## Current theme: release confidence after v0.1.0

Four acceptance gates define this maintenance theme. Mark a gate verified only
with an executed check and a named source/CI run. Main merges and deployments
remain the owner's decision.

| Gate | Acceptance | Status |
| --- | --- | --- |
| Roadmap | Separate completed milestones, maintenance and deferred work; link evidence | Updated in this batch |
| Clean install | Empty Ubuntu engine, private Compose, blocked app egress; desktop and phone add/photo/import/move/find, then recreation | Passed in [PR #145 checks](https://github.com/bclark/relicrat/pull/145/checks) and on physical Android; [dated evidence](release-readiness.md) |
| Upgrade | Start at immutable v0.1.0 `373873e58e495e09c7e064134909b66266c9692e`, populate on both layouts, take backup, migrate to candidate; preserve original UUIDs, photos, boxes and histories, then use new features | Passed in [PR #145 checks](https://github.com/bclark/relicrat/pull/145/checks) and on physical Android; [dated evidence](release-readiness.md) |
| Release handoff | Review fixes, green checks and a reviewable release handoff with limitations; main merge/deployment stay manual | Prepared in [PR #145](https://github.com/bclark/relicrat/pull/145); release checks must remain green before owner merge |

**Current completion: 100% (4 of 4 gates prepared and verified).** This is the
bounded release-confidence theme, not a claim that maintenance is finished.
Release approval, main merge, tagging and deployment remain separate owner actions.

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
