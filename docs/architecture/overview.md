# RelicRat architecture overview

**Status:** Design baseline, not an implemented feature inventory.

## Mission

A self-hosted system for managing physical collectibles, including comics, trading cards, records, books, games, toys, LEGO, pins, and user-defined categories.

## Domain invariants

1. A **catalog item** represents a logical collectible; a **release** represents a physical variant; an **owned copy** represents one physical object.
2. An owned copy can be provisional without a canonical match. Reconciliation must preserve its UUID and history.
3. Identification state, ownership/disposition state, listing state, and deletion state are independent.
4. Collection Packs define catalogs, metadata, and completion rules, **not** ownership.
5. Multiple Collection Packs may reference one canonical catalog identity.
6. Manual collections may overlap; a copy has only one effective current physical storage location.
7. External providers and AI produce evidence and suggestions, never silent authoritative inventory changes.
8. Unknown valuations must remain unknown rather than zero; manual overrides take precedence.
9. Audit history, soft deletion, conflict-aware undo, and reliable backup/restore protect user data.

## Modules and evolution

- **Foundation:** catalog, inventory, media, storage, search, audit, backup.
- **Collection intelligence:** packs, completion goals, ingestion, AI identification.
- **Commerce:** acquisitions, valuations, listings, sales, wishlists, notifications.
- **Operations:** jobs, integration adapters, authentication, configuration.

## First vertical slice

Create a provisional owned copy → link it to a canonical catalog item and optional release → assign a storage location → find it through search → back up its database record and media.

The current implementation includes six foundational tables, provisional-copy
creation/list/retrieval, manual revision-checked reconciliation with retained
history, photo upload/list/download endpoints, nested storage locations and
revision-checked copy movement with retained history. The web app
remains a placeholder. Search and production
backup/restore are not implemented. The synthetic recovery rehearsal is development
verification only. See the [inventory API contract](../../apps/api/INVENTORY.md). See [the harness guide](../harness.md) for
executable API verification and its known limitations.

## Planned key entities

`categories`, `catalog_items`, `releases`, `owned_copies`, `media_assets`, `storage_locations`; later `collection_packs`, `pack_versions`, `collections`, `completion_goals`, `acquisitions`, `valuation_estimates`, `sale_offers`, `wishlist_entries`, `operations`, `audit_events`, `backup_executions`.

## Implementation principles

Use UUID primary keys, explicit foreign keys, timestamps, migration reviews, and transactional domain operations. Define uniqueness and reconciliation rules per category before implementing automated matching. Start with PostgreSQL full-text and relational search; do not introduce a separate search cluster prematurely.

See [ADR 0001](../decisions/0001-modular-monolith.md) for stack decisions and the root [README](../../README.md) for setup and roadmap.
