# ADR 0001: Self-hosted modular monolith

**Status:** Accepted

## Context

RelicRat is a self-hosted physical collectibles inventory system. A single-owner deployment needs reliable local persistence, flexible domain models, background jobs, and an approachable development setup without unnecessary operational complexity.

## Decision

- Use a modular monolith with a Python FastAPI API and shared domain services.
- Use PostgreSQL as the authoritative datastore.
- Use SQLAlchemy 2.x for persistence and Alembic for versioned migrations.
- Use Next.js/React/TypeScript for a responsive PWA.
- Use Docker Compose for local development and initial NAS deployment.
- Store media on host-mounted filesystem storage; use a separate worker for slow tasks when introduced.
- Keep AI, catalog, and marketplace integrations behind replaceable adapters.

## Consequences

A single codebase simplifies development and deployment. Modules must retain explicit boundaries to avoid tightly coupled domain logic. Background jobs, authentication, backups, and media storage require further implementation before real-world deployment.

## Non-goals

This decision does not prescribe a specific queue, authentication provider, cloud hosting service, or production backup implementation.
