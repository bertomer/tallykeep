<!--
  Account + Purse + Strongbox detail — /holding/[id]
  Mockup contract (all validated):
    mobile_account_detail_operations_populated.html         (2026-05-17)
    mobile_account_detail_operations_empty.html             (2026-05-17)
    mobile_account_detail_settings.html                     (2026-05-17)
    mobile_account_detail_remove_confirm.html               (2026-05-19 — fill-bar timer)
    mobile_account_detail_connection_error.html             (2026-05-17)
    mobile_purse_detail_operations_populated.html           (2026-05-19)
    mobile_purse_detail_operations_empty.html               (2026-05-19)
    mobile_purse_detail_settings_watch_only.html            (2026-05-20 — Copy CTA retrofit)
    mobile_purse_detail_settings_on_device.html             (2026-05-20 — Copy CTA retrofit)
    mobile_purse_detail_forget_confirm.html                 (2026-05-19)
    mobile_purse_detail_connection_error.html               (2026-05-19)
    mobile_purse_detail_send_blocked_watch_only.html        (2026-05-19)
    mobile_strongbox_detail_operations_populated.html       (2026-05-20)
    mobile_strongbox_detail_operations_empty.html           (2026-05-20)
    mobile_strongbox_detail_settings.html                   (2026-05-20)
    mobile_strongbox_detail_settings_missing_metadata.html  (2026-05-20)
    mobile_strongbox_detail_forget_confirm.html             (2026-05-20)
    mobile_strongbox_detail_connection_error.html           (2026-05-20)
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
    purse_mode: string | null;
    account_detail: AccountDetail | null;
    signing_device_label: string | null;
    signing_metadata_present: boolean | null;
  }

  interface PurseLedgerEntry {
    id: string;
    direction: string;
    net_amount_sats: number;
    timestamp: string;
    category: string | null;
  }

  interface PurseDescriptor {
    id: string;
    expression: string;
  }

  // ─── Core state ──────────────────────────────────────────────────────────────

  let holdingId = $derived($page.params.id ?? '');
  let serverUrl = $state('');

  let snapshot = $state<HoldingSnapshot | null>(null);
  let detail = $derived(snapshot?.account_detail ?? null);

  let activeTab = $state<'operations' | 'settings'>('operations');

  // ─── Account: connection-error toast ─────────────────────────────────────────

  let toastDismissed = $state(false);
  let toastVisible = $derived(
    !toastDismissed &&
    !!detail &&
    (detail.connection_status === 'unreachable' || detail.connection_status === 'auth_failed')
  );

  $effect(() => {
    if (!toastVisible) return;
    const t = setTimeout(() => { toastDismissed = true; }, 5000);
    return () => clearTimeout(t);
  });

  // ─── Account: forget modal with fill-bar timer ────────────────────────────────

  let showRemoveConfirm = $state(false);
  let removing = $state(false);
  let forgetCountdown = $state(5);
  let forgetCounting = $state(false);
  let forgetReady = $derived(forgetCountdown <= 0);

  $effect(() => {
    if (showRemoveConfirm) {
      forgetCountdown = 5;
      forgetCounting = false;
      requestAnimationFrame(() => { forgetCounting = true; });
      const h = setInterval(() => {
        forgetCountdown -= 1;
        if (forgetCountdown <= 0) clearInterval(h);
      }, 1000);
      return () => {
        clearInterval(h);
        forgetCounting = false;
        forgetCountdown = 5;
      };
    }
  });

  // ─── Account: other state ─────────────────────────────────────────────────────

  let showPollingPicker = $state(false);
  let pollingUpdating = $state(false);

  let showRenameInput = $state(false);
  let renameValue = $state('');
  let renaming = $state(false);

  // ─── Purse state ─────────────────────────────────────────────────────────────

  let purseBalance = $state(0);
  let purseLedger = $state<PurseLedgerEntry[]>([]);
  let purseDescriptors = $state<PurseDescriptor[]>([]);
  let purseChainStatus = $state('healthy');
  let purseLastFetched = $state<number | null>(null);
  let purseToastDismissed = $state(false);
  let purseRefreshing = $state(false);
  let showDescriptor = $state(false);
  let purseCopied = $state(false);
  let showPurseRenameInput = $state(false);
  let purseRenameValue = $state('');
  let purseRenaming = $state(false);
  let showPurseForgetModal = $state(false);
  let purseForgetCountdown = $state(5);
  let purseForgetCounting = $state(false);
  let purseForgetReady = $derived(purseForgetCountdown <= 0);
  let purseForgetRemoving = $state(false);
  let purseForgetError = $state(false);
  let purseEventSource: EventSource | null = null;

  // ─── Strongbox state ──────────────────────────────────────────────────────────

  let strongboxBalance = $state(0);
  let strongboxLedger = $state<PurseLedgerEntry[]>([]);
  let strongboxDescriptors = $state<PurseDescriptor[]>([]);
  let strongboxChainStatus = $state('healthy');
  let strongboxLastFetched = $state<number | null>(null);
  let strongboxToastDismissed = $state(false);
  let strongboxRefreshing = $state(false);
  let showStrongboxDescriptor = $state(false);
  let strongboxCopied = $state(false);
  let showStrongboxRenameInput = $state(false);
  let strongboxRenameValue = $state('');
  let strongboxRenaming = $state(false);
  let showSigningLabelInput = $state(false);
  let signingLabelValue = $state('');
  let signingLabelSaving = $state(false);
  let showStrongboxForgetModal = $state(false);
  let strongboxForgetCountdown = $state(5);
  let strongboxForgetCounting = $state(false);
  let strongboxForgetReady = $derived(strongboxForgetCountdown <= 0);
  let strongboxForgetRemoving = $state(false);
  let strongboxEventSource: EventSource | null = null;

  let strongboxToastVisible = $derived(
    !strongboxToastDismissed &&
    snapshot?.holding_type === 'strongbox' &&
    (strongboxChainStatus === 'unreachable' || strongboxChainStatus === 'degraded')
  );

  $effect(() => {
    if (!strongboxToastVisible) return;
    const t = setTimeout(() => { strongboxToastDismissed = true; }, 5000);
    return () => clearTimeout(t);
  });

  $effect(() => {
    if (showStrongboxForgetModal) {
      strongboxForgetCountdown = 5;
      strongboxForgetCounting = false;
      requestAnimationFrame(() => { strongboxForgetCounting = true; });
      const h = setInterval(() => {
        strongboxForgetCountdown -= 1;
        if (strongboxForgetCountdown <= 0) clearInterval(h);
      }, 1000);
      return () => {
        clearInterval(h);
        strongboxForgetCounting = false;
        strongboxForgetCountdown = 5;
      };
    }
  });

  let purseToastVisible = $derived(
    !purseToastDismissed &&
    snapshot?.holding_type === 'purse' &&
    (purseChainStatus === 'unreachable' || purseChainStatus === 'degraded')
  );

  $effect(() => {
    if (!purseToastVisible) return;
    const t = setTimeout(() => { purseToastDismissed = true; }, 5000);
    return () => clearTimeout(t);
  });

  $effect(() => {
    if (showPurseForgetModal) {
      purseForgetCountdown = 5;
      purseForgetCounting = false;
      purseForgetError = false;
      requestAnimationFrame(() => { purseForgetCounting = true; });
      const h = setInterval(() => {
        purseForgetCountdown -= 1;
        if (purseForgetCountdown <= 0) clearInterval(h);
      }, 1000);
      return () => {
        clearInterval(h);
        purseForgetCounting = false;
        purseForgetCountdown = 5;
      };
    }
  });

  // ─── Freshness ticker ────────────────────────────────────────────────────────

  let now = $state(Date.now());
  let tickInterval: ReturnType<typeof setInterval> | null = null;

  // ─── SSE cleanup handles ─────────────────────────────────────────────────────

  let eventSource: EventSource | null = null;
  let refreshing = $state(false);

  // ─── Helpers ─────────────────────────────────────────────────────────────────

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
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function formatBtc(sats: number): string {
    return (sats / 1e8).toFixed(8).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
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
    const extra = tickers.length > 3 ? ` · + ${tickers.length - 3} more` : '';
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

  // Purse-specific helpers

  function purseModeLabel(mode: string | null): string {
    if (!mode) return 'Wallet';
    if (mode.startsWith('on_device')) return 'Spending wallet';
    if (mode === 'watch_only') return 'Watch-only';
    return 'Wallet';
  }

  function purseModeDesc(mode: string | null, createdAt: string): string {
    const date = new Date(createdAt).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    if (mode === 'on_device_tk_generated') return `TallyKeep generated this wallet's keys on ${date}. They live on this device only.`;
    if (mode === 'on_device_user_imported') return `You imported this wallet's keys on ${date}. They live on this device only.`;
    if (mode === 'watch_only') return `Imported from descriptor on ${date}. TallyKeep doesn't hold the keys for this Purse.`;
    return `Created ${date}.`;
  }

  function purseChainStatusLabel(status: string): string {
    if (status === 'healthy') return 'Connected';
    if (status === 'degraded') return 'Degraded';
    if (status === 'unreachable') return 'Connection lost';
    return 'Connected';
  }

  function purseFreshness(): string {
    if (!purseLastFetched) return '';
    const diffMs = now - purseLastFetched;
    const secs = Math.floor(diffMs / 1000);
    const prefix = purseChainStatus === 'healthy' ? 'Updated' : 'Last seen';
    if (secs < 60) return `${prefix} just now`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${prefix} ${mins} min ago`;
    const hrs = Math.floor(mins / 60);
    return `${prefix} ${hrs}h ago`;
  }

  function purseEntryTitle(e: PurseLedgerEntry): string {
    if (e.direction === 'incoming') return 'Received · BTC';
    if (e.direction === 'outgoing') return 'Sent · BTC';
    return 'Transfer · BTC';
  }

  function purseEntryAmountClass(e: PurseLedgerEntry): string {
    if (e.direction === 'incoming') return 'activity-amount--positive';
    if (e.direction === 'outgoing') return 'activity-amount--negative';
    return '';
  }

  function purseDescriptorMasked(expr: string): string {
    if (!expr) return '•••• ??????';
    return `•••• ${expr.slice(-6)}`;
  }

  // Strongbox-specific helpers

  function strongboxSubtitle(): string {
    return snapshot?.signing_device_label?.trim() || 'External signing device';
  }

  function strongboxChainStatusLabel(status: string): string {
    if (status === 'healthy') return 'Connected';
    if (status === 'degraded') return 'Degraded';
    if (status === 'unreachable') return 'Connection lost';
    return 'Connected';
  }

  function strongboxFreshness(): string {
    if (!strongboxLastFetched) return '';
    const diffMs = now - strongboxLastFetched;
    const secs = Math.floor(diffMs / 1000);
    const prefix = strongboxChainStatus === 'healthy' ? 'Updated' : 'Last seen';
    if (secs < 60) return `${prefix} just now`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${prefix} ${mins} min ago`;
    const hrs = Math.floor(mins / 60);
    return `${prefix} ${hrs}h ago`;
  }

  function strongboxCreatedLabel(): string {
    if (!snapshot?.created_at) return '';
    return new Date(snapshot.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }

  function strongboxDescriptorMasked(expr: string): string {
    if (!expr) return '•••• ??????';
    return `•••• ${expr.slice(-6)}`;
  }

  // ─── Lifecycle ───────────────────────────────────────────────────────────────

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';
    await fetchSnapshot();
    tickInterval = setInterval(() => { now = Date.now(); }, 30_000);
    if (snapshot?.holding_type === 'purse') {
      await fetchPurseAll();
      subscribePurseSSE();
    } else if (snapshot?.holding_type === 'strongbox') {
      await fetchStrongboxAll();
      subscribeStrongboxSSE();
    } else {
      subscribeSSE();
    }
  });

  onDestroy(() => {
    if (tickInterval !== null) clearInterval(tickInterval);
    eventSource?.close();
    purseEventSource?.close();
    strongboxEventSource?.close();
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

  async function fetchPurseBalance(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}/summary`, {
        headers: authHeaders(),
      });
      if (!resp.ok) return;
      const data = await resp.json();
      purseBalance = data.confirmed_sats ?? 0;
    } catch { /* offline */ }
  }

  async function fetchPurseLedger(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/ledger-entries?holding_id=${holdingId}&limit=50`,
        { headers: authHeaders() }
      );
      if (!resp.ok) return;
      const data = await resp.json();
      purseLedger = data.entries ?? [];
    } catch { /* offline */ }
  }

  async function fetchPurseDescriptors(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/descriptors?holding_id=${holdingId}`,
        { headers: authHeaders() }
      );
      if (!resp.ok) return;
      purseDescriptors = await resp.json();
    } catch { /* offline */ }
  }

  async function fetchPurseAll(): Promise<void> {
    await Promise.all([fetchPurseBalance(), fetchPurseLedger(), fetchPurseDescriptors()]);
    purseLastFetched = Date.now();
  }

  async function fetchStrongboxBalance(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}/summary`, {
        headers: authHeaders(),
      });
      if (!resp.ok) return;
      const data = await resp.json();
      strongboxBalance = data.confirmed_sats ?? 0;
    } catch { /* offline */ }
  }

  async function fetchStrongboxLedger(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/ledger-entries?holding_id=${holdingId}&limit=50`,
        { headers: authHeaders() }
      );
      if (!resp.ok) return;
      const data = await resp.json();
      strongboxLedger = data.entries ?? [];
    } catch { /* offline */ }
  }

  async function fetchStrongboxDescriptors(): Promise<void> {
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/descriptors?holding_id=${holdingId}`,
        { headers: authHeaders() }
      );
      if (!resp.ok) return;
      strongboxDescriptors = await resp.json();
    } catch { /* offline */ }
  }

  async function fetchStrongboxAll(): Promise<void> {
    await Promise.all([fetchStrongboxBalance(), fetchStrongboxLedger(), fetchStrongboxDescriptors()]);
    strongboxLastFetched = Date.now();
  }

  // ─── SSE ─────────────────────────────────────────────────────────────────────

  function subscribeSSE(): void {
    if (!serverUrl || !holdingId) return;
    const topics = 'treasury.custodial.cycle_completed,treasury.custodial.ledger_entry_added,treasury.custodial.connection_state_changed';
    const hdrs = authHeaders();
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

  function subscribePurseSSE(): void {
    if (!serverUrl || !holdingId) return;
    const topics = 'system.chain.connection_state_changed,holding.utxo.received,holding.utxo.spent';
    const hdrs = authHeaders();
    const rawCredential = (hdrs['Authorization'] ?? '').replace('Bearer ', '');
    const tokenParam = rawCredential ? `&token=${encodeURIComponent(rawCredential)}` : '';
    const url = `${serverUrl}/api/v1/events/stream?topics=${encodeURIComponent(topics)}${tokenParam}`;
    purseEventSource = new EventSource(url);

    purseEventSource.addEventListener('system.chain.connection_state_changed', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        const status: string = data.payload?.new_status ?? 'healthy';
        purseChainStatus = status;
        if (status !== 'healthy') {
          purseToastDismissed = false;
        }
      } catch { /* ignore */ }
    });

    purseEventSource.addEventListener('holding.utxo.received', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchPurseAll();
      } catch { /* ignore */ }
    });

    purseEventSource.addEventListener('holding.utxo.spent', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchPurseAll();
      } catch { /* ignore */ }
    });
  }

  function subscribeStrongboxSSE(): void {
    if (!serverUrl || !holdingId) return;
    const topics = 'system.chain.connection_state_changed,holding.utxo.received,holding.utxo.spent';
    const hdrs = authHeaders();
    const rawCredential = (hdrs['Authorization'] ?? '').replace('Bearer ', '');
    const tokenParam = rawCredential ? `&token=${encodeURIComponent(rawCredential)}` : '';
    const url = `${serverUrl}/api/v1/events/stream?topics=${encodeURIComponent(topics)}${tokenParam}`;
    strongboxEventSource = new EventSource(url);

    strongboxEventSource.addEventListener('system.chain.connection_state_changed', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        const status: string = data.payload?.new_status ?? 'healthy';
        strongboxChainStatus = status;
        if (status !== 'healthy') {
          strongboxToastDismissed = false;
        }
      } catch { /* ignore */ }
    });

    strongboxEventSource.addEventListener('holding.utxo.received', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchStrongboxAll();
      } catch { /* ignore */ }
    });

    strongboxEventSource.addEventListener('holding.utxo.spent', (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.payload?.holding_id !== holdingId) return;
        fetchStrongboxAll();
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

  async function forcePurseRefresh(): Promise<void> {
    if (purseRefreshing) return;
    purseRefreshing = true;
    try {
      await fetchPurseAll();
    } catch { /* ignore */ } finally {
      purseRefreshing = false;
    }
  }

  async function forgePurse(): Promise<void> {
    if (!snapshot || purseForgetRemoving) return;
    purseForgetRemoving = true;
    try {
      if (snapshot.purse_mode?.startsWith('on_device')) {
        try {
          await secureStorage.delete(holdingId);
        } catch {
          purseForgetError = true;
          purseForgetRemoving = false;
          return;
        }
      }
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}/archive`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (resp.ok) {
        goto('/home');
      }
    } catch { /* ignore */ } finally {
      purseForgetRemoving = false;
    }
  }

  function openPurseRename(): void {
    purseRenameValue = snapshot?.name ?? '';
    showPurseRenameInput = true;
  }

  async function submitPurseRename(): Promise<void> {
    if (!purseRenameValue.trim()) return;
    purseRenaming = true;
    try {
      await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name: purseRenameValue.trim() }),
      });
      await fetchSnapshot();
      showPurseRenameInput = false;
    } catch { /* ignore */ } finally {
      purseRenaming = false;
    }
  }

  async function copyPurseDescriptor(): Promise<void> {
    const expr = purseDescriptors[0]?.expression ?? '';
    if (!expr) return;
    try {
      await navigator.clipboard.writeText(expr);
      purseCopied = true;
      setTimeout(() => { purseCopied = false; }, 2000);
    } catch { /* ignore */ }
  }

  async function forceStrongboxRefresh(): Promise<void> {
    if (strongboxRefreshing) return;
    strongboxRefreshing = true;
    try {
      await fetchStrongboxAll();
    } catch { /* ignore */ } finally {
      strongboxRefreshing = false;
    }
  }

  async function forgetStrongbox(): Promise<void> {
    if (strongboxForgetRemoving) return;
    strongboxForgetRemoving = true;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}/archive`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (resp.ok) {
        goto('/home');
      }
    } catch { /* ignore */ } finally {
      strongboxForgetRemoving = false;
    }
  }

  function openStrongboxRename(): void {
    strongboxRenameValue = snapshot?.name ?? '';
    showStrongboxRenameInput = true;
  }

  async function submitStrongboxRename(): Promise<void> {
    if (!strongboxRenameValue.trim()) return;
    strongboxRenaming = true;
    try {
      await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name: strongboxRenameValue.trim() }),
      });
      await fetchSnapshot();
      showStrongboxRenameInput = false;
    } catch { /* ignore */ } finally {
      strongboxRenaming = false;
    }
  }

  function openSigningLabelEdit(): void {
    signingLabelValue = snapshot?.signing_device_label ?? '';
    showSigningLabelInput = true;
  }

  async function submitSigningLabel(): Promise<void> {
    signingLabelSaving = true;
    try {
      // NOTE: signing_device_label is absent from HoldingUpdate PATCH schema
      // (additionalProperties: false) — backend gap, will return 422 until fixed.
      await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ signing_device_label: signingLabelValue.trim() || null }),
      });
      await fetchSnapshot();
      showSigningLabelInput = false;
    } catch { /* ignore */ } finally {
      signingLabelSaving = false;
    }
  }

  async function copyStrongboxDescriptor(): Promise<void> {
    const expr = strongboxDescriptors[0]?.expression ?? '';
    if (!expr) return;
    try {
      await navigator.clipboard.writeText(expr);
      strongboxCopied = true;
      setTimeout(() => { strongboxCopied = false; }, 2000);
    } catch { /* ignore */ }
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

  <!-- Scroll area -->
  <div class="scroll-area">

    {#if snapshot?.holding_type === 'purse'}

      <!-- ── Purse: connection-error toast ── -->
      {#if purseToastVisible}
        <div class="connection-toast" role="alert">
          <div class="toast-row">
            <span class="toast-title">Cannot reach the Bitcoin network</span>
            <button class="toast-close" aria-label="Dismiss"
              onclick={() => { purseToastDismissed = true; }}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <button class="toast-retry" type="button" onclick={forcePurseRefresh}>
            Try again now
          </button>
        </div>
      {/if}

      <!-- ── Purse: status card ── -->
      <button
        class="status-card status-card--purse"
        type="button"
        aria-label="Wallet connection status — tap to refresh"
        onclick={forcePurseRefresh}
        disabled={purseRefreshing}
      >
        <span class="status-mode">{purseModeLabel(snapshot?.purse_mode ?? null)}</span>
        <span class="status-line">
          {#if purseRefreshing}
            <span class="status-spinner" aria-hidden="true">⟳</span>
          {:else}
            <span class="status-dot {dotClass(purseChainStatus)}" aria-hidden="true"></span>
          {/if}
          <span class="status-state">{purseChainStatusLabel(purseChainStatus)}</span>
          {#if purseLastFetched}
            <span class="status-sep">·</span>
            <span>{purseFreshness()}</span>
          {/if}
        </span>
      </button>

      <!-- ── Purse: hero balance ── -->
      <div class="detail-hero">
        <div class="hero-amount-line">
          <span class="hero-amount">
            {preferences.unit === 'sats' ? formatSats(purseBalance) : formatBtc(purseBalance)}
          </span>
          <span class="hero-unit-label">
            {preferences.unit === 'sats' ? 'sats' : 'BTC'}<button
              class="unit-toggle"
              aria-label="Cycle unit: sats / BTC"
              onclick={preferences.cycleUnit}
            >↻</button>
          </span>
        </div>
      </div>

      <!-- ── Purse: action row ── -->
      <div class="action-row">
        <button class="action-btn" type="button" aria-label="Send BTC from this wallet"
          onclick={() => goto(`/holding/purse/${holdingId}/send`)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <line x1="5" y1="15" x2="19" y2="15"/>
            <line x1="12" y1="9" x2="12" y2="2"/>
            <polyline points="8 6 12 2 16 6"/>
          </svg>
          Send
        </button>
        <button class="action-btn" type="button" aria-label="Receive BTC into this wallet"
          onclick={() => goto(`/holding/purse/${holdingId}/receive`)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <line x1="5" y1="15" x2="19" y2="15"/>
            <line x1="12" y1="2" x2="12" y2="9"/>
            <polyline points="8 5 12 9 16 5"/>
          </svg>
          Receive
        </button>
      </div>

      <!-- ── Purse: tab strip ── -->
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

      <!-- ── Purse: Operations tab ── -->
      {#if activeTab === 'operations'}
        {#if purseLedger.length === 0}
          <div class="activity-empty">
            <div class="title">No activity yet</div>
            <div class="sub">Incoming and outgoing payments will surface here as they hit the chain.</div>
          </div>
        {:else}
          <ul class="activity-list" aria-label="Recent activity">
            {#each purseLedger as entry (entry.id)}
              <li class="activity-entry">
                <span class="activity-main">
                  <span class="activity-title">{purseEntryTitle(entry)}</span>
                  <span class="activity-time">{entryTime(entry.timestamp)}</span>
                  {#if entry.category}
                    <span class="activity-category">
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <polyline points="3 7 9 13 21 5"/>
                      </svg>
                      {entry.category}
                    </span>
                  {/if}
                </span>
                <span class="activity-amount {purseEntryAmountClass(entry)}">
                  {entry.direction === 'incoming' ? '+' : '−'}{formatAmount(entry.net_amount_sats)}<span class="unit">{preferences.unit === 'sats' ? 'sats' : 'BTC'}</span>
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      {/if}

      <!-- ── Purse: Settings tab ── -->
      {#if activeTab === 'settings'}

        <!-- Wallet -->
        <div class="settings-label">Wallet</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value">{purseModeLabel(snapshot?.purse_mode ?? null)}</div>
              <div class="settings-meta">{purseModeDesc(snapshot?.purse_mode ?? null, snapshot?.created_at ?? '')}</div>
            </div>
          </div>
        </div>

        <!-- Display name -->
        <div class="settings-label">Display name</div>
        <div class="settings-card">
          {#if showPurseRenameInput}
            <div class="settings-row">
              <div class="rename-form">
                <input
                  class="rename-input"
                  type="text"
                  bind:value={purseRenameValue}
                  maxlength="100"
                  placeholder="Purse name"
                  aria-label="New Purse name"
                />
                <div class="rename-actions">
                  <button class="settings-cta" type="button"
                    onclick={() => { showPurseRenameInput = false; }}>
                    Cancel
                  </button>
                  <button class="settings-cta settings-cta--primary" type="button"
                    disabled={purseRenaming || !purseRenameValue.trim()}
                    onclick={submitPurseRename}>
                    {purseRenaming ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value">{snapshot?.name ?? ''}</div>
                <div class="settings-meta">How this Purse appears across TallyKeep.</div>
              </div>
              <button class="settings-cta" type="button" onclick={openPurseRename}>Rename</button>
            </div>
          {/if}
        </div>

        <!-- Descriptor -->
        <div class="settings-label">Descriptor</div>
        <div class="settings-card">
          {#if showDescriptor}
            <div class="descriptor-revealed">
              <div class="settings-meta">The public-key descriptor TallyKeep watches on the chain. Safe to paste into Sparrow, Specter, or Electrum for an independent view.</div>
              <div class="descriptor-mono-card">{purseDescriptors[0]?.expression ?? ''}</div>
              <div class="descriptor-actions">
                <button class="settings-cta" type="button"
                  onclick={() => { showDescriptor = false; }}>
                  Hide
                </button>
                <button class="settings-cta" type="button"
                  onclick={copyPurseDescriptor}>
                  {purseCopied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value settings-value--mono">
                  {purseDescriptorMasked(purseDescriptors[0]?.expression ?? '')}
                </div>
                <div class="settings-meta">The public-key descriptor TallyKeep watches on the chain.</div>
              </div>
              <button class="settings-cta" type="button"
                onclick={() => { showDescriptor = true; }}>
                Show
              </button>
            </div>
          {/if}
        </div>

        <!-- Recovery phrase (ON_DEVICE only) -->
        {#if snapshot?.purse_mode?.startsWith('on_device')}
          <div class="settings-label">Recovery phrase</div>
          <div class="settings-card">
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value">View recovery phrase</div>
                <div class="settings-meta">The 12-word phrase that recovers this wallet's keys. Sensitive — only shown after biometric.</div>
              </div>
              <button class="settings-cta" type="button"
                onclick={() => goto(`/holding/purse/${holdingId}/recovery`)}>
                View
              </button>
            </div>
          </div>
        {/if}

        <!-- Auto-sweep rules -->
        <div class="settings-label">Auto-sweep rules</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value settings-value--not-configured">None</div>
              <div class="settings-meta">Move BTC out of this Purse automatically on a schedule or threshold.</div>
            </div>
            <button class="settings-cta" type="button"
              onclick={() => goto(`/holding/purse/${holdingId}/sweep/add`)}>
              Add rule
            </button>
          </div>
        </div>

        <!-- Instant payments -->
        <div class="settings-label">Instant payments</div>
        <div class="settings-card">
          {#if snapshot?.purse_mode?.startsWith('on_device')}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value settings-value--not-configured">Not enabled</div>
                <div class="settings-meta">Add Lightning to this wallet for small, instant, low-fee payments.</div>
              </div>
              <button class="settings-cta" type="button"
                onclick={() => goto(`/holding/purse/${holdingId}/lightning`)}>
                Activate
              </button>
            </div>
          {:else}
            <div class="settings-row settings-row--gated">
              <div class="settings-body">
                <div class="settings-value settings-value--not-configured">Needs on-device keys</div>
                <div class="settings-meta">Lightning needs signing capability. Add the keys to this Purse to enable instant payments.</div>
              </div>
              <button class="settings-cta settings-cta--disabled" type="button" aria-disabled="true">
                Activate
              </button>
            </div>
          {/if}
        </div>

        <!-- Danger zone -->
        <div class="settings-label settings-label--danger">Danger zone</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value">Forget this Purse</div>
              <div class="settings-meta">
                {#if snapshot?.purse_mode?.startsWith('on_device')}
                  TallyKeep destroys the keys on this device. Without a working recovery-phrase backup, the funds become permanently inaccessible. Any categories you've assigned to this Purse's activity are erased with it.
                {:else}
                  TallyKeep forgets the descriptor and stops scanning the chain. Funds at your source wallet are unaffected. Any categories you've assigned to this Purse's activity are erased with it.
                {/if}
              </div>
            </div>
            <button class="settings-cta settings-cta--danger" type="button"
              onclick={() => { showPurseForgetModal = true; }}>
              Forget
            </button>
          </div>
        </div>

      {/if}

    {:else if snapshot?.holding_type === 'strongbox'}

      <!-- ── Strongbox: connection-error toast ── -->
      {#if strongboxToastVisible}
        <div class="connection-toast" role="alert">
          <div class="toast-row">
            <span class="toast-title">Cannot reach the Bitcoin network</span>
            <button class="toast-close" aria-label="Dismiss"
              onclick={() => { strongboxToastDismissed = true; }}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <button class="toast-retry" type="button" onclick={forceStrongboxRefresh}>
            Try again now
          </button>
        </div>
      {/if}

      <!-- ── Strongbox: status card ── -->
      <button
        class="status-card status-card--strongbox"
        type="button"
        aria-label="Wallet connection status — tap to refresh"
        onclick={forceStrongboxRefresh}
        disabled={strongboxRefreshing}
      >
        <span class="status-mode">{strongboxSubtitle()}</span>
        <span class="status-line">
          {#if strongboxRefreshing}
            <span class="status-spinner" aria-hidden="true">⟳</span>
          {:else}
            <span class="status-dot {dotClass(strongboxChainStatus)}" aria-hidden="true"></span>
          {/if}
          <span class="status-state">{strongboxChainStatusLabel(strongboxChainStatus)}</span>
          {#if strongboxLastFetched}
            <span class="status-sep">·</span>
            <span>{strongboxFreshness()}</span>
          {/if}
        </span>
      </button>

      <!-- ── Strongbox: hero balance ── -->
      <div class="detail-hero">
        <div class="hero-amount-line">
          <span class="hero-amount">
            {preferences.unit === 'sats' ? formatSats(strongboxBalance) : formatBtc(strongboxBalance)}
          </span>
          <span class="hero-unit-label">
            {preferences.unit === 'sats' ? 'sats' : 'BTC'}<button
              class="unit-toggle"
              aria-label="Cycle unit: sats / BTC"
              onclick={preferences.cycleUnit}
            >↻</button>
          </span>
        </div>
      </div>

      <!-- ── Strongbox: action row ── -->
      <div class="action-row">
        <button class="action-btn" type="button" aria-label="Send BTC from this Strongbox"
          onclick={() => goto(`/holding/strongbox/${holdingId}/send`)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <line x1="5" y1="15" x2="19" y2="15"/>
            <line x1="12" y1="9" x2="12" y2="2"/>
            <polyline points="8 6 12 2 16 6"/>
          </svg>
          Send
        </button>
        <button class="action-btn" type="button" aria-label="Receive BTC into this Strongbox"
          onclick={() => goto(`/holding/strongbox/${holdingId}/receive`)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <line x1="5" y1="15" x2="19" y2="15"/>
            <line x1="12" y1="2" x2="12" y2="9"/>
            <polyline points="8 5 12 9 16 5"/>
          </svg>
          Receive
        </button>
      </div>

      <!-- ── Strongbox: tab strip ── -->
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

      <!-- ── Strongbox: Operations tab ── -->
      {#if activeTab === 'operations'}
        {#if strongboxLedger.length === 0}
          <div class="activity-empty">
            <div class="title">No activity yet</div>
            <div class="sub">Incoming and outgoing payments will surface here as they hit the chain.</div>
          </div>
        {:else}
          <ul class="activity-list" aria-label="Recent activity">
            {#each strongboxLedger as entry (entry.id)}
              <li class="activity-entry">
                <span class="activity-main">
                  <span class="activity-title">{purseEntryTitle(entry)}</span>
                  <span class="activity-time">{entryTime(entry.timestamp)}</span>
                  {#if entry.category}
                    <span class="activity-category">
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <polyline points="3 7 9 13 21 5"/>
                      </svg>
                      {entry.category}
                    </span>
                  {/if}
                </span>
                <span class="activity-amount {purseEntryAmountClass(entry)}">
                  {entry.direction === 'incoming' ? '+' : '−'}{formatAmount(entry.net_amount_sats)}<span class="unit">{preferences.unit === 'sats' ? 'sats' : 'BTC'}</span>
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      {/if}

      <!-- ── Strongbox: Settings tab ── -->
      {#if activeTab === 'settings'}

        <!-- Advisory: missing signing metadata -->
        {#if snapshot?.signing_metadata_present === false}
          <div class="advisory-card" role="status">
            <div class="advisory-header">
              <span class="advisory-title">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M 12 3 L 22 20 L 2 20 Z"/>
                  <line x1="12" y1="10" x2="12" y2="14"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                Missing derivation metadata
              </span>
              <button class="advisory-cta" type="button"
                onclick={() => goto(`/holding/strongbox/${holdingId}/fix-metadata`)}>
                Fix this
              </button>
            </div>
            <p class="advisory-body">
              Your hardware wallet may refuse to sign transactions with this descriptor. Receiving funds works as expected. Re-export your descriptor with full origin metadata to enable signing.
            </p>
          </div>
        {/if}

        <!-- Wallet -->
        <div class="settings-label">Wallet</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value">External signing device</div>
              <div class="settings-meta">Imported on {strongboxCreatedLabel()}. The signing keys live on your hardware wallet — TallyKeep never sees them.</div>
            </div>
          </div>
        </div>

        <!-- Display name -->
        <div class="settings-label">Display name</div>
        <div class="settings-card">
          {#if showStrongboxRenameInput}
            <div class="settings-row">
              <div class="rename-form">
                <input
                  class="rename-input"
                  type="text"
                  bind:value={strongboxRenameValue}
                  maxlength="100"
                  placeholder="Strongbox name"
                  aria-label="New Strongbox name"
                />
                <div class="rename-actions">
                  <button class="settings-cta" type="button"
                    onclick={() => { showStrongboxRenameInput = false; }}>
                    Cancel
                  </button>
                  <button class="settings-cta settings-cta--primary" type="button"
                    disabled={strongboxRenaming || !strongboxRenameValue.trim()}
                    onclick={submitStrongboxRename}>
                    {strongboxRenaming ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value">{snapshot?.name ?? ''}</div>
                <div class="settings-meta">How this Strongbox appears across TallyKeep.</div>
              </div>
              <button class="settings-cta" type="button" onclick={openStrongboxRename}>Rename</button>
            </div>
          {/if}
        </div>

        <!-- Signing device label -->
        <div class="settings-label">Signing device</div>
        <div class="settings-card">
          {#if showSigningLabelInput}
            <div class="settings-row">
              <div class="rename-form">
                <input
                  class="rename-input"
                  type="text"
                  bind:value={signingLabelValue}
                  maxlength="100"
                  placeholder="e.g. Coldcard Mk4 in safe"
                  aria-label="Signing device label"
                />
                <div class="rename-actions">
                  <button class="settings-cta" type="button"
                    onclick={() => { showSigningLabelInput = false; }}>
                    Cancel
                  </button>
                  <button class="settings-cta settings-cta--primary" type="button"
                    disabled={signingLabelSaving}
                    onclick={submitSigningLabel}>
                    {signingLabelSaving ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                {#if snapshot?.signing_device_label?.trim()}
                  <div class="settings-value">{snapshot.signing_device_label}</div>
                {:else}
                  <div class="settings-value settings-value--not-configured">Not set</div>
                {/if}
                <div class="settings-meta">Your note about where this hardware wallet lives. Shown as the subtitle on this Strongbox's status card.</div>
              </div>
              <button class="settings-cta" type="button" onclick={openSigningLabelEdit}>
                {snapshot?.signing_device_label?.trim() ? 'Edit' : 'Set'}
              </button>
            </div>
          {/if}
        </div>

        <!-- Descriptor -->
        <div class="settings-label">Descriptor</div>
        <div class="settings-card">
          {#if showStrongboxDescriptor}
            <div class="descriptor-revealed">
              <div class="settings-meta">The public-key descriptor TallyKeep watches on the chain. Safe to paste into Sparrow, Specter, or Electrum for an independent view.</div>
              <div class="descriptor-mono-card">{strongboxDescriptors[0]?.expression ?? ''}</div>
              <div class="descriptor-actions">
                <button class="settings-cta" type="button"
                  onclick={() => { showStrongboxDescriptor = false; }}>
                  Hide
                </button>
                <button class="settings-cta" type="button"
                  onclick={copyStrongboxDescriptor}>
                  {strongboxCopied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          {:else}
            <div class="settings-row">
              <div class="settings-body">
                <div class="settings-value settings-value--mono">
                  {strongboxDescriptorMasked(strongboxDescriptors[0]?.expression ?? '')}
                </div>
                <div class="settings-meta">The public-key descriptor TallyKeep watches on the chain.</div>
              </div>
              <button class="settings-cta" type="button"
                onclick={() => { showStrongboxDescriptor = true; }}>
                Show
              </button>
            </div>
          {/if}
        </div>

        <!-- Auto-sweep rules -->
        <div class="settings-label">Auto-sweep rules</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value settings-value--not-configured">None</div>
              <div class="settings-meta">Receive BTC into this Strongbox automatically on a schedule or threshold (e.g. weekly sweep from Kraken).</div>
            </div>
            <button class="settings-cta" type="button"
              onclick={() => goto(`/holding/strongbox/${holdingId}/sweep/add`)}>
              Add rule
            </button>
          </div>
        </div>

        <!-- Instant payments — permanently gated for Strongbox -->
        <div class="settings-label">Instant payments</div>
        <div class="settings-card">
          <div class="settings-row settings-row--gated">
            <div class="settings-body">
              <div class="settings-value">Not available on Strongbox</div>
              <div class="settings-meta">Strongbox keys live on your hardware wallet only. Lightning needs hot keys — activate it on a Spending wallet.</div>
            </div>
            <button class="settings-cta settings-cta--disabled" type="button" aria-disabled="true" disabled>Activate</button>
          </div>
        </div>

        <!-- Danger zone -->
        <div class="settings-label settings-label--danger">Danger zone</div>
        <div class="settings-card">
          <div class="settings-row">
            <div class="settings-body">
              <div class="settings-value">Forget this Strongbox</div>
              <div class="settings-meta">TallyKeep forgets the descriptor and stops scanning the chain. Your hardware wallet and the keys it holds are unaffected. Any categories you've assigned to this Strongbox's activity are erased with it.</div>
            </div>
            <button class="settings-cta settings-cta--danger" type="button"
              onclick={() => { showStrongboxForgetModal = true; }}>
              Forget
            </button>
          </div>
        </div>

      {/if}

    {:else if detail}

      <!-- ── Account: connection-error toast ── -->
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

      <!-- ── Account: status card ── -->
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

      <!-- ── Account: hero balance ── -->
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

      <!-- ── Account: action row ── -->
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

      <!-- ── Account: tab strip ── -->
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

      <!-- ── Account: Operations tab ── -->
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

      <!-- ── Account: Settings tab ── -->
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

        <!-- Display name -->
        <div class="settings-label">Display name</div>
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
                <div class="settings-value">{snapshot?.name ?? ''}</div>
                <div class="settings-meta">How this Account appears across TallyKeep.</div>
              </div>
              <button class="settings-cta" type="button" onclick={openRename}>Rename</button>
            </div>
          {/if}
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

  <!-- ── Account forget modal (fill-bar timer) ── -->
  {#if showRemoveConfirm}
    <div class="modal-backdrop" role="presentation" aria-hidden="true"></div>
    <div class="modal-sheet" role="dialog" aria-modal="true" aria-labelledby="acct-forget-title">
      <div class="drag-handle" aria-hidden="true"></div>
      <h2 id="acct-forget-title" class="modal-title">Forget this Account?</h2>
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
        <button
          class="btn {forgetReady ? 'btn-danger' : `btn-danger-timer${forgetCounting ? ' counting' : ''}`}"
          type="button"
          disabled={!forgetReady || removing}
          aria-disabled={!forgetReady}
          onclick={removeAccount}
        >
          {forgetReady ? (removing ? 'Forgetting…' : 'Forget') : `Forget · ${forgetCountdown}`}
        </button>
      </div>
    </div>
  {/if}

  <!-- ── Strongbox forget modal (fill-bar timer, no seed warning) ── -->
  {#if showStrongboxForgetModal}
    <div class="modal-backdrop" role="presentation" aria-hidden="true"></div>
    <div class="modal-sheet" role="dialog" aria-modal="true" aria-labelledby="strongbox-forget-title">
      <div class="drag-handle" aria-hidden="true"></div>
      <h2 id="strongbox-forget-title" class="modal-title">Forget this Strongbox?</h2>
      <p class="modal-body">
        TallyKeep forgets the descriptor and stops scanning the
        chain. Your hardware wallet and the keys it holds are
        unaffected. Any categories you've assigned to this
        Strongbox's activity are erased with it.
      </p>
      <div class="modal-actions">
        <button class="btn btn-cancel" type="button"
          disabled={strongboxForgetRemoving}
          onclick={() => { showStrongboxForgetModal = false; }}>
          Cancel
        </button>
        <button
          class="btn {strongboxForgetReady ? 'btn-danger' : `btn-danger-timer${strongboxForgetCounting ? ' counting' : ''}`}"
          type="button"
          disabled={!strongboxForgetReady || strongboxForgetRemoving}
          aria-disabled={!strongboxForgetReady}
          onclick={forgetStrongbox}
        >
          {strongboxForgetReady ? (strongboxForgetRemoving ? 'Forgetting…' : 'Forget') : `Forget · ${strongboxForgetCountdown}`}
        </button>
      </div>
    </div>
  {/if}

  <!-- ── Purse forget modal (fill-bar timer) ── -->
  {#if showPurseForgetModal}
    <div class="modal-backdrop" role="presentation" aria-hidden="true"></div>
    <div class="modal-sheet" role="dialog" aria-modal="true" aria-labelledby="purse-forget-title">
      <div class="drag-handle" aria-hidden="true"></div>
      <h2 id="purse-forget-title" class="modal-title">Forget this Purse?</h2>

      {#if snapshot?.purse_mode?.startsWith('on_device')}
        <div class="modal-warning" role="alert">
          You told us you backed up your recovery phrase. Verify your
          backup is intact and you can read it. Once you forget this
          Purse, the keys are destroyed and any forgotten backup is
          gone forever.
        </div>
      {/if}

      {#if purseForgetError}
        <div class="modal-error" role="alert">
          Couldn't delete the on-device keys. The Forget has been
          aborted — your Purse is unchanged. Try again, or restart
          the app and retry.
        </div>
      {/if}

      <p class="modal-body">
        {#if snapshot?.purse_mode?.startsWith('on_device')}
          TallyKeep destroys the keys on this device, forgets the
          descriptor, and stops scanning the chain. Without a working
          backup of your recovery phrase, the funds in this Purse
          become permanently inaccessible. Any categories you've
          assigned to this Purse's activity are erased with it. You
          can re-import this Purse from your recovery phrase, but the
          categorizations don't come back.
        {:else}
          TallyKeep forgets the descriptor and stops scanning the
          chain. Funds at your source wallet are unaffected. Any
          categories you've assigned to this Purse's activity are
          erased with it.
        {/if}
      </p>

      <div class="modal-actions">
        <button class="btn btn-cancel" type="button"
          disabled={purseForgetRemoving}
          onclick={() => { showPurseForgetModal = false; }}>
          Cancel
        </button>
        <button
          class="btn {purseForgetReady ? 'btn-danger' : `btn-danger-timer${purseForgetCounting ? ' counting' : ''}`}"
          type="button"
          disabled={!purseForgetReady || purseForgetRemoving}
          aria-disabled={!purseForgetReady}
          onclick={forgePurse}
        >
          {purseForgetReady ? (purseForgetRemoving ? 'Forgetting…' : 'Forget') : `Forget · ${purseForgetCountdown}`}
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
  .status-card--purse { border-left-color: var(--color-holding-purse); }
  .status-provider {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .status-mode {
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
  .activity-category {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    color: var(--color-text-muted);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-pill);
    padding: 1px var(--space-2);
    margin-top: 4px;
    width: max-content;
    line-height: 1.2;
  }
  .activity-category svg {
    width: 10px; height: 10px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
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
  .settings-row--gated .settings-value,
  .settings-row--gated .settings-meta { color: var(--color-text-dim); }
  .settings-row--gated .settings-value--not-configured { color: var(--color-text-dim); }
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
    word-break: break-all;
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
  .settings-cta--disabled {
    color: var(--color-text-dim);
    border-color: var(--color-border);
    cursor: help;
  }
  .settings-cta--disabled:hover { background: var(--color-bg); }

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

  /* ── Forget modals ── */
  .modal-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 110;
  }
  .modal-sheet {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    background: var(--color-surface);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    padding: var(--space-3) var(--space-5) var(--space-5);
    z-index: 111;
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
  .modal-warning {
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    margin: 0 0 var(--space-3);
    font-size: var(--font-size-sm);
    color: var(--color-danger-text-on-soft);
    line-height: var(--line-height-default);
    font-weight: var(--font-weight-medium);
  }
  .modal-error {
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    margin: 0 0 var(--space-3);
    font-size: var(--font-size-sm);
    color: var(--color-danger-text-on-soft);
    line-height: var(--line-height-default);
    font-weight: var(--font-weight-semibold);
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

  /* Fill-bar countdown timer — coding-agent contract (see mockup):
     Mount without .counting; add .counting on next rAF to trigger
     background-position transition from 100% (soft) to 0% (danger).
     After 5s: swap to .btn-danger class (no snapback). */
  .btn-danger-timer {
    background:
      linear-gradient(to right,
        var(--color-danger) 50%,
        var(--color-danger-soft) 50%);
    background-size: 200% 100%;
    background-position: 100% 0;
    color: var(--color-danger-text-on-soft);
    border: 1px solid var(--color-danger-border);
    transition: background-position 5s linear, color 5s linear;
    cursor: not-allowed;
  }
  .btn-danger-timer.counting {
    background-position: 0% 0;
    color: #ffffff;
  }
  .btn-danger-timer:hover { background-color: transparent; }

  /* ── Strongbox stripe ── */
  .status-card--strongbox { border-left-color: var(--color-holding-strongbox); }

  /* ── Descriptor revealed state ── */
  .descriptor-revealed {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-2) 0;
  }
  .descriptor-mono-card {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    color: var(--color-text);
    letter-spacing: 0.02em;
    word-break: break-all;
    line-height: 1.5;
  }
  .descriptor-actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    justify-content: flex-end;
  }

  /* ── Security-health inline advisory card ── */
  .advisory-card {
    margin: var(--space-4) var(--space-4) 0;
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .advisory-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }
  .advisory-title {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-warning-text-on-soft, #6a4a10);
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }
  .advisory-title svg {
    width: 16px; height: 16px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    flex-shrink: 0;
  }
  .advisory-body {
    font-size: var(--font-size-xs);
    color: var(--color-warning-text-on-soft, #6a4a10);
    line-height: var(--line-height-default);
    margin: 0;
  }
  .advisory-cta {
    background: var(--color-surface);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-family: inherit;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-warning-text-on-soft, #6a4a10);
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .advisory-cta:hover { background: var(--color-warning-soft); }
  .advisory-card + .settings-label { margin-top: var(--space-4); }
</style>
