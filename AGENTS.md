# RelicRat — instructions for coding agents

These instructions apply throughout this repository. Read the relevant files and trace the affected code path before editing. They are inspired by [Ponytail](https://github.com/DietrichGebert/ponytail), but are **RelicRat-specific rules**, not an installation of the Ponytail plugin or its slash commands.

## Objective

Build a trustworthy, self-hosted collectibles inventory and provenance application. Favor the smallest **complete and correct** change that solves the current requirement. Reuse existing code, language features, and framework facilities before adding abstractions or dependencies. Never optimize for line count at the expense of correctness.

## First read

- `README.md` — product goals, setup, and status.
- `docs/architecture/overview.md` — domain invariants and planned boundaries.
- `docs/decisions/` — accepted architecture decisions.
- The tests, migration history, and calling code related to your change.
- `docs/harness.md` — executable checks, evidence, and Symphony pilot boundaries.

Treat architecture documentation as design intent, not proof that a feature is implemented.

## Shared UI, brand, and theming context

- Before UI, brand, or appearance work, read `docs/design/README.md` and its relevant source links. Re-read it when resuming related work; project membership does not synchronize chat transcripts.
- Record decisions that affect another area in that shared brief, with date, status (approved direction, proposed, implemented, or deployed), source, and remaining work. Keep detailed contracts in their existing authoritative files rather than duplicating them.
- Preserve the canonical brand references under `docs/brand/`; assets under `docs/design/proposals/` remain proposals and do not establish production defaults or implemented features.
- Check the current theme contract before styling mockups or changing Appearance. Layout/navigation proposals require separate implementation; theme imports cannot install them.
- Check current files and Git state before edits. If another chat is changing the same area, coordinate scope before overlapping edits. Separate worktrees/branches need the relevant committed changes before they share this context.
- Read relevant chats when context is missing. Send cross-chat messages only when the user explicitly authorizes that communication; these repository instructions do not grant standing messaging permission.

Run API checks with `sh scripts/test-api.sh` on a Docker host, or
`python3 scripts/test-api-remote.py relicrat-worker` from the configured Mac.
Report expected failures and skipped tests explicitly. Never reuse real data.

## Current stack and boundaries

- `apps/api`: Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL.
- `apps/web`: Next.js, React, TypeScript.
- `packages/collection-packs`: future declarative pack schema and examples.
- `compose.yaml`: local development, **not** a hardened production deployment.
- Keep a modular monolith. Domain operations belong in reusable services, not duplicated in routes, jobs, or UI components.
- Avoid introducing a generic repository layer, message bus, queue, cache, or provider framework without a concrete requirement.

## Non-negotiable domain rules

1. **Identity:** catalog item = logical collectible; release = edition/variant; owned copy = one physical object. Do not conflate them.
2. **Provisional intake:** an owned copy may lack catalog/release identification, but must have meaningful user-supplied information or media. Preserve its UUID and history during reconciliation.
3. **Consistency:** a release linked to an owned copy must belong to the same catalog item. Database constraints matter; API validation alone is insufficient.
4. **Ownership vs catalog:** Collection Packs, external catalogs, and AI matches must never silently create or change ownership.
5. **History:** preserve auditability, sales/disposition history, and provenance. Do not hard-delete records as a shortcut.
6. **Storage:** one effective physical location per copy; location nesting must not allow cycles.
7. **Uncertainty:** unknown values are not zero. Label tentative identification and valuation evidence; manual overrides must remain explicit.
8. **Safety:** never expose development services, credentials, user images, or arbitrary filesystem paths. Treat uploads, pack files, external responses, and model output as untrusted.

## How to make a change

1. State the observable behavior and affected domain invariant.
2. Read the current implementation and existing tests; check for a simpler built-in solution.
3. Make the smallest coherent change. Avoid speculative extension points and unrelated refactors.
4. Add a focused test for any branch, parser, database constraint, data loss risk, security boundary, or financial calculation.
5. Run relevant tests and static checks when execution is available. Report exact commands and results; never claim an unrun check passed.
6. Document migration or deployment impact and remaining risks.

If a dependency is warranted, explain what it replaces and why the existing stack cannot do the job reasonably.

## Database and migrations

- Use SQLAlchemy 2.x typed mappings and Alembic revisions; keep model metadata and migrations consistent.
- Prefer database-enforced foreign keys, uniqueness, and check constraints for invariants.
- PostgreSQL-specific behavior (JSONB, triggers, deferrable constraints, transactions, concurrency) requires PostgreSQL integration tests, not only metadata tests.
- Review upgrade **and downgrade** paths on disposable data; avoid destructive migrations without an explicit recovery plan.
- Model `updated_at` behavior deliberately for both ORM and direct SQL writes.
- Be careful with nullable composite foreign keys, concurrent updates, and deferred triggers.
- Do not change existing migration history after it has been deployed; add a corrective migration.

## API, web, and integration guidelines

- FastAPI: validate input at trust boundaries; keep routes thin and errors explicit. Make multi-row domain changes transactional.
- Next.js: default to accessible semantic HTML and existing React patterns. Do not add a component library or state manager just for a single screen.
- Integrations/AI: adapters may suggest matches or values but may not directly overwrite authoritative inventory without a reviewed workflow.
- Uploads and media: constrain types, sizes, paths, and access; never trust client-provided paths or MIME types alone.
- Search: use parameterized queries or validated filters; never execute AI-generated SQL.
- Secrets: use environment variables and ignored local files; never commit credentials or real collection data.

## Pull request expectations

Keep PRs focused and reviewable. Include:

- **Why:** user behavior and invariant affected.
- **What:** the smallest meaningful implementation and important design decisions.
- **Validation:** commands actually run, results, and tests that still need to run.
- **Risks:** migration, concurrency, security, data-loss, or deployment implications.
- **Out of scope:** what was intentionally deferred.

Review changes in context, not just the diff. Prioritize correctness, security, real load, missing tests, and avoidable complexity. If something was not checked, say so.

## Current milestone

The repository is in early development. The first vertical slice is: provisional copy → catalog/release reconciliation → storage assignment → search → backup. Do not claim the slice exists until it is implemented and tested.

## Ponytail compatibility

This file adapts the principles of understanding the code first, reusing existing capabilities, and preserving tests/security while keeping solutions lean. It does **not** install Ponytail, enable hooks, or provide `/ponytail-review` and `/ponytail-audit` commands. Those require a separate supported-agent installation. See the [upstream project](https://github.com/DietrichGebert/ponytail) for optional setup.
