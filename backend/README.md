# tallykeep — backend

FastAPI + SQLAlchemy 2 + Alembic + RQ. Single Python codebase, two entry points:

- `tallykeep.main` — HTTP API and SSE.
- `tallykeep.worker` — listeners, schedulers, subscribers (per spec module 01).

Run via the top-level Docker Compose stack; not intended to be run directly on the host.
