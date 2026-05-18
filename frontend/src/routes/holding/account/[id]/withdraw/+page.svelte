<!--
  Withdraw out — coming-soon stub.
  Reached from the Account detail page "Withdraw out" action card.
  The full two-key withdrawal flow (withdrawal credential, whitelist address,
  signed transaction) is a future iteration.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';

  let holdingId = $derived($page.params.id ?? '');

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
  });
</script>

<div class="phone-screen safe-top safe-bottom">

  <div class="app-bar">
    <button class="back-btn" aria-label="Back" onclick={() => history.back()}>
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </button>
    <div class="screen-title">Withdraw out</div>
    <div></div>
  </div>

  <div class="scroll-area">
    <div class="stub-body">

      <div class="stub-icon-wrap" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/>
          <polyline points="5 12 12 5 19 12"/>
        </svg>
      </div>

      <h1 class="stub-heading">Withdraw out</h1>
      <h2 class="stub-subheading">Coming in an upcoming iteration</h2>

      <p class="stub-body-text">
        Withdrawals from your exchange Account to a self-custody Holding will
        be initiated here. The full two-key setup — withdrawal credential,
        whitelisted destination address, and signed transaction — ships in the
        next design pass.
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
    display: inline-flex; align-items: center; justify-content: center;
    background: transparent; border: 0;
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
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-6) var(--space-5);
  }

  .stub-body {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--space-3);
    max-width: 300px;
  }

  .stub-icon-wrap {
    width: 80px; height: 80px;
    display: flex; align-items: center; justify-content: center;
    border: 2px solid var(--color-holding-account);
    border-radius: var(--radius-lg);
    color: var(--color-holding-account);
  }
  .stub-icon-wrap svg { width: 40px; height: 40px; }

  .stub-heading {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0;
    line-height: var(--line-height-tight);
  }
  .stub-subheading {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-muted);
    margin: 0;
  }

  .stub-body-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: 0;
  }

  .stub-cta {
    margin-top: var(--space-3);
    padding: var(--space-3) var(--space-5);
    background: var(--color-primary);
    color: var(--color-on-primary);
    border: 0;
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
  }
  .stub-cta:hover { background: var(--color-primary-strong); }
</style>
