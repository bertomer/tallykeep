/**
 * Security Health store — SSE-driven item list.
 *
 * Subscribes to the three security_health.* SSE topics and maintains the
 * current list of open items. Exposes:
 *   openItems       — all open SecurityHealthItems, sorted critical-first
 *   criticalCount   — count of open items with severity='critical' (drives the badge)
 *   appLevelOpen    — open items with holding_id=null (surfaced on Home)
 *
 * Call init() once per app session after auth is confirmed. Call close() on
 * app shutdown. Re-calling init() while already connected is a no-op for SSE
 * but always re-fetches REST to sync current state.
 *
 * Call refresh() after any user-initiated resolve/revive so the UI updates
 * immediately without relying on SSE timing.
 */

export interface SecurityHealthItem {
  id: string;
  item_type: string;
  holding_id: string | null;
  state: string;
  severity: string;
  created_at: string;
  resolved_at: string | null;
  dismissal_reason: string | null;
  raw_context: Record<string, unknown>;
}

function createSecurityHealthStore() {
  let openItems = $state<SecurityHealthItem[]>([]);
  let _eventSource: EventSource | null = null;
  let _initialized = false;
  let _serverUrl = '';
  let _credential = '';

  const criticalCount = $derived(
    openItems.filter(i => i.severity === 'critical').length
  );

  const appLevelOpen = $derived(
    openItems.filter(i => i.holding_id === null)
  );

  function _isValid(item: unknown): item is SecurityHealthItem {
    if (!item || typeof item !== 'object') return false;
    const i = item as Record<string, unknown>;
    return (
      typeof i.id === 'string' && i.id.length > 0 &&
      typeof i.item_type === 'string' && i.item_type.length > 0 &&
      typeof i.severity === 'string' && i.severity.length > 0 &&
      typeof i.state === 'string' && i.state.length > 0
    );
  }

  function _sortItems(items: SecurityHealthItem[]): SecurityHealthItem[] {
    // Deduplicate by id before sorting — guards against concurrent REST/SSE races.
    const seen = new Set<string>();
    const unique = items.filter(i => {
      if (seen.has(i.id)) return false;
      seen.add(i.id);
      return true;
    });
    return unique.sort((a, b) => {
      const sevOrder = (s: string) => s === 'critical' ? 0 : s === 'warning' ? 1 : 2;
      const sd = sevOrder(a.severity) - sevOrder(b.severity);
      if (sd !== 0) return sd;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }

  async function _fetchOpenItems(): Promise<void> {
    if (!_serverUrl || !_credential) return;
    try {
      const resp = await fetch(`${_serverUrl}/api/v1/security_health/items?state=open`, {
        headers: { Authorization: `Bearer ${_credential}` },
      });
      if (resp.ok) {
        const data: unknown = await resp.json();
        if (!Array.isArray(data)) return;
        const items = (data as unknown[]).filter(_isValid);
        openItems = _sortItems(items);
      }
    } catch { /* offline — keep current state, SSE will fill in */ }
  }

  async function init(serverUrl: string, credential: string): Promise<void> {
    _serverUrl = serverUrl;
    _credential = credential;

    // Always re-fetch REST so the list is fresh after unlock / backend restart.
    await _fetchOpenItems();

    // SSE subscription is set up only once.
    if (_initialized) return;
    _initialized = true;

    const tokenParam = credential ? `&token=${encodeURIComponent(credential)}` : '';
    const topics = 'security_health.item_added,security_health.item_resolved,security_health.item_revived';
    const url = `${serverUrl}/api/v1/events/stream?topics=${encodeURIComponent(topics)}${tokenParam}`;
    _eventSource = new EventSource(url);

    _eventSource.addEventListener('security_health.item_added', (evt: MessageEvent) => {
      try {
        const item: unknown = JSON.parse(evt.data);
        if (_isValid(item) && !openItems.find(i => i.id === item.id)) {
          openItems = _sortItems([...openItems, item]);
        }
      } catch { /* malformed payload */ }
    });

    _eventSource.addEventListener('security_health.item_resolved', (evt: MessageEvent) => {
      try {
        const item: unknown = JSON.parse(evt.data);
        if (_isValid(item)) {
          openItems = openItems.filter(i => i.id !== item.id);
        }
      } catch { /* malformed payload */ }
    });

    _eventSource.addEventListener('security_health.item_revived', (evt: MessageEvent) => {
      try {
        const item: unknown = JSON.parse(evt.data);
        if (_isValid(item) && !openItems.find(i => i.id === item.id)) {
          openItems = _sortItems([...openItems, item]);
        }
      } catch { /* malformed payload */ }
    });
  }

  function close(): void {
    _eventSource?.close();
    _eventSource = null;
    _initialized = false;
  }

  /** Re-fetch open items from REST. Call after user-initiated resolve/revive for immediate feedback. */
  async function refresh(): Promise<void> {
    await _fetchOpenItems();
  }

  return {
    get openItems() { return openItems; },
    get criticalCount() { return criticalCount; },
    get appLevelOpen() { return appLevelOpen; },
    init,
    close,
    refresh,
  };
}

export const securityHealth = createSecurityHealthStore();
