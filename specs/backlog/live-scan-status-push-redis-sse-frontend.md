# Live scan-status push (Redis → SSE → frontend)

- **Captured:** 2026-05-14 (surfaced during Purse wizard hand-test — home page
  showed "Scanning…" indefinitely because the frontend only fetches once on mount
  and the backend never pushes the completed state).
- **Motivation:** The backend already has Redis and an async worker stack.
  Descriptor imports trigger a background chain scan; when the scan completes the
  `scan_status` field updates in the DB. The frontend has no way to know this
  happened — it has to be told. A one-shot page-load fetch is not enough.
- **Sketch:**
    - Backend emits a Redis pub/sub event when scan_status transitions
      (`scanning → synced`, `scanning → error`).
    - A thin SSE endpoint (`GET /api/v1/events/holdings`) streams those events
      to the connected client (same auth as REST calls).
    - Frontend `home/+page.svelte` subscribes to the SSE stream after mount;
      on a `holding.scan_status_changed` event, updates the matching holding in
      the local list reactively without a full refetch.
    - Graceful degradation: if SSE is unavailable (offline, proxy strips
      keep-alive), the page shows the last-known state. A manual pull-to-refresh
      is acceptable fallback.
- **Touches:** backend event emitter (Redis pub/sub hook in the scan worker),
  new SSE endpoint, frontend home page reactive state, auth middleware (SSE
  needs the same Bearer-token guard as REST)
- **Status:** sketched
- **Milestone:** pre-shipping — "Scanning…" that never resolves is a confusing
  UX for any user who imports a wallet and waits for their balance to appear.
  Low implementation cost given Redis is already running.
- **Notes:** The broader "Push-driven categorization workflow" entry (below)
  uses the same SSE channel — coordinate so both events flow through one
  `EventSource` connection, not two. This entry is the simpler first step:
  no push notification, no Capacitor plugin — just a browser SSE stream to
  the already-connected backend.
