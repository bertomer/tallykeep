<!--
  WizardShell — reusable 3-step wizard layout shell.
  Used by: Purse wizard (this iteration). Strongbox and Vault wizards inherit.

  Provides: grid app-bar (back | step counter | placeholder), scrollable body
  slot, sticky footer with optional error region + primary CTA.

  The caller owns the content (children snippet) and the error region snippet.
  Step-specific CSS lives in the caller — WizardShell handles structural chrome only.
-->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    stepNumber: number;
    totalSteps?: number;
    showBack?: boolean;
    onBack?: () => void;
    ctaLabel: string;
    loadingLabel?: string;
    ctaDisabled?: boolean;
    loading?: boolean;
    onCta: () => void;
    children: Snippet;
    errorRegion?: Snippet;
  }

  let {
    stepNumber,
    totalSteps = 3,
    showBack = true,
    onBack = () => history.back(),
    ctaLabel,
    loadingLabel = 'Saving…',
    ctaDisabled = false,
    loading = false,
    onCta,
    children,
    errorRegion,
  }: Props = $props();
</script>

<div class="phone-screen safe-top safe-bottom wz-shell">

  <div class="wz-bar">
    {#if showBack}
      <button class="wz-back" aria-label="Go back" onclick={onBack}>
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 6 9 12 15 18"/>
        </svg>
      </button>
    {:else}
      <div></div>
    {/if}
    <div class="wz-step-counter">Step {stepNumber} of {totalSteps}</div>
    <div></div>
  </div>

  <div class="wz-scroll">
    {@render children()}
  </div>

  <div class="wz-footer">
    {#if errorRegion}
      {@render errorRegion()}
    {/if}
    <button
      class="wz-cta"
      class:wz-cta--disabled={ctaDisabled}
      class:wz-cta--loading={loading}
      onclick={onCta}
      disabled={ctaDisabled || loading}
    >
      {#if loading}
        <svg class="wz-spinner" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor"
                  stroke-width="2.5" stroke-linecap="round"
                  stroke-dasharray="28 56" />
        </svg>
        {loadingLabel}
      {:else}
        {ctaLabel}
      {/if}
    </button>
  </div>

</div>

<style>
  .wz-shell {
    background: var(--color-bg);
  }

  .wz-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: grid;
    grid-template-columns: 44px 1fr 44px;
    align-items: center;
    padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }

  .wz-back {
    width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    border-radius: var(--radius-md);
    color: var(--color-text);
    cursor: pointer;
    justify-self: start;
    margin-left: var(--space-2);
  }
  .wz-back:hover { background: var(--color-bg); }
  .wz-back svg { width: 22px; height: 22px; }

  .wz-step-counter {
    text-align: center;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    line-height: 1;
  }

  .wz-scroll {
    flex: 1;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .wz-footer {
    flex-shrink: 0;
    padding: var(--space-3) var(--space-4) var(--space-4);
    background: var(--color-surface);
    border-top: 1px solid var(--color-border);
  }

  .wz-cta {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    background: var(--color-primary);
    color: var(--color-on-primary);
    border: 0;
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
  }
  .wz-cta:hover:not(:disabled) { background: var(--color-primary-strong); }
  .wz-cta:disabled,
  .wz-cta--disabled {
    background: var(--color-border);
    color: var(--color-text-dim);
    cursor: not-allowed;
  }
  .wz-cta--loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    opacity: 0.85;
    cursor: wait;
  }

  @keyframes wz-spin {
    to { transform: rotate(360deg); }
  }
  .wz-spinner {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    animation: wz-spin 0.8s linear infinite;
  }
</style>
