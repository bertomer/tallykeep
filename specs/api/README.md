# Backend API contract

This directory holds the **frozen, as-built** backend API contract.
It is generated from the running backend; it is not authored by hand.

## File

- `openapi.yaml` — OpenAPI 3.x export of every endpoint
  exposed by the FastAPI backend, including request/response schemas
  and the SSE stream descriptor.

## How to regenerate

FastAPI emits OpenAPI automatically. With the backend running:

```bash
curl http://localhost:8000/openapi.json \
  | python -m json.tool \
  > openapi.json

# or if you want YAML
python -c "import json, yaml, sys; \
  yaml.safe_dump(json.load(sys.stdin), sys.stdout, sort_keys=False)" \
  < openapi.json \
  > openapi.yaml
```

(Adjust port and host as appropriate.)

The exact command should be captured in the backend repo's README so
this is reproducible by any agent.

## Status

The file should be present at `openapi.yaml` (or `.json`).
If absent, regenerate as in the previous section before any UI work
starts.

## Working rules

- This file is the **contract** for UI work. UI specs consume it; UI
  specs do not redefine endpoint shapes.
- **Currency is mandatory.** Any code change touching the API
  surface (new endpoint, schema change, removed field, SSE event
  change) must be accompanied by regeneration of this file in the
  closeout commit of that iteration. Drift between OpenAPI and
  code is a bug. The coding agent is responsible.
- **Regeneration timing.** Regen happens during iteration closeout
  (`PROCESS.md §2.7` stage 5), **after** Rémy's smoke-test +
  Swagger validation gives the explicit greenlight — not while the
  code is still being iterated. Regenerating mid-iteration captures
  half-built state; regenerating after greenlight captures the
  shipped state.
- When work needs a backend change, the change is listed as part
  of the relevant iteration in `../next_iteration.md` (per ADR-0002,
  replacing the older `UI/backend_deltas.md` proposal).
- The iteration is not complete until the OpenAPI matches the code.
- Manual edits to `openapi.yaml` are forbidden. If it's
  wrong, the backend is wrong; fix it there.
