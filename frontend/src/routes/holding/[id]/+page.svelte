<!--
  Account detail — /holding/[id]
  Mockup contract (all validated 2026-05-17):
    mobile_account_detail_operations_populated.html
    mobile_account_detail_operations_empty.html
    mobile_account_detail_settings.html
    mobile_account_detail_remove_confirm.html
    mobile_account_detail_connection_error.html
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { preferences } from '$lib/stores/preferences.svelte';
  import { secureStorage } from '$lib/native-bridge';
  import BottomNav from '$lib/components/BottomNav.svelte';

  // ─── Types ───────────────────────────────────────────────────────────────────

  interface LedgerEntry {
    id: string;
    provider_entry_id: string;
    kind: string;
    asset: string;
    amount_sats: number;
    status: string;
    timestamp: string;
  }

  interface AccountDetail {
    provider_id: string;
    provider_kind: string;
    adapter_id: string;
    display_name: string;
    connection_status: string;
    last_polled_at: string | null;
    last_error: string | null;
    last_known_balance_sats: number | null;
    non_btc_balances: Record<string, string>;
    polling_interval_seconds: number;
    observation_key_last_four: string | null;
    ledger_entries: LedgerEntry[];
    ledger_has_more: boolean;
  }

  interface HoldingSnapshot {
    id: string;
    holding_type: string;
    name: string;
    created_at: string;
    account_detail: AccountDetail | null;
  }

  // ─── State ───────────────────────────────────────────────────────────────────

  let holdingId = $derived($page.params.id ?? '');
  let serverUrl = $state('');

  let snapshot = $state<HoldingSnapshot | null>(null);
  let detail = $derived(snapshot?.account_detail ?? null);

  let activeTab = $state<'operations' | 'settings'>('operations');

  // Connection-error toast
  let toastDismissed = $state(false);
  let toastVisible = $derived(
    !toastDismissed &&
    !!detail &&
    (detail.connection_status === 'unreachable' || detail.connection_status === 'auth_failed')
  );

  // Toast auto-dismiss after ~5s on each appearance
  $effect(() => {
    if (!toastVisible) return;
    const t = setTimeout(() => { toastDismissed = true; }, 5000);
    return () => clearTimeout(t);
  });

  // Remove-confirm bottom sheet
  let showRemoveConfirm = $state(false);
  let removing = $state(false);

  // Polling inline picker
  let showPollingPicker = $state(false);
  let pollingUpdating = $state(false);

  // Rename inline
  let showRenameInput = $state(false);
  let renameValue = $state('');
  let renaming = $state(false);

  // Freshness ticker
  let now = $state(Date.now());
  let tickInterval: ReturnType<typeof setInterval> | null = null;

  // SSE cleanup
  let eventSource: EventSource | null = null;

  // Force-poll state (status card spinner)
  let refreshing = $state(false);

  // ─── Derived ─────────────────────────────────────────────────────────────────

  function dotClass(status: string): string {
    if (status === 'healthy') return 'status-dot--healthy';
    if (status === 'degraded') return 'status-dot--degraded';
    if (status === 'unreachable' || status === 'auth_failed') return 'status-dot--unreachable';
    return 'status-dot--healthy';
  }

  function statusLabel(status: string): string {
    if (status === 'healthy') return 'Connected';
    if (status === 'degraded') return 'Degraded';
    if (status === 'unreachable') return 'Unreachable';
    if (status === 'auth_failed') return 'Auth failed';
    return 'Unknown';
  }

  function freshness(polledAt: string | null): string {
    if (!polledAt) return '';
    const diffMs = now - new Date(polledAt).getTime();
    const secs = Math.floor(diffMs / 1000);
    if (secs < 60) return 'Updated just now';
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `Updated ${mins} min ago`;
    const hrs = Math.floor(mins / 60);
    return `Updated ${hrs}h ago`;
  }

  function formatSats(n: number): string {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function formatBtc(sats: number): string {
    return (sats / 1e8).toFixed(8).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function formatAmount(sats: number): string {
    return preferences.unit === 'sats' ? formatSats(Math.abs(sats)) : formatBtc(Math.abs(sats));
  }

  function amountClass(sats: number): string {
    if (sats > 0) return 'activity-amount--positive';
    if (sats < 0) return 'activity-amount--negative';
    return '';
  }

  function entryTitle(e: LedgerEntry): string {
    const kind = e.kind.charAt(0).toUpperCase() + e.kind.slice(1);
    return `${kind} · ${e.asset}`;
  }

  function entryTime(ts: string): string {
    const d = new Date(ts);
    const diffMs = now - d.getTime();
    const secs = Math.floor(diffMs / 1000);
    if (secs < 3600) return `${Math.max(1, Math.floor(secs / 60))}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    if (secs < 604800) {
      const days = Math.floor(secs / 86400);
      return days === 1 ? 'yesterday' : `${days}d ago`;
    }
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function nonBtcSummary(balances: Record<string, string>): string {
    const tickers = Object.keys(balances).sort();
    if (tickers.length === 0) return '';
    const top = tickers.slice(0, 3).join(', ');
    const extra = tickers.length > 3 ? ` · + ${tickers.length - 3} more` : '';
    return top + extra;
  }

  function pollingLabel(secs: number): string {
    if (secs === 60) return 'Every minute';
    if (secs === 300) return 'Every 5 minutes';
    if (secs === 600) return 'Every 10 minutes';
    if (secs === 1800) return 'Every 30 minutes';
    if (secs === 3600) return 'Every hour';
    return `Every ${secs}s`;
  }

  // ─── Lifecycle ───────────────────────────────────────────────────────────────

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';
    await fetchSnapshot();
    tickInterval = setInterval(() => { now = Date.now(); }, 30_000);
    subscribeSSE();
  });

  onDestroy(() => {
    if (tickInterval !== null) clearInterval(tickInterval);
    eventSource?.close();
  });

  // ─── Data fetching ───────────────────────────────────────────────────────────

  async function fetchSnapshot(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        headers: authHeaders(),
      });
      if (!resp.ok) return;
      snapshot = await resp.json();
    } catch { /* offline */ }
  }

  async function forcePoll(): Promise<void> {
    if (!detail || refreshing) return;
    refreshing = true;
    try {
      await fetch(
        `${serverUrl}/api/v1/custodial-providers/${detail.provider_id}/refresh`,
        { method: 'POST', headers: authHeaders() }
      );
      await fetchSnapshot();
    } catch { /* ignore */ } finally {
      refreshing = false;
    }
  }

  // ─── SSE ─────────────────────────────────────────────────────────────────────

  function subscribeSSE(): void {
    if (!serverUrl || !holdingId) return;
    const topics = 'treasury.custodial.cycle_completed,treasury.custodial.ledger_entry_added,treasury.custodial.connection_state_changed';
    const hdrs = authHeaders();
    // EventSource cannot send custom headers; pass the raw credential (without
    // the "Bearer " prefix) as ?token= so the middleware can authenticate it.
    const rawCredential = (hdrs['Authorization'] ?? '').replace('Bearer ', '');
    const tokenParam = rawCredential ? `&token=${encodeURIComponent(rawCredential)}` : '';
    const url = `${serverUrl}/api/v1/events/stream?topics=${encodeURIComponent(topics)}${tokenParam}`;
    eventSource = new EventSource(url);

    eventSource.addEventListener('treasury.custodial.cycle_completed', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchSnapshot();
      } catch { /* ignore */ }
    });

    eventSource.addEventListener('treasury.custodial.ledger_entry_added', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchSnapshot();
      } catch { /* ignore */ }
    });

    eventSource.addEventListener('treasury.custodial.connection_state_changed', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchSnapshot();
        if (data.payload.new_status !== 'healthy') {
          toastDismissed = false;
        }
      } catch { /* ignore */ }
    });
  }

  // ─── Actions ─────────────────────────────────────────────────────────────────

  async function removeAccount(): Promise<void> {
    removing = true;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      if (resp.ok) {
        goto('/home');
      }
    } catch { /* ignore */ } finally {
      removing = false;
    }
  }

  async function updatePollingInterval(secs: number): Promise<void> {
    if (!serverUrl || !holdingId) return;
    pollingUpdating = true;
    try {
      await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ polling_interval_seconds: secs }),
      });
      await fetchSnapshot();
    } catch { /* ignore */ } finally {
      pollingUpdating = false;
      showPollingPicker = false;
    }
  }

  async function submitRename(): Promise<void> {
    if (!renameValue.trim()) return;
    renaming = true;
    try {
      await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name: renameValue.trim() }),
      });
      await fetchSnapshot();
      showRenameInput = false;
    } catch { /* ignore */ } finally {
      renaming = false;
    }
  }

  function openRename(): void {
    renameValue = snapshot?.name ?? '';
    showRenameInput = true;
  }
</script>

<div class="phone-screen safe-top safe-bottom">

  <!-- App bar -->
  <div class="app-bar">
    <button class="back-btn" aria-label="Back" onclick={() => history.back()}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </button>
    <div class="app-bar-title">{snapshot?.name ?? '…'}</div>
    <div></div>
  </div>

  <!-- Scroll area (pull-to-refresh target) -->
  <div class="scroll-area">

    <!-- Connection-error toast (slides in when connection lost / auth failed) -->
    {#if toastVisible}
      <div class="connection-toast" role="alert">
        <div class="toast-row">
          <span class="toast-title">
            {#if detail?.connection_status === 'auth_failed'}
              Your {detail.display_name} API key is no longer valid
            {:else}
              Connection lost · {freshness(detail?.last_polled_at ?? null)}
            {/if}
          </span>
          <button class="toast-close" aria-label="Dismiss" onclick={() => { toastDismissed = true; }}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        {#if detail?.connection_status === 'auth_failed'}
          <button class="toast-retry" type="button"
            onclick={() => goto(`/holding/account/${holdingId}/obs-key/replace`)}>
            Replace key
          </button>
        {:else}
          <button class="toast-retry" type="button" onclick={forcePoll}>
            Try again now
          </button>
        {/if}
      </div>
    {/if}

    {#if detail}
      <!-- Status card (tap to force-refresh) -->
      <button
        class="status-card"
        type="button"
        aria-label="Account connection status — tap to refresh"
        onclick={forcePoll}
        disabled={refreshing}
      >
        <span class="status-provider">{detail.display_name}</span>
        <span class="status-line">
          {#if refreshing}
            <span class="status-spinner" aria-hidden="true">⟳</span>
          {:else}
            <span class="status-dot {dotClass(detail.connection_status)}" aria-hidden="true"></span>
          {/if}
          <span class="status-state">{statusLabel(detail.connection_status)}</span>
          {#if detail.last_polled_at}
            <span class="status-sep">·</span>
            <span>{freshness(detail.last_polled_at)}</span>
          {/if}
        </span>
      </button>

      <!-- Hero balance -->
      <div class="detail-hero">
        <div class="hero-amount-line">
          <span class="hero-amount">
            {preferences.unit === 'sats'
              ? formatSats(detail.last_known_balance_sats ?? 0)
              : formatBtc(detail.last_known_balance_sats ?? 0)}
          </span>
          <span class="hero-unit-label">
            {preferences.unit === 'sats' ? 'sats' : 'BTC'}<button
              class="unit-toggle"
              aria-label="Cycle unit: sats / BTC"
              onclick={preferences.cycleUnit}
            >↻</button>
          </span>
        </div>
        {#if Object.keys(detail.non_btc_balances).length > 0}
          <div class="hero-other-assets">
            <span class="other-label">Other assets:</span>
            {nonBtcSummary(detail.non_btc_balances)}
          </div>
        {/if}
      </div>

      <!-- Action row -->
      <div class="action-row">
        <button class="action-btn" type="button" aria-label="Deposit BTC to this Account"
          onclick={() => goto(`/holding/account/${holdingId}/deposit`)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="4" y="12" width="16" height="9" rx="1.5"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
            <polyline points="8 11 12 15 16 11"/>
          </svg>
          Deposit
        </button>
        <button class="action-btn" type="button" aria-label="Withdraw BTC from this Account"
          onclick={() => goto(`/holding/account/${holdingId}/withdraw`)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="4" y="12" width="16" height="9" rx="1.5"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
            <polyline points="8 7 12 3 16 7"/>
          </svg>
          Withdraw
        </button>
      </div>

      <!-- Tab strip -->
      <div class="tab-strip" role="tablist">
        <button
          class="tab {activeTab === 'operations' ? 'tab--active' : ''}"
          role="tab"
          aria-selected={activeTab === 'operations'}
          onclick={() => { activeTab = 'operations'; }}
        >Operations</button>
        <button
          class="tab {activeTab === 'settings' ? 'tab--active' : ''}"
          role="tab"
          aria-selected={activeTab === 'settings'}
          onclick={() => { activeTab = 'settings'; }}
        >Settings</button>
      </div>

      <!-- ── Operations tab ── -->
      {#if activeTab === 'operations'}
        {#if detail.ledger_entries.length === 0}
          <div class="activity-empty">
            <div class="title">No BTC activity yet</div>
            <div class="sub">BTC deposits, withdrawals, and trades will appear here as they happen on {detail.display_name}. Other assets are not tracked.</div>
          </div>
        {:else}
          <ul class="activity-list" aria-label="Recent BTC activity">
            {#each detail.ledger_entries as entry (entry.id)}
              <li class="activity-entry">
                <span class="activity-main">
                  <span class="activity-title">{entryTitle(entry)}</span>
                  <span class="activity-time">{entryTime(entry.timestamp)}</span>
                </span>
                <span class="activity-amount {amountClass(entry.amount_sats)}">
                  {entry.amount_sats >= 0 ? '+' : '−'}{formatAmount(entry.amount_sats)}<span class="unit">{preferences.unit === 'sats' ? 'sats' : 'BTC'}</span>
                </span>
              </li>
            {/each}
          </ul>
          <p class="activity-btc-note">BTC movements only · other assets not tracked</p>
        {/if}
      {/if}

      <!-- ── Settings tab ── -->
      {#if activeTab === 'settings'}

        <!-- Provider -->
        <div class="settings-label">Provider</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value">{detail.display_name}</div>
              <div class="settings-meta">Connected via API since {new Date(snapshot?.created_at ?? '').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</div>
            </div>
          </div>
        </div>

        <!-- Observation key -->
        <div class="settings-label">Observation key</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              {#if detail.observation_key_last_four}
                <div class="settings-value settings-value--mono">•••• {detail.observation_key_last_four}</div>
              {:else}
                <div class="settings-value settings-value--not-configured">Not configured</div>
              {/if}
              <div class="settings-meta">Read-only API key used to observe balance and ledger activity.</div>
            </div>
            <button class="settings-cta" type="button"
              onclick={() => goto(`/holding/account/${holdingId}/obs-key/replace`)}>
              Replace
            </button>
          </div>
        </div>

        <!-- Withdrawal key -->
        <div class="settings-label">Withdrawal key</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value settings-value--not-configured">Not configured</div>
              <div class="settings-meta">Required to send BTC out of this Account to your other Holdings.</div>
            </div>
            <button class="settings-cta" type="button"
              onclick={() => goto(`/holding/account/${holdingId}/withdraw-key/setup`)}>
              Set up
            </button>
          </div>
        </div>

        <!-- Deposit address -->
        <div class="settings-label">Deposit address</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value settings-value--not-configured">Not configured</div>
              <div class="settings-meta">Required to send BTC into this Account from your other Holdings.</div>
            </div>
            <button class="settings-cta" type="button"
              onclick={() => goto(`/holding/account/${holdingId}/deposit-address/setup`)}>
              Set up
            </button>
          </div>
        </div>

        <!-- Auto-sweep rules -->
        <div class="settings-label">Auto-sweep rules</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value settings-value--not-configured">None</div>
              <div class="settings-meta">Move BTC in or out automatically on a schedule or threshold.</div>
            </div>
            <button class="settings-cta" type="button"
              onclick={() => goto(`/holding/account/${holdingId}/sweep/add`)}>
              Add rule
            </button>
          </div>
        </div>

        <!-- Polling -->
        <div class="settings-label">Polling</div>
        <div class="settings-card">
          {#if showPollingPicker}
            <div class="polling-picker" role="group" aria-label="Select polling interval">
              {#each [60, 300, 600, 1800, 3600] as secs (secs)}
                <button
                  class="polling-option {detail.polling_interval_seconds === secs ? 'polling-option--active' : ''}"
                  type="button"
                  disabled={pollingUpdating}
                  onclick={() => updatePollingInterval(secs)}
                >
                  {pollingLabel(secs)}
                </button>
              {/each}
              <button class="settings-cta" type="button"
                onclick={() => { showPollingPicker = false; }}>
                Cancel
              </button>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value">{pollingLabel(detail.polling_interval_seconds)}</div>
                <div class="settings-meta">How often TallyKeep observes balance and ledger changes at {detail.display_name}.</div>
              </div>
              <button class="settings-cta" type="button"
                onclick={() => { showPollingPicker = true; }}>
                Change
              </button>
            </div>
          {/if}
        </div>

        <!-- Danger zone -->
        <div class="settings-label settings-label--danger">Danger zone</div>
        <div class="settings-card">

          {#if showRenameInput}
            <div class="settings-row">
              <div class="rename-form">
                <input
                  class="rename-input"
                  type="text"
                  bind:value={renameValue}
                  maxlength="100"
                  placeholder="Account name"
                  aria-label="New account name"
                />
                <div class="rename-actions">
                  <button class="settings-cta" type="button"
                    onclick={() => { showRenameInput = false; }}>
                    Cancel
                  </button>
                  <button class="settings-cta settings-cta--primary" type="button"
                    disabled={renaming || !renameValue.trim()}
                    onclick={submitRename}>
                    {renaming ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value">Rename this Account</div>
                <div class="settings-meta">Change how this Account appears across TallyKeep.</div>
              </div>
              <button class="settings-cta" type="button" onclick={openRename}>
                Rename
              </button>
            </div>
          {/if}

          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value">Forget this Account</div>
              <div class="settings-meta">TallyKeep forgets the credentials and stops observing. Your {detail.display_name} account itself is unaffected.</div>
            </div>
            <button class="settings-cta settings-cta--danger" type="button"
              onclick={() => { showRemoveConfirm = true; }}>
              Forget
            </button>
          </div>
        </div>

      {/if}

    {:else}
      <!-- Loading skeleton placeholder -->
      <div class="loading-placeholder" aria-label="Loading…">
        <div class="skel skel-card"></div>
        <div class="skel skel-hero"></div>
        <div class="skel skel-action"></div>
      </div>
    {/if}

  </div>

  <BottomNav active="home" />

  <!-- Remove-confirm bottom sheet (backdrop NOT dismissable) -->
  {#if showRemoveConfirm}
    <div class="modal-backdrop" role="presentation" aria-hidden="true"></div>
    <div class="modal-sheet" role="dialog" aria-modal="true" aria-labelledby="forget-title">
      <div class="drag-handle" aria-hidden="true"></div>
      <h2 id="forget-title" class="modal-title">Forget this Account?</h2>
      <p class="modal-body">
        TallyKeep forgets the API credentials and stops observing
        this Account. Your account on {detail?.display_name ?? 'the provider'} itself is unaffected.
        You keep your funds and history with the provider. You can
        re-add this Account later by running the Add Account wizard
        again.
      </p>
      <div class="modal-actions">
        <button class="btn btn-cancel" type="button"
          disabled={removing}
          onclick={() => { showRemoveConfirm = false; }}>
          Cancel
        </button>
        <button class="btn btn-danger" type="button"
          disabled={removing}
          onclick={removeAccount}>
          {removing ? 'Forgetting…' : 'Forget'}
        </button>
      </div>
    </div>
  {/if}

</div>

<style>
  .phone-screen { background: var(--color-bg); position: relative; }

  /* ── App bar ── */
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: grid;
    grid-template-columns: 44px 1fr 44px;
    align-items: center;
    padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    position: relative;
    z-index: 2;
  }
  .back-btn {
    width: 36px; height: 36px;
    display: inline-flex; align-items: center; justify-content: center;
    background: transparent; border: 0;
    border-radius: var(--radius-md);
    color: var(--color-text);
    cursor: pointer;
    justify-self: start;
    margin-left: var(--space-2);
  }
  .back-btn:hover { background: var(--color-bg); }
  .back-btn svg {
    width: 22px; height: 22px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .app-bar-title {
    text-align: center;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* ── Scroll area ── */
  .scroll-area {
    flex: 1;
    overflow-y: auto;
    padding-bottom: var(--mobile-bottom-nav);
    position: relative;
  }

  /* ── Connection-error toast ── */
  .connection-toast {
    margin: var(--space-3) var(--space-4) 0;
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    box-shadow: var(--shadow-sm);
  }
  .toast-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }
  .toast-title {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-danger-text-on-soft);
  }
  .toast-close {
    background: transparent; border: 0; padding: 0;
    width: 24px; height: 24px;
    display: inline-flex; align-items: center; justify-content: center;
    color: var(--color-danger-text-on-soft);
    cursor: pointer;
    border-radius: var(--radius-sm);
    flex-shrink: 0;
  }
  .toast-close:hover { background: rgba(0,0,0,0.05); }
  .toast-close svg {
    width: 14px; height: 14px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .toast-retry {
    align-self: flex-start;
    background: var(--color-surface);
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-family: inherit;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-danger-text-on-soft);
    cursor: pointer;
  }
  .toast-retry:hover { background: var(--color-danger-soft); }

  /* ── Status card ── */
  .status-card {
    margin: var(--space-3) var(--space-4) 0;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-account);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: 2px;
    cursor: pointer;
    text-align: left;
    width: calc(100% - var(--space-4) * 2);
    font-family: inherit;
  }
  .status-card:hover { background: var(--color-surface-raised); }
  .status-card:disabled { cursor: default; }
  .status-provider {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .status-line {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    line-height: 1.4;
  }
  .status-sep { color: var(--color-text-dim); }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }
  .status-dot--healthy     { background: var(--color-success); }
  .status-dot--degraded    { background: var(--color-warning); }
  .status-dot--unreachable { background: var(--color-danger); }
  .status-state {
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
  }
  .status-spinner {
    font-size: 12px;
    color: var(--color-text-muted);
    animation: spin 1s linear infinite;
    display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Hero ── */
  .detail-hero {
    padding: var(--space-5) var(--space-4) var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .hero-amount-line {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .hero-amount {
    font-family: var(--font-sans);
    font-size: 36px;
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .hero-unit-label {
    font-size: var(--font-size-md);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-medium);
    line-height: 1;
  }
  .unit-toggle {
    background: transparent; border: 0;
    padding: 0 0 0 2px; margin: 0;
    font-size: 0.7em; vertical-align: super; line-height: 1;
    color: var(--color-text-muted);
    cursor: pointer; font-family: inherit;
  }
  .hero-other-assets {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    margin-top: var(--space-1);
  }
  .hero-other-assets .other-label {
    color: var(--color-text-muted);
    margin-right: var(--space-1);
  }

  /* ── Action row ── */
  .action-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-4) var(--space-4);
  }
  .action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    background: var(--color-primary-soft);
    border: 0;
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary-strong);
    cursor: pointer;
  }
  .action-btn:hover { background: #c9e3d9; }
  .action-btn svg {
    width: 18px; height: 18px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }

  /* ── Tab strip ── */
  .tab-strip {
    display: grid;
    grid-template-columns: 1fr 1fr;
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--color-bg);
    border-top: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
  }
  .tab {
    padding: var(--space-3) 0;
    background: transparent;
    border: 0;
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-muted);
    cursor: pointer;
    position: relative;
  }
  .tab:hover { color: var(--color-text); }
  .tab--active {
    color: var(--color-text);
    font-weight: var(--font-weight-semibold);
  }
  .tab--active::after {
    content: '';
    position: absolute;
    left: 12%;
    right: 12%;
    bottom: -1px;
    height: 2px;
    background: var(--color-primary);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  }

  /* ── Activity list ── */
  .activity-list {
    list-style: none;
    margin: 0;
    padding: 0;
    background: var(--color-surface);
  }
  .activity-entry {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--color-border);
  }
  .activity-entry:last-child { border-bottom: 0; }
  .activity-main {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .activity-title {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .activity-time {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }
  .activity-amount {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    align-self: center;
    text-align: right;
  }
  .activity-amount--positive { color: var(--color-success-text-on-soft); }
  .activity-amount--negative { color: var(--color-danger-text-on-soft); }
  .activity-amount .unit {
    color: var(--color-text-dim);
    font-size: 10px;
    margin-left: var(--space-1);
    font-weight: var(--font-weight-normal);
  }

  /* ── Empty state ── */
  .activity-empty {
    background: var(--color-surface);
    padding: var(--space-7) var(--space-5);
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    align-items: center;
  }
  .activity-empty .title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .activity-empty .sub {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 280px;
  }

  .activity-btc-note {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-align: center;
    padding: var(--space-3) var(--space-5) var(--space-5);
    margin: 0;
  }

  /* ── Settings sections ── */
  .settings-label {
    margin: var(--space-4) var(--space-5) var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
  }
  .settings-label--danger { color: var(--color-danger); }
  .settings-card {
    margin: 0 var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
  }
  .settings-card + .settings-label { margin-top: var(--space-5); }
  .settings-row {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) 0;
  }
  .settings-row + .settings-row { border-top: 1px solid var(--color-border); }
  .settings-body { min-width: 0; }
  .settings-value {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
  }
  .settings-value--not-configured {
    color: var(--color-text-muted);
    font-style: italic;
  }
  .settings-value--mono {
    font-family: var(--font-mono);
    letter-spacing: 0.04em;
  }
  .settings-meta {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    margin-top: 2px;
    line-height: var(--line-height-default);
  }
  .settings-cta {
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-family: inherit;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    cursor: pointer;
    flex-shrink: 0;
    white-space: nowrap;
  }
  .settings-cta:hover { background: var(--color-bg); }
  .settings-cta:disabled { opacity: 0.5; cursor: not-allowed; }
  .settings-cta--danger {
    color: var(--color-danger);
    border-color: var(--color-danger-border);
  }
  .settings-cta--danger:hover { background: var(--color-danger-soft); }
  .settings-cta--primary {
    background: var(--color-primary);
    color: var(--color-on-primary);
    border-color: var(--color-primary);
  }
  .settings-cta--primary:hover { background: var(--color-primary-strong); border-color: var(--color-primary-strong); }

  /* ── Polling picker ── */
  .polling-picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2) 0;
  }
  .polling-option {
    padding: var(--space-2) var(--space-3);
    background: transparent;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    cursor: pointer;
    text-align: left;
  }
  .polling-option:hover { background: var(--color-bg); }
  .polling-option--active {
    background: var(--color-primary-soft);
    border-color: var(--color-primary);
    color: var(--color-primary-strong);
    font-weight: var(--font-weight-semibold);
  }
  .polling-option:disabled { opacity: 0.5; cursor: not-allowed; }

  /* ── Rename form ── */
  .rename-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    width: 100%;
  }
  .rename-input {
    width: 100%;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    color: var(--color-text);
    background: var(--color-bg);
    box-sizing: border-box;
  }
  .rename-input:focus { outline: 2px solid var(--color-primary); outline-offset: -1px; }
  .rename-actions {
    display: flex;
    gap: var(--space-2);
    justify-content: flex-end;
  }

  /* ── Loading skeleton ── */
  .loading-placeholder { padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }
  .skel {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    animation: pulse 1.5s ease-in-out infinite;
  }
  .skel-card { height: 64px; }
  .skel-hero { height: 80px; }
  .skel-action { height: 48px; }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* ── Remove confirm modal ── */
  .modal-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 10;
  }
  .modal-sheet {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    background: var(--color-surface);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    padding: var(--space-3) var(--space-5) var(--space-5);
    z-index: 11;
    box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.18);
  }
  .drag-handle {
    width: 36px; height: 4px;
    margin: 0 auto var(--space-4);
    background: var(--color-border-strong);
    border-radius: var(--radius-pill);
  }
  .modal-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0 0 var(--space-2);
    line-height: var(--line-height-tight);
  }
  .modal-body {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: 0 0 var(--space-4);
  }
  .modal-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
  }
  .btn {
    padding: var(--space-3) var(--space-4);
    border: 0;
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
  }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-cancel {
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    color: var(--color-danger-text-on-soft);
  }
  .btn-cancel:hover:not(:disabled) { background: #ecc5b6; }
  .btn-danger {
    background: var(--color-danger);
    color: #ffffff;
  }
  .btn-danger:hover:not(:disabled) { background: #9b2a14; }
</style>
