<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';

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
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </button>
    <div class="app-bar-title">Fix signing metadata</div>
    <div></div>
  </div>

  <div class="scroll-area">
    <div class="stub-body">
      <div class="stub-icon-wrap" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M 12 3 L 22 20 L 2 20 Z"/>
          <line x1="12" y1="10" x2="12" y2="14"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <h1 class="stub-heading">Fix derivation metadata</h1>
      <h2 class="stub-subheading">Coming in an upcoming iteration</h2>
      <p class="stub-body-text">
        The metadata remediation flow — re-importing with full origin
        info or manually entering fingerprint and derivation path —
        ships with the Security-health iteration.
      </p>
      <button class="stub-cta" type="button" onclick={() => history.back()}>
        Back
      </button>
    </div>
  </div>

</div>

<style>
  .phone-screen { background: var(--color-bg); position: relative; }
  .app-bar {
    height: var(--mobile-app-bar); flex-shrink: 0;
    display: grid; grid-template-columns: 44px 1fr 44px;
    align-items: center; padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    position: relative; z-index: 2;
  }
  .back-btn {
    width: 36px; height: 36px;
    display: inline-flex; align-items: center; justify-content: center;
    background: transparent; border: 0; border-radius: var(--radius-md);
    color: var(--color-text); cursor: pointer;
    justify-self: start; margin-left: var(--space-2);
  }
  .back-btn:hover { background: var(--color-bg); }
  .back-btn svg {
    width: 22px; height: 22px; stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .app-bar-title {
    text-align: center; font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold); color: var(--color-text);
  }
  .scroll-area { flex: 1; overflow-y: auto; }
  .stub-body {
    display: flex; flex-direction: column; align-items: center;
    text-align: center; padding: var(--space-8) var(--space-5) var(--space-5);
    gap: var(--space-3);
  }
  .stub-icon-wrap {
    width: 64px; height: 64px; border-radius: var(--radius-lg);
    background: var(--color-surface); border: 1px solid var(--color-border);
    display: inline-flex; align-items: center; justify-content: center;
    margin-bottom: var(--space-2);
  }
  .stub-icon-wrap svg { width: 32px; height: 32px; color: var(--color-warning, #d97706); }
  .stub-heading {
    font-size: var(--font-size-xl); font-weight: var(--font-weight-semibold);
    color: var(--color-text); margin: 0;
  }
  .stub-subheading {
    font-size: var(--font-size-base); font-weight: var(--font-weight-medium);
    color: var(--color-text-muted); margin: 0;
  }
  .stub-body-text {
    font-size: var(--font-size-sm); color: var(--color-text-muted);
    line-height: var(--line-height-default); max-width: 280px; margin: 0;
  }
  .stub-cta {
    margin-top: var(--space-3); padding: var(--space-3) var(--space-5);
    background: var(--color-primary); color: var(--color-on-primary);
    border: 0; border-radius: var(--radius-md); font-family: inherit;
    font-size: var(--font-size-base); font-weight: var(--font-weight-semibold);
    cursor: pointer;
  }
  .stub-cta:hover { background: var(--color-primary-strong); }
</style>
