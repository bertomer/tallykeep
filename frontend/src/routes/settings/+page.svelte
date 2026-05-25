<!--
  Settings — coming-soon stub.
  Full design (server URL, passphrase change, pairing, feature flags) ships in a future iteration.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';
  import { securityHealth } from '$lib/stores/security_health.svelte';
  import BottomNav from '$lib/components/BottomNav.svelte';

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
  });
</script>

<div class="phone-screen safe-top safe-bottom">

  <div class="app-bar">
    <a href="/home" class="back-btn" aria-label="Back to Home">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </a>
    <div class="app-bar-title">Settings</div>
    <div></div>
  </div>

  <div class="scroll-area">
    <div class="stub-body">
      <div class="stub-icon-wrap" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </div>
      <h1 class="stub-heading">Settings</h1>
      <p class="stub-body-text">
        Settings — server URL, passphrase change, pairing, and preferences — ships in an upcoming iteration.
      </p>
      <a href="/home" class="stub-cta">Return to Home</a>
    </div>
  </div>

  <BottomNav active="home" criticalCount={securityHealth.openItems.length} />

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
    width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text);
    text-decoration: none;
    justify-self: start;
    margin-left: var(--space-2);
  }
  .back-btn svg {
    width: 22px; height: 22px; stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .app-bar-title {
    text-align: center;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
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
    width: 96px;
    height: 96px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-surface);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
  }
  .stub-icon-wrap svg { width: 52px; height: 52px; color: var(--color-text-muted); }
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
    font-family: var(--font-sans);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    text-decoration: none;
    display: inline-block;
  }
  .stub-cta:hover { background: var(--color-surface); }
</style>
