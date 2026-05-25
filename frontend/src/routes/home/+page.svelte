<!--
  Home — empty state + populated state + security health zone.
  Banking-grade structure: app bar (wordmark + gear), hero balance,
  conditional Security health section, Holdings section, BottomNav.
  Picker sheet opens when ?sheet=add is in the URL.

  Empty state:              specs/UI/mockups/mobile_home_empty.html (validated 2026-05-24)
  Populated state:          specs/UI/mockups/mobile_home_populated.html (validated 2026-05-13, updated 2026-05-24)
  Critical badge:           specs/UI/mockups/mobile_home_populated_security_critical_badge.html (validated 2026-05-24)
  Security health zone:     specs/UI/mockups/mobile_home_populated_security_health_zone.html (validated 2026-05-24)
  Picker:                   specs/UI/mockups/mobile_add_holding_picker.html (validated 2026-05-13)
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { preferences } from '$lib/stores/preferences.svelte';
  import { secureStorage } from '$lib/native-bridge';
  import { securityHealth } from '$lib/stores/security_health.svelte';
  import WordmarkIcony from '$lib/components/WordmarkIcony.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import AddHoldingSheet from '$lib/components/AddHoldingSheet.svelte';

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

  let totalSats = $state(0);
  let holdings = $state<HoldingSummary[]>([]);
  let serverUrl = $state('');
  let acknowledging = $state(false);

  let showPicker = $derived($page.url.searchParams.get('sheet') === 'add');
  let showPrinciplesSheet = $derived($page.url.searchParams.get('open') === 'principles');

  function formatSats(n: number): string {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function formatBtc(sats: number): string {
    return (sats / 1e8).toFixed(8).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function openPicker() {
    goto('?sheet=add');
  }

  function closePicker() {
    goto('?');
  }

  function relativeDate(isoStr: string | null | undefined): string {
    if (!isoStr) return '';
    const d = new Date(isoStr.replace(/(\.\d{3})\d+/, '$1'));
    if (isNaN(d.getTime())) return '';
    const days = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (days === 0) return 'today';
    if (days === 1) return 'yesterday';
    return `${days} days ago`;
  }

  function itemTitle(item: { item_type: string }): string {
    if (item.item_type === 'principles_ack') return 'Acknowledge how TallyKeep works';
    if (item.item_type === 'seed_backup') return 'Back up your recovery phrase';
    if (item.item_type === 'missing_signing_metadata') return 'Missing derivation metadata';
    return item.item_type;
  }

  function itemSummary(item: { item_type: string }): string {
    if (item.item_type === 'principles_ack') return 'You skipped the principles at setup. Take a moment to read them.';
    if (item.item_type === 'seed_backup') return 'Without a backup, losing this device means losing these funds.';
    if (item.item_type === 'missing_signing_metadata') return 'Hardware wallet may refuse to sign without derivation metadata.';
    return '';
  }

  function handleShItemClick(item: { item_type: string; holding_id: string | null }) {
    if (item.item_type === 'principles_ack') {
      goto('?open=principles');
    } else if (item.holding_id) {
      goto(`/holding/${item.holding_id}?tab=settings`);
    }
  }

  async function acknowledgeAndClose() {
    if (acknowledging) return;
    const item = securityHealth.appLevelOpen.find(i => i.item_type === 'principles_ack');
    if (!item) return;
    acknowledging = true;
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/security_health/items/${item.id}/resolve`,
        {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ state: 'acknowledged' }),
        },
      );
      if (resp.ok) {
        await securityHealth.refresh();
        goto('?');
      }
    } catch { /* ignore */ }
    acknowledging = false;
  }

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';

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
    } catch { /* offline — show zeros */ }

    // Init the security health store after we have auth data
    const credential = auth.deviceCredential;
    if (serverUrl && credential) {
      securityHealth.init(serverUrl, credential);
    }
  });
</script>

<div class="phone-screen safe-top safe-bottom">

  <!-- App bar — wordmark left, gear right -->
  <div class="app-bar">
    <WordmarkIcony width={120} />
    <a href="/settings" class="gear-btn" aria-label="Settings">
      <Icon name="gear" size={24} />
    </a>
  </div>

  <!-- Scrollable area -->
  <div class="scroll-area">

    <!-- Hero — consolidated balance, left-aligned -->
    <div class="hero">
      <div class="label-line">Total balance</div>
      <div class="amount-line">
        <span class="amount">
          {preferences.unit === 'sats' ? formatSats(totalSats) : formatBtc(totalSats)}
        </span>
        <span class="unit-label">
          {preferences.unit === 'sats' ? 'sats' : 'BTC'}<button
            class="unit-toggle"
            aria-label="Cycle unit: sats / BTC"
            onclick={preferences.cycleUnit}
          >↻</button>
        </span>
      </div>
      <button class="show-fiat-link">Show in fiat</button>
    </div>

    <!-- Security health section — application-level items only (ADR-0019) -->
    {#if securityHealth.appLevelOpen.length > 0}
      <div class="section-head">
        <span class="section-title">Security health</span>
        {#if securityHealth.appLevelOpen.length > 1}
          <a href="/security-health" class="view-all-link">View all</a>
        {/if}
      </div>
      <ul class="sh-list">
        {#each securityHealth.appLevelOpen as item (item.id)}
          <li>
            <button
              class="sh-row {item.severity}"
              type="button"
              onclick={() => handleShItemClick(item)}
            >
              <span class="sh-dot {item.severity}" aria-hidden="true"></span>
              <span class="sh-body">
                <span class="sh-title">{itemTitle(item)}</span>
                <span class="sh-summary">{itemSummary(item)}</span>
                <span class="sh-date">Opened {relativeDate(item.created_at)}</span>
              </span>
              <span class="sh-chevron" aria-hidden="true">›</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}

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
          <li><button class="holding-row {h.holding_type}" type="button" onclick={() => goto(`/holding/${h.holding_id}`)}>
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
              {preferences.unit === 'sats' ? formatSats(h.confirmed_sats) : formatBtc(h.confirmed_sats)}<span class="unit">{preferences.unit === 'sats' ? 'sats' : 'BTC'}</span>
            </span>
          </button></li>
        {/each}
      </ul>
    {/if}

  </div>

  <BottomNav active="home" criticalCount={securityHealth.openItems.length} />

  <!-- Picker sheet -->
  {#if showPicker}
    <AddHoldingSheet oncancel={closePicker} />
  {/if}

  <!-- Principles-ack bottom-sheet -->
  {#if showPrinciplesSheet}
    <div class="overlay" role="dialog" aria-modal="true" aria-label="How TallyKeep works">
      <button class="overlay-dismiss" onclick={() => goto('?')} aria-label="Close"></button>
      <div class="sheet">
        <div class="sheet-handle" aria-hidden="true"></div>
        <h2 class="sheet-title">How TallyKeep works</h2>
        <ul class="principle-list">
          <li class="principle">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
            <div>
              <div class="principle-label">Open source</div>
              <div class="principle-body">The code is public. Anyone can read it.</div>
            </div>
          </li>
          <li class="principle">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              <line x1="2" y1="2" x2="22" y2="22"/>
            </svg>
            <div>
              <div class="principle-label">No accounts</div>
              <div class="principle-body">We don't know who you are. No email, no profile, no record on our side.</div>
            </div>
          </li>
          <li class="principle">
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <div>
              <div class="principle-label">Your keys stay yours</div>
              <div class="principle-body">They live on this device, on your hardware wallet, or with your custodial provider — never on our servers. If you lose them, we cannot recover them.</div>
            </div>
          </li>
        </ul>
        <div class="summary-block">
          TallyKeep is a tool, not a service. You hold the funds. You hold the keys. You're the one responsible for backing them up and keeping them safe — we can't do that for you and we can't recover what's lost. Tap below to confirm you've read this and you accept it.
        </div>
        <button
          class="cta-primary"
          type="button"
          disabled={acknowledging}
          onclick={acknowledgeAndClose}
        >
          {acknowledging ? 'Saving…' : 'I understand and accept'}
        </button>
      </div>
    </div>
  {/if}

</div>

<style>
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--space-4);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }

  /* Gear icon — 44×44 hit target, 24px glyph, muted stroke */
  .gear-btn {
    width: 44px;
    height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-muted);
    margin-right: -10px;
    text-decoration: none;
  }
  .gear-btn:hover { color: var(--color-text); }

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
  .view-all-link {
    font-size: var(--font-size-xs);
    color: var(--color-primary-strong);
    text-decoration: none;
    font-weight: var(--font-weight-medium);
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

  /* ── Security health section ── */
  .sh-list {
    margin: 0 var(--space-4) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    list-style: none;
    padding: 0;
  }
  .sh-list li { display: block; }
  .sh-row {
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
  .sh-row:last-child { border-bottom: 0; }
  .sh-row.warning  { background: var(--color-warning-soft);  color: var(--color-warning-text-on-soft); }
  .sh-row.critical { background: var(--color-danger-soft);   color: var(--color-danger-text-on-soft); }
  .sh-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .sh-dot.warning  { background: var(--color-warning); }
  .sh-dot.critical { background: var(--color-danger); }
  .sh-body {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .sh-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: inherit;
    line-height: var(--line-height-tight);
  }
  .sh-summary {
    font-size: var(--font-size-xs);
    color: inherit;
    opacity: 0.75;
    line-height: var(--line-height-tight);
  }
  .sh-date {
    font-size: 11px;
    color: inherit;
    opacity: 0.6;
    line-height: var(--line-height-tight);
    margin-top: 2px;
  }
  .sh-chevron {
    color: inherit;
    opacity: 0.6;
    font-size: 18px;
    line-height: 1;
  }

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

  /* ── Principles-ack bottom-sheet ── */
  .overlay {
    position: absolute;
    inset: 0;
    background: var(--color-overlay);
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    z-index: 200;
  }
  .overlay-dismiss {
    flex: 1;
    background: transparent;
    border: 0;
    cursor: pointer;
  }
  .sheet {
    background: var(--color-surface);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    padding: var(--space-3) var(--space-4) var(--space-5);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }
  .sheet-handle {
    width: 36px;
    height: 4px;
    background: var(--color-border-strong);
    border-radius: var(--radius-pill);
    align-self: center;
    margin-bottom: var(--space-3);
  }
  .sheet-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0;
  }
  .principle-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .principle {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
  }
  .ico {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--color-primary-strong);
  }
  .principle-label {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
  }
  .principle-body {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin-top: 2px;
  }
  .summary-block {
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-sm);
    color: var(--color-warning-text-on-soft);
    line-height: var(--line-height-default);
  }
  .cta-primary {
    background: var(--color-primary);
    color: var(--color-on-primary);
    border: 0;
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    font-family: inherit;
  }
  .cta-primary:hover:not(:disabled) { background: var(--color-primary-strong); }
  .cta-primary:disabled { opacity: 0.6; cursor: default; }
</style>
