<!--
  Security Health dashboard — ADR-0019.
  Active tab: SSE-driven open items (from securityHealth store).
  History tab: fetched on demand from REST.
  Principles-ack items open a bottom-sheet; per-Holding items deep-link.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { securityHealth, type SecurityHealthItem } from '$lib/stores/security_health.svelte';
  import { secureStorage } from '$lib/native-bridge';
  import BottomNav from '$lib/components/BottomNav.svelte';

  let serverUrl = $state('');
  let activeTab = $state<'active' | 'history'>('active');
  let holdingNames = $state<Record<string, string>>({});
  let historyItems = $state<SecurityHealthItem[]>([]);
  let historyLoaded = $state(false);
  let historyLoading = $state(false);

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }

    serverUrl = (await secureStorage.get('server_url')) ?? '';
    const credential = auth.deviceCredential ?? '';
    if (serverUrl && credential) {
      securityHealth.init(serverUrl, credential);
    }

    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/summary/global`, {
        headers: authHeaders(),
      });
      if (resp.ok) {
        const data = await resp.json();
        const names: Record<string, string> = {};
        for (const h of (data.holdings ?? [])) names[h.holding_id] = h.name;
        holdingNames = names;
      }
    } catch { /* offline */ }
  });

  async function loadHistory() {
    if (historyLoaded || historyLoading) return;
    historyLoading = true;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/security_health/items?state=history`, {
        headers: authHeaders(),
      });
      if (resp.ok) {
        historyItems = await resp.json();
      }
    } catch { /* offline */ }
    historyLoaded = true;
    historyLoading = false;
  }

  function switchTab(tab: 'active' | 'history') {
    activeTab = tab;
    if (tab === 'history') loadHistory();
  }

  function handleItemTap(item: SecurityHealthItem) {
    if (item.item_type === 'principles_ack') {
      goto('/home?open=principles');
    } else if (item.holding_id) {
      goto(`/holding/${item.holding_id}?tab=settings`);
    }
  }

  async function reviveItem(item: SecurityHealthItem) {
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/security_health/items/${item.id}/revive`,
        { method: 'POST', headers: authHeaders() },
      );
      if (resp.ok) {
        historyItems = historyItems.filter(i => i.id !== item.id);
        await securityHealth.refresh();
      }
    } catch { /* ignore */ }
  }

  function _parseDate(isoStr: string | null | undefined): Date {
    // Python emits 6-digit microseconds (e.g. 2026-05-25T08:34:33.123456+00:00).
    // ECMAScript Date only guarantees 3-digit milliseconds; truncate the extra digits.
    if (!isoStr) return new Date(NaN);
    return new Date(isoStr.replace(/(\.\d{3})\d+/, '$1'));
  }

  function relativeDate(isoStr: string | null | undefined): string {
    const d = _parseDate(isoStr);
    if (isNaN(d.getTime())) return '';
    const diffDays = Math.floor((Date.now() - d.getTime()) / 86_400_000);
    if (diffDays <= 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    const diffWeeks = Math.floor(diffDays / 7);
    return `${diffWeeks} week${diffWeeks > 1 ? 's' : ''} ago`;
  }

  function openedDate(isoStr: string | null | undefined): string {
    const d = _parseDate(isoStr);
    if (isNaN(d.getTime())) return '';
    const diffDays = Math.floor((Date.now() - d.getTime()) / 86_400_000);
    if (diffDays <= 0) return 'Opened today';
    if (diffDays === 1) return 'Opened yesterday';
    return `Opened ${diffDays} days ago`;
  }

  function itemTitle(item: SecurityHealthItem): string {
    if (item.item_type === 'seed_backup') return 'Back up your recovery phrase';
    if (item.item_type === 'missing_signing_metadata') return 'Missing derivation metadata';
    if (item.item_type === 'principles_ack') return 'Acknowledge how TallyKeep works';
    return item.item_type;
  }

  function holdingLabel(item: SecurityHealthItem): string {
    if (!item.holding_id) return '';
    return holdingNames[item.holding_id] ?? '';
  }

  function itemSummary(item: SecurityHealthItem): string {
    const name = (item.raw_context?.holding_name as string) ?? '';
    if (item.item_type === 'seed_backup') {
      return `${name}${name ? ' · ' : ''}without a backup, losing this phone loses the funds`;
    }
    if (item.item_type === 'missing_signing_metadata') {
      return `${name}${name ? ' · ' : ''}hardware wallet may refuse to sign without it`;
    }
    if (item.item_type === 'principles_ack') {
      return 'You skipped the principles at setup';
    }
    return '';
  }

  function histVerb(item: SecurityHealthItem): string {
    if (item.state === 'resolved_by_fix') return 'Fixed';
    if (item.state === 'dismissed_intentional') return 'Acknowledged as intentional';
    if (item.state === 'acknowledged') return 'Acknowledged';
    return item.state;
  }

  function histVerbClass(item: SecurityHealthItem): string {
    if (item.state === 'resolved_by_fix') return 'fixed';
    if (item.state === 'dismissed_intentional') return 'intentional';
    return 'acknowledged';
  }

  function histSummary(item: SecurityHealthItem): string {
    const name = (item.raw_context?.holding_name as string) ?? '';
    const reason = item.dismissal_reason ?? '';
    if (item.item_type === 'seed_backup') {
      return `${name}${name ? ' · ' : ''}you confirmed you saved it`;
    }
    if (item.item_type === 'missing_signing_metadata') {
      const suffix = reason ? `"${reason}"` : 're-exported with full origin';
      return `${name}${name ? ' · ' : ''}${suffix}`;
    }
    if (item.item_type === 'principles_ack') {
      return 'You read and accepted how TallyKeep works';
    }
    return '';
  }

  const USER_ATTESTED_STATES = new Set(['dismissed_intentional']);
</script>

<div class="phone-screen safe-top safe-bottom">

  <div class="app-bar">
    <a href="/home" class="app-bar-back" aria-label="Back">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="15 18 9 12 15 6"/>
      </svg>
    </a>
    <span class="app-bar-title">Security health</span>
    <a href="/settings" class="app-bar-gear" aria-label="Settings">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </svg>
    </a>
  </div>

  <div class="tab-strip" role="tablist">
    <button
      class="tab-btn"
      class:active={activeTab === 'active'}
      role="tab"
      aria-selected={activeTab === 'active'}
      onclick={() => switchTab('active')}
    >Active</button>
    <button
      class="tab-btn"
      class:active={activeTab === 'history'}
      role="tab"
      aria-selected={activeTab === 'history'}
      onclick={() => switchTab('history')}
    >History</button>
  </div>

  <!-- Active tab -->
  {#if activeTab === 'active'}
    <div class="scroll-area">
      {#if securityHealth.openItems.length === 0}
        <div class="empty-panel">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <div class="empty-title">You're all caught up</div>
          <div class="empty-body">This page shows anything TallyKeep wants your attention on. Nothing open right now.</div>
        </div>
      {:else}
        <div class="list-label">{securityHealth.openItems.length} open</div>
        <div class="item-list">
          {#each securityHealth.openItems as item (item.id)}
            <button
              class="item-row {item.severity}"
              type="button"
              onclick={() => handleItemTap(item)}
            >
              <span class="sev-dot {item.severity}" aria-hidden="true"></span>
              <span class="item-body">
                <span class="item-title">{itemTitle(item)}</span>
                {#if holdingLabel(item)}<span class="item-holding">{holdingLabel(item)}</span>{/if}
                <span class="item-summary">{itemSummary(item)}</span>
                <span class="item-date">{openedDate(item.created_at)}</span>
              </span>
              <span class="item-chevron" aria-hidden="true">›</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- History tab -->
  {#if activeTab === 'history'}
    <div class="scroll-area">
      {#if historyLoading}
        <div class="empty-panel">
          <div class="empty-body">Loading…</div>
        </div>
      {:else if historyItems.length === 0}
        <div class="empty-panel">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <div class="empty-title">No history yet</div>
          <div class="empty-body">Resolved security items will appear here.</div>
        </div>
      {:else}
        <div class="list-label">Resolved</div>
        <div class="hist-list">
          {#each historyItems as item (item.id)}
            <div class="hist-row">
              <div class="hist-meta-line">
                <span class="hist-verb {histVerbClass(item)}">{histVerb(item)}</span>
                <span class="hist-date">{relativeDate(item.resolved_at ?? item.created_at)}</span>
              </div>
              <span class="hist-title">{itemTitle(item)}</span>
              {#if holdingLabel(item)}<span class="hist-holding">{holdingLabel(item)}</span>{/if}
              <span class="hist-summary">{histSummary(item)}</span>
              {#if USER_ATTESTED_STATES.has(item.state)}
                <button class="hist-revive" type="button" onclick={() => reviveItem(item)}>
                  Move back to open
                </button>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <BottomNav active="security" criticalCount={securityHealth.openItems.length} />

</div>

<style>
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }
  .app-bar-back {
    width: 44px;
    height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    cursor: pointer;
    padding: 0;
    color: var(--color-text);
    text-decoration: none;
  }
  .app-bar-back svg { width: 24px; height: 24px; }
  .app-bar-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    flex: 1;
    text-align: center;
    margin: 0 -44px 0 0;
  }
  .app-bar-gear {
    width: 44px;
    height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    cursor: pointer;
    padding: 0;
    color: var(--color-text-muted);
    text-decoration: none;
  }
  .app-bar-gear svg { width: 24px; height: 24px; }

  /* Tab strip */
  .tab-strip {
    flex-shrink: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }
  .tab-btn {
    padding: var(--space-3) 0;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    background: transparent;
    border: 0;
    cursor: pointer;
    color: var(--color-text-dim);
    font-family: inherit;
    position: relative;
  }
  .tab-btn.active {
    color: var(--color-primary-strong);
    font-weight: var(--font-weight-semibold);
  }
  .tab-btn.active::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 25%;
    right: 25%;
    height: 2px;
    background: var(--color-primary);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-3) 0 var(--space-4);
    padding-bottom: var(--mobile-bottom-nav);
  }

  /* Active tab — item list */
  .list-label {
    padding: 0 var(--space-4) var(--space-2);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .item-list {
    margin: 0 var(--space-4) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }
  .item-row {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    width: 100%;
    border: 0;
    border-bottom: 1px solid var(--color-border);
    padding: var(--space-3) var(--space-4);
    font-family: inherit;
    text-align: left;
    cursor: pointer;
    gap: var(--space-3);
  }
  .item-row:last-child { border-bottom: 0; }
  .item-row.critical { background: var(--color-danger-soft); color: var(--color-danger-text-on-soft); }
  .item-row.warning  { background: var(--color-warning-soft); color: var(--color-warning-text-on-soft); }
  .sev-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .sev-dot.warning  { background: var(--color-warning); }
  .sev-dot.critical { background: var(--color-danger); }
  .item-body {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .item-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: inherit;
    line-height: var(--line-height-tight);
  }
  .item-summary {
    font-size: var(--font-size-xs);
    color: inherit;
    opacity: 0.75;
    line-height: var(--line-height-tight);
  }
  .item-holding {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: inherit;
    opacity: 0.9;
    line-height: var(--line-height-tight);
  }
  .item-date {
    font-size: 11px;
    color: inherit;
    opacity: 0.6;
    line-height: var(--line-height-tight);
    margin-top: 2px;
  }
  .item-chevron {
    color: inherit;
    opacity: 0.6;
    font-size: 18px;
    line-height: 1;
  }

  /* Empty state */
  .empty-panel {
    margin: var(--space-7) var(--space-4) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-6) var(--space-4);
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
  }
  .empty-panel svg {
    width: 40px;
    height: 40px;
    color: var(--color-success);
  }
  .empty-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .empty-body {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 240px;
  }

  /* History tab */
  .hist-list {
    margin: 0 var(--space-4) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }
  .hist-row {
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .hist-row:last-child { border-bottom: 0; }
  .hist-meta-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-2);
  }
  .hist-verb {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .hist-verb.fixed       { color: var(--color-success-text-on-soft); }
  .hist-verb.acknowledged { color: var(--color-text-muted); }
  .hist-verb.intentional  { color: var(--color-text-muted); }
  .hist-date {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
  }
  .hist-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
  }
  .hist-holding {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    line-height: var(--line-height-tight);
  }
  .hist-summary {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    line-height: var(--line-height-tight);
  }
  .hist-revive {
    background: transparent;
    border: 0;
    padding: 0;
    margin-top: 4px;
    font-size: var(--font-size-xs);
    color: var(--color-primary-strong);
    cursor: pointer;
    align-self: flex-start;
    font-family: inherit;
  }

</style>
