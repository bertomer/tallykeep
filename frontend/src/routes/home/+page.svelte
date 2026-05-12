<!--
  Home — empty state.
  Banking-grade structure: app bar, hero balance, Holdings section w/ empty card, BottomNav.
  Matches: specs/UI/mockups/mobile_home_empty.html (validated 2026-05-10)
-->
<script lang="ts">
  import WordmarkIcony from '$lib/components/WordmarkIcony.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';
  import Icon from '$lib/components/Icon.svelte';

  type Unit = 'sats' | 'btc';
  let unit = $state<Unit>('sats');

  function cycleUnit() {
    unit = unit === 'sats' ? 'btc' : 'sats';
  }
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
        <span class="amount">{unit === 'sats' ? '0' : '0.00000000'}</span>
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
      <button class="add-btn" aria-label="Add a Holding">
        <Icon name="add" size={14} />
      </button>
    </div>
    <div class="list-card-empty">
      No Holdings yet
    </div>

  </div>

  <!-- Bottom nav — home active, activity + holdings disabled -->
  <BottomNav active="home" activityDisabled holdingsDisabled />

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
    font-family: var(--font-mono);
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
    border: 1.5px solid var(--color-primary);
    background: transparent;
    color: var(--color-primary);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 0;
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
</style>
