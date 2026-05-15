<!--
  Holding detail — placeholder.
  Spec: next_iteration.md task 9 — "tapping a Vault row routes to a minimal
  placeholder page; explicit detail design is deferred to its own iteration."
  Applies to all holding types; the detailed design ships per-type later.
-->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
</script>

<div class="screen">
  <div class="app-bar">
    <button class="back-btn" type="button" aria-label="Back" onclick={() => history.back()}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="15 18 9 12 15 6"/>
      </svg>
    </button>
    <span class="bar-title">Holding</span>
    <span></span>
  </div>

  <div class="body">
    <p class="coming-soon">Detail view coming soon.</p>
    <button class="home-btn" type="button" onclick={() => goto('/home')}>Back to Home</button>
  </div>
</div>

<style>
  .screen {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    background: var(--color-bg);
  }
  .app-bar {
    height: var(--mobile-app-bar, 52px);
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
  }
  .back-btn:hover { background: var(--color-bg); }
  .back-btn svg {
    width: 22px; height: 22px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .bar-title {
    text-align: center;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .body {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-5);
    padding: var(--space-6);
    text-align: center;
  }
  .coming-soon {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    margin: 0;
  }
  .home-btn {
    padding: var(--space-3) var(--space-5);
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    cursor: pointer;
  }
  .home-btn:hover { background: var(--color-bg); }
</style>
