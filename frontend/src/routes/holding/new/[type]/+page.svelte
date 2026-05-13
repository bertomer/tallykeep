<!--
  Add Holding — coming-soon stub (parameterized by holding type).
  Matches: specs/UI/mockups/mobile_add_holding_coming_soon.html (validated 2026-05-13)
  Back chevron: history.back() → returns to home?sheet=add (picker still open).
  "Return to Home" CTA: goto('/home') → home without picker.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';
  import HoldingIcon from '$lib/components/HoldingIcon.svelte';

  const TYPE_META: Record<string, { name: string; colorClass: string }> = {
    account:   { name: 'Account',   colorClass: 'account' },
    purse:     { name: 'Purse',     colorClass: 'purse' },
    strongbox: { name: 'Strongbox', colorClass: 'strongbox' },
    vault:     { name: 'Vault',     colorClass: 'vault' },
  };

  let holdingType = $derived($page.params.type ?? '');
  let meta = $derived(TYPE_META[holdingType] ?? { name: holdingType, colorClass: '' });

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
  });
</script>

<div class="phone-screen safe-top safe-bottom">

  <!-- App bar: back chevron + centred title -->
  <div class="app-bar">
    <button class="back-btn" aria-label="Back" onclick={() => history.back()}>
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </button>
    <div class="screen-title">Add a {meta.name}</div>
    <div></div>
  </div>

  <!-- Centered stub body -->
  <div class="scroll-area">
    <div class="stub-body">

      <!-- Type icon — 96 px bordered square -->
      <div class="stub-icon-wrap {meta.colorClass}">
        <HoldingIcon type={holdingType} size={72} />
      </div>

      <h1 class="stub-heading">Coming in an upcoming iteration</h1>

      <p class="stub-body-text">
        The {meta.name} onboarding wizard ships shortly. Backend support
        is in place — Holdings can be added via the API for now.
      </p>

      <button class="stub-cta" type="button" onclick={() => goto('/home')}>
        Return to Home
      </button>

    </div>
  </div>

  <BottomNav active="home" />

</div>

<style>
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: grid;
    grid-template-columns: 44px 1fr 44px;
    align-items: center;
    padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }
  .back-btn {
    width: 36px; height: 36px;
    display: inline-flex;
    align-items: center; justify-content: center;
    background: transparent;
    border: 0;
    border-radius: var(--radius-md);
    color: var(--color-text);
    cursor: pointer;
    justify-self: start;
    margin-left: var(--space-2);
  }
  .back-btn:hover { background: var(--color-bg); }
  .back-btn svg { width: 22px; height: 22px; }
  .screen-title {
    text-align: center;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: 1;
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    padding-bottom: var(--mobile-bottom-nav);
  }
  .stub-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-7) var(--space-5);
    gap: var(--space-4);
    text-align: center;
  }

  .stub-icon-wrap {
    width: 96px; height: 96px;
    display: flex; align-items: center; justify-content: center;
    background: var(--color-surface);
    border: 2px solid var(--stub-border, var(--color-border));
    border-radius: var(--radius-lg);
  }
  .stub-icon-wrap.account   { --stub-border: var(--color-holding-account); }
  .stub-icon-wrap.purse     { --stub-border: var(--color-holding-purse); }
  .stub-icon-wrap.strongbox { --stub-border: var(--color-holding-strongbox); }
  .stub-icon-wrap.vault     { --stub-border: var(--color-holding-vault); }
  .stub-icon-wrap :global(svg) { display: block; }

  .stub-heading {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
    margin: 0;
  }
  .stub-body-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 280px;
    margin: 0;
  }
  .stub-cta {
    margin-top: var(--space-3);
    padding: var(--space-3) var(--space-5);
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    cursor: pointer;
  }
  .stub-cta:hover { background: var(--color-surface); }
</style>
