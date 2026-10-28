# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

RelicRat is for a collector managing physical collectibles on their own infrastructure.
The project progress dashboard is for the project owner reviewing completed work and choosing the next development step.

## Product Purpose

Keep logical catalog items, releases and individual owned copies distinct; preserve identity, provenance and collection data as identification improves.

## Operating Context

The repository uses FastAPI, PostgreSQL, Alembic and Next.js. Development runs on an isolated worker on the owner's NAS. Symphony has completed three supervised implementation tasks; work is handed off through human-reviewed pull requests.

## Capabilities and Constraints

The API supports provisional intake, photos and manual revision-checked reconciliation with retained history. A synthetic recovery rehearsal verifies database and media recovery. Storage assignment, search, a usable web workflow, authentication and production backup support remain unfinished. The current web page is a placeholder.

The requested dashboard must distinguish implemented API behavior, development verification and production readiness. Its source facts are merged repository history, executable code, test evidence and the architecture roadmap. It must identify its snapshot revision and avoid implying live monitoring.

## Evidence on Hand

README.md, docs/architecture/overview.md, docs/harness.md, apps/api/INVENTORY.md and merged PRs #1–5, #7–10, #12 and #14. The last verified application source passed 43 API tests, migration round trips and synthetic recovery with missing/corrupt-media controls.

## Product Principles

- Prefer evidence over implied completion.
- Preserve physical-copy identity, data and history.
- Make the next bounded development step clear.
- Keep the progress report separate from product capability claims.

## Open Decisions

The owner has not specified a permanent dashboard host or visual identity. This task proceeds with a self-contained local report as a reversible implementation choice; it does not set a standing product branding or build-path preference.
