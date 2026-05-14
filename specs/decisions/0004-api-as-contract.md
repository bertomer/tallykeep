# ADR-0004 — Backend OpenAPI is the API contract

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during consolidation merge
- **Migrated from:** `pre-implementation.md` Decided item
  `api-surface-canonical-source` (2026-05).

## Context

The original spec carried module 04 (`04_api_surface.md`) as a
hand-written enumeration of every endpoint. The running FastAPI
backend already emitted OpenAPI automatically. Two parallel
sources of truth for the API surface accumulated drift the moment
either side moved.

## Decision

1. The OpenAPI document exported from the running FastAPI backend
   (`api/openapi.yaml`) is the single source of truth for endpoint
   shapes — paths, methods, request and response schemas, SSE
   stream descriptors, error registry.
2. Module `04_api_conventions.md` keeps only cross-cutting rules
   that don't fit OpenAPI: auth posture, error format, pagination
   convention, idempotency, locked-state semantics, SSE stream
   pattern, async-job pattern, URI versioning.
3. Module `04_api_surface.md` retires to `archive/`.
4. Manual edits to `api/openapi.yaml` are forbidden. If it's
   wrong, the backend is wrong; fix it there, then regenerate.
5. Any iteration whose code touches an endpoint, schema, SSE
   event, error type, or locked-state behavior **must** regenerate
   `api/openapi.yaml` as part of that iteration's acceptance. The
   iteration is not done until the file is up to date and
   committed in the same change. Drift is a bug, not a chore.

## Consequences

- UI specs reference endpoint shapes by pointing at
  `api/openapi.yaml`; they never restate them.
- The "iteration is done when…" checklist in PROCESS.md §4.6
  enforces this mechanically; the per-iteration sanity sweep
  catches any drift that slipped past commit time.
- Reviewers reject iterations that landed backend changes without
  regenerating the file.

## Affected files

- `api/openapi.yaml` — canonical, regenerated per iteration
- `api/README.md` — describes the regen procedure
- `04_api_conventions.md` — cross-cutting rules only
- `archive/04_api_surface.md` — historical
- `PROCESS.md §4.2` and `§4.6` — enforcement
