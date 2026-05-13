# 04 — API Conventions

This module defines **cross-cutting rules** for the internal API:
auth posture, error format, pagination, idempotency, locked-state
semantics, the Server-Sent Events stream, the async-job pattern,
and URI versioning.

It does **not** list endpoints. The source of truth for endpoint
shapes — paths, methods, request bodies, response schemas — is
`api/openapi.yaml`, regenerated from the running backend on every
iteration that touches the API (per PROCESS.md §2.2). When you need
to know "what does endpoint X take and return," read OpenAPI. When
you need to know "what's our error format" or "what's the pagination
convention," read this file.

## URL prefix and versioning

All endpoints are under `/api/v1/`. The `/api/v1/` URL prefix is the
**API URI version**, independent of project phases (per ADR-0003).
Breaking changes go to `/api/v2/`. Adding fields, adding endpoints,
and other backwards-compatible changes stay under `/api/v1/`.

The frontend is the only client today, but the contract is designed
as if an external caller would consume it later.

## Authentication

None in the dev phase. Localhost binding is the security boundary.
App-level authentication (passphrase + biometric) is a private-ship
requirement per ADR-0003; the public-ship event hardens it further.
The threat model (`concerns/threat_model.md`) documents this.

## Format

- JSON in, JSON out. UTF-8.
- `Content-Type: application/json` required on requests with bodies.
- Timestamps: ISO 8601 UTC, e.g. `2026-04-27T14:30:00Z`.
- Amounts: integer **satoshis**. Field name always suffixed `_sats`.
  Never floating point.

## Errors

RFC 7807 Problem Details:

```json
{
  "type": "/errors/invalid-descriptor",
  "title": "...",
  "status": 400,
  "detail": "...",
  "instance": "..."
}
```

The `type` field is a path under `/errors/` that uniquely identifies
the error class. New error classes are added as part of the iteration
that introduces them; the registry lives implicitly in the backend's
error definitions and is reflected in OpenAPI's response schemas.

## Pagination

List endpoints accept:

- `?limit=N` — default 50, maximum 200.
- `?cursor=...` — opaque cursor token from the previous response.

Response includes `next_cursor` when more results exist. Absent
`next_cursor` means end of results.

## Idempotency

Mutating endpoints accept an optional `Idempotency-Key` header. If
the same key is replayed, the server returns the original response
without re-executing the operation.

## Locked state

When `SECRETS_BACKEND=encrypted_database` and the app is not yet
unlocked (the user has not entered the passphrase since startup),
**every endpoint except `/api/v1/unlock` and `/api/v1/health` returns
`423 Locked`**. The frontend handles this by routing to the unlock
screen on any 423 response.

## Async jobs

Long-running operations follow this pattern:

```
POST /api/v1/<some-resource>/<some-action>   → 202 Accepted { job_id }
GET  /api/v1/jobs/{job_id}                   → 200 OK       { status, result | error }
```

The frontend polls `GET /jobs/{id}` or subscribes to the SSE stream
filtered to that job. Job status values: `queued`, `running`,
`success`, `failed`, `cancelled`.

## Server-Sent Events stream

The single live-update channel for the frontend. Replaces polling
for fresh data.

```
GET /api/v1/events/stream
  Query: ?topics=<comma-separated patterns>
         (default: all topics)
  Response: text/event-stream

  Each event arrives as:
    event: <topic>
    data: { "topic": "...", "payload": {...}, "timestamp": "..." }
```

The frontend opens this stream once on app load and keeps it open.
The backend forwards bus events through this stream, filtered by the
requested topic patterns. Topic taxonomy lives in
`01_architecture.md` §"Event taxonomy".

Backpressure: the backend buffers up to N events per client and
drops the oldest if a client falls behind. The stream is the **only**
way the frontend receives live updates. There are no polling
fallbacks for live data; if the stream disconnects, the frontend
re-subscribes and refetches state via the regular GET endpoints.

## Flag-gated endpoints

Endpoints that require a feature flag to be enabled return
`403 Forbidden` with `/errors/feature-disabled` when called while
the gating flag is false:

```json
{
  "type": "/errors/feature-disabled",
  "title": "Feature disabled",
  "status": 403,
  "detail": "analysis.blueprint.shown is false."
}
```

This way an external API consumer (in the future) gets a clear
signal rather than a silent empty response.

## Rate limits

None enforced internally (single-user app). External custodial
provider APIs are rate-limited by the worker via ccxt's built-in
throttling. bitcoind RPC is rate-limited by the node's configuration.

## OpenAPI generation and discipline

FastAPI auto-generates `/openapi.json`. The frontend consumes it via
a typed TypeScript client (e.g., `openapi-typescript`). This keeps
the frontend and backend in sync and catches contract drift at build
time.

Per PROCESS.md §2.2, any iteration whose code changes touch the API
surface must regenerate `api/openapi.yaml` as part of that
iteration's acceptance. Drift is a bug, not a chore.
