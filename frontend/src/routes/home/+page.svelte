<!--
  Home — empty state + populated state.
  Banking-grade structure: app bar, hero balance, Holdings section, BottomNav.
  Picker sheet opens when ?sheet=add is in the URL.
  Empty state: specs/UI/mockups/mobile_home_empty.html (validated 2026-05-10)
  Populated state: specs/UI/mockups/mobile_home_populated.html (validated 2026-05-13)
  Picker: specs/UI/mockups/mobile_add_holding_picker.html (validated 2026-05-13)
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { secureStorage } from '$lib/native-bridge';
  import WordmarkIcony from '$lib/components/WordmarkIcony.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import AddHoldingSheet from '$lib/components/AddHoldingSheet.svelte';

  type Unit = 'sats' | 'btc';

  interface HoldingSummary {
    holding_id: string;
    holding_type: string;
    name: string;
    purpose: string;
    confirmed_sats: number;
    descriptor_count: number;
    utxo_count: number;
    is_archived: boolean;
    display_color: string;
    display_order: number;
    meta: string | null;
    scan_status: string;
  }

  let unit = $state<Unit>('sats');
  let totalSats = $state(0);
  let holdings = $state<HoldingSummary[]>([]);
  let serverUrl = $state('');

  let showPicker = $derived($page.url.searchParams.get('sheet') === 'add');

  function cycleUnit() {
    unit = unit === 'sats' ? 'btc' : 'sats';
  }

  function formatSats(n: number): string {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function formatBtc(sats: number): string {
    return (sats / 1e8).toFixed(8).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function openPicker() {
    goto('?sheet=add');
  }

  function closePicker() {
    goto('?');
  }

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';

    // Probe the backend directly — auth.unlocked resets on every browser
    // refresh (it's in-memory only), so we use the API response as ground
    // truth rather than redirecting on every reload.
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/summary/global`, {
        headers: authHeaders(),
      });
      if (resp.ok) {
        auth.markUnlocked();
        const data = await resp.json();
        totalSats = data.total_sats ?? 0;
        holdings = data.holdings ?? [];
      } else if (resp.status === 401) {
        const errData = await resp.json().catch(() => ({}));
        const msg = (errData?.detail ?? '').toLowerCase();
        if (msg.includes('locked') || msg.includes('unlock')) {
          goto('/unlock');
        } else {
          await auth.clearCredential();
          goto('/');
        }
      }
      // Other errors (5xx, offline): keep showing empty state
    } catch { /* offline — show zeros */ }
  });
</script>

<div class="phone-screen safe-top safe-bottom">

  <!-- App bar — small wordmark at left -->
  <div class="app-bar">
    <WordmarkIcony width={120} />
  </div>

  <!-- Scrollable area -->
  <div class="scroll-area">

    <!-- Hero — consolidated balance, left-aligned -->
    <div class="hero">
      <div class="label-line">Total balance</div>
      <div class="amount-line">
        <span class="amount">
          {unit === 'sats' ? formatSats(totalSats) : formatBtc(totalSats)}
        </span>
        <span class="unit-label">
          {unit === 'sats' ? 'sats' : 'BTC'}<button
            class="unit-toggle"
            aria-label="Cycle unit: sats / BTC"
            onclick={cycleUnit}
          >↻</button>
        </span>
      </div>
      <button class="show-fiat-link">Show in fiat</button>
    </div>

    <!-- Holdings section -->
    <div class="section-head">
      <span class="section-title">Holdings</span>
      <button class="add-btn" aria-label="Add a Holding" onclick={openPicker}>
        <Icon name="add" size={14} />
      </button>
    </div>

    {#if holdings.length === 0}
      <div class="list-card-empty">No Holdings yet</div>
    {:else}
      <ul class="holding-list">
        {#each holdings as h (h.holding_id)}
          <li><button class="holding-row {h.holding_type}" type="button">
            <span class="holding-stripe" aria-hidden="true"></span>
            <span class="holding-body">
              <span class="holding-name">{h.name}</span>
              {#if h.meta}
                <span class="holding-meta">{h.meta}</span>
              {:else if h.scan_status === 'scanning'}
                <span class="holding-meta">Scanning…</span>
              {/if}
            </span>
            <span class="holding-amt">
              {unit === 'sats' ? formatSats(h.confirmed_sats) : formatBtc(h.confirmed_sats)}<span class="unit">{unit === 'sats' ? 'sats' : 'BTC'}</span>
            </span>
          </button></li>
        {/each}
      </ul>
    {/if}

  </div>

  <!-- Bottom nav — home active, activity + holdings disabled -->
  <BottomNav active="home" activityDisabled holdingsDisabled />

  <!-- Picker sheet (portal-free — positioned within phone-screen) -->
  {#if showPicker}
    <AddHoldingSheet oncancel={closePicker} />
  {/if}

</div>

<style>
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding: 0 var(--space-4);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    padding-bottom: var(--mobile-bottom-nav);
  }

  /* ── Hero ── */
  .hero {
    flex-shrink: 0;
    padding: var(--space-5) var(--space-4) var(--space-4);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }
  .label-line {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
  }
  .amount-line {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
  }
  .amount {
    font-family: var(--font-sans);
    font-size: 36px;
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .unit-label {
    font-size: var(--font-size-md);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-medium);
    line-height: 1;
  }
  .unit-toggle {
    background: transparent;
    border: none;
    padding: 0 0 0 2px;
    margin: 0;
    font-size: 0.7em;
    vertical-align: super;
    line-height: 1;
    color: var(--color-text-muted);
    cursor: pointer;
    font-family: inherit;
  }
  .unit-toggle:hover { color: var(--color-text); }
  .show-fiat-link {
    background: transparent;
    border: none;
    padding: 0;
    color: var(--color-text-dim);
    font-size: var(--font-size-xs);
    font-family: var(--font-sans);
    cursor: pointer;
    margin-top: var(--space-1);
  }
  .show-fiat-link:hover { color: var(--color-text-muted); }

  /* ── Section header ── */
  .section-head {
    padding: var(--space-3) var(--space-4) var(--space-2);
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }
  .section-title {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .add-btn {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-md);
    border: 0;
    background: var(--color-primary);
    color: var(--color-on-primary);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 0;
  }
  .add-btn:hover { background: var(--color-primary-strong); }

  /* ── Empty placeholder card ── */
  .list-card-empty {
    margin: 0 var(--space-4) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-5) var(--space-4);
    text-align: center;
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
  }

  /* ── Holdings list card ── */
  .holding-list {
    margin: 0 var(--space-4) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    list-style: none;
    padding: 0;
  }
  .holding-list li { display: block; }
  .holding-row {
    display: grid;
    grid-template-columns: 4px 1fr auto;
    align-items: stretch;
    width: 100%;
    border: 0;
    border-bottom: 1px solid var(--color-border);
    background: transparent;
    padding: 0;
    font-family: inherit;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }
  .holding-row:last-child { border-bottom: 0; }
  .holding-row:hover { background: var(--color-surface-raised); }

  .holding-stripe { align-self: stretch; }
  .holding-row.account   .holding-stripe { background: var(--color-holding-account); }
  .holding-row.purse     .holding-stripe { background: var(--color-holding-purse); }
  .holding-row.strongbox .holding-stripe { background: var(--color-holding-strongbox); }
  .holding-row.vault     .holding-stripe { background: var(--color-holding-vault); }

  .holding-body {
    padding: var(--space-3) var(--space-4);
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .holding-name {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .holding-meta {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    line-height: var(--line-height-tight);
  }
  .holding-amt {
    padding: var(--space-3) var(--space-4);
    text-align: right;
    font-family: var(--font-sans);
    font-variant-numeric: tabular-nums;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    white-space: nowrap;
    align-self: center;
  }
  .unit {
    color: var(--color-text-dim);
    font-size: 10px;
    margin-left: var(--space-1);
    font-family: var(--font-sans);
    font-weight: var(--font-weight-normal);
  }
</style>
