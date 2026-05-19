<!-- Purse · Receive — coming-soon stub -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
  });
</script>

<div class="phone-screen safe-top safe-bottom">
  <div class="app-bar">
    <button class="back-btn" aria-label="Back" onclick={() => history.back()}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </button>
    <div class="app-bar-title">Receive</div>
    <div></div>
  </div>
  <div class="stub-body">
    <h1 class="stub-heading">Receive BTC</h1>
    <h2 class="stub-subheading">Coming in an upcoming iteration</h2>
    <p class="stub-text">Address generation and QR display ship in the Receive iteration.</p>
    <button class="stub-cta" type="button" onclick={() => history.back()}>Go back</button>
  </div>
</div>

<style>
  .phone-screen { background: var(--color-bg); position: relative; }
  .app-bar {
    height: var(--mobile-app-bar); flex-shrink: 0;
    display: grid; grid-template-columns: 44px 1fr 44px;
    align-items: center; padding: 0 var(--space-2);
    background: var(--color-surface); border-bottom: 1px solid var(--color-border);
  }
  .back-btn {
    width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
    background: transparent; border: 0; border-radius: var(--radius-md);
    color: var(--color-text); cursor: pointer; justify-self: start; margin-left: var(--space-2);
  }
  .back-btn:hover { background: var(--color-bg); }
  .back-btn svg { width: 22px; height: 22px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .app-bar-title { text-align: center; font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); color: var(--color-text); }
  .stub-body { display: flex; flex-direction: column; align-items: center; text-align: center; padding: var(--space-8) var(--space-5); gap: var(--space-3); }
  .stub-heading { font-size: var(--font-size-xl); font-weight: var(--font-weight-semibold); color: var(--color-text); margin: 0; }
  .stub-subheading { font-size: var(--font-size-base); font-weight: var(--font-weight-medium); color: var(--color-text-muted); margin: 0; }
  .stub-text { font-size: var(--font-size-sm); color: var(--color-text-muted); line-height: var(--line-height-default); max-width: 280px; margin: 0; }
  .stub-cta { margin-top: var(--space-3); padding: var(--space-3) var(--space-5); background: var(--color-primary); color: var(--color-on-primary); border: 0; border-radius: var(--radius-md); font-family: inherit; font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); cursor: pointer; }
  .stub-cta:hover { background: var(--color-primary-strong); }
</style>
