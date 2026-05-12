<!--
  DevGate — "Capacitor needed" banner for browser-dev stubs (ADR-0007).

  Mounted at the root layout level and listens for NativeBridge gate events.
  Shows a dismissible bottom banner in DEV mode when a native capability is
  invoked. In production (non-DEV) this component renders nothing.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { onDevGate, DEV_MODE } from '$lib/native-bridge';

  let lastCapability = $state<string | null>(null);
  let visible = $state(false);
  let timer: ReturnType<typeof setTimeout>;

  onMount(() => {
    if (!DEV_MODE) return;
    const unsubscribe = onDevGate((capability) => {
      lastCapability = capability;
      visible = true;
      clearTimeout(timer);
      timer = setTimeout(() => { visible = false; }, 4000);
    });
    return unsubscribe;
  });
</script>

{#if DEV_MODE && visible}
  <div class="dev-gate-banner" role="status" aria-live="polite">
    <span class="label">⚠ Capacitor needed</span>
    <span class="capability">{lastCapability}</span>
    <span class="note">browser build — using dev stub</span>
    <button class="dismiss" onclick={() => { visible = false; }} aria-label="Dismiss">×</button>
  </div>
{/if}

<style>
  .dev-gate-banner {
    position: fixed;
    bottom: calc(var(--mobile-bottom-nav) + var(--space-2));
    left: 50%;
    transform: translateX(-50%);
    max-width: calc(var(--mobile-viewport-width) - var(--space-6));
    width: max-content;
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-warning-text-on-soft);
    z-index: 9999;
    box-shadow: var(--shadow-md);
  }
  .label { font-weight: var(--font-weight-semibold); }
  .capability { font-family: var(--font-mono); }
  .note { color: var(--color-text-muted); }
  .dismiss {
    background: none;
    border: none;
    cursor: pointer;
    font-size: var(--font-size-md);
    color: var(--color-warning-text-on-soft);
    line-height: 1;
    padding: 0 0 0 var(--space-1);
  }
</style>
