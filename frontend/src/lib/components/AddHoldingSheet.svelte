<!--
  AddHoldingSheet — bottom sheet picker for adding a Holding.
  Matches: specs/UI/mockups/mobile_add_holding_picker.html (validated 2026-05-13)
  Row order: Account → Purse → Strongbox → Vault (custody-tier progression).
-->
<script lang="ts">
  import { goto } from '$app/navigation';
  import HoldingIcon from '$lib/components/HoldingIcon.svelte';

  let { oncancel }: { oncancel: () => void } = $props();

  function pick(type: string) {
    goto(`/holding/new/${type}`);
  }
</script>

<!-- Scrim — dismiss on tap -->
<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="scrim" aria-hidden="true" onclick={oncancel}></div>

<!-- Sheet -->
<div class="sheet" role="dialog" aria-labelledby="sheet-title" aria-modal="true">
  <div class="sheet-handle" aria-hidden="true"></div>

  <div class="sheet-head">
    <h2 id="sheet-title">Add a Holding</h2>
    <p class="sheet-sub">Each holds your keys differently.</p>
  </div>

  <div class="add-options">

    <!-- Account -->
    <button class="add-option account" type="button" onclick={() => pick('account')}>
      <span class="ao-icon-wrap">
        <HoldingIcon type="account" size={32} />
      </span>
      <span class="ao-text">
        <span class="ao-name">Account</span>
        <span class="ao-desc">Held at an exchange or broker. They hold the keys; you see balances.</span>
      </span>
      <span class="ao-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 6 15 12 9 18"/>
        </svg>
      </span>
    </button>

    <!-- Purse -->
    <button class="add-option purse" type="button" onclick={() => pick('purse')}>
      <span class="ao-icon-wrap">
        <HoldingIcon type="purse" size={32} />
      </span>
      <span class="ao-text">
        <span class="ao-name">Purse</span>
        <span class="ao-desc">On your phone. For daily spending.</span>
      </span>
      <span class="ao-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 6 15 12 9 18"/>
        </svg>
      </span>
    </button>

    <!-- Strongbox -->
    <button class="add-option strongbox" type="button" onclick={() => pick('strongbox')}>
      <span class="ao-icon-wrap">
        <HoldingIcon type="strongbox" size={32} />
      </span>
      <span class="ao-text">
        <span class="ao-name">Strongbox</span>
        <span class="ao-desc">On a hardware wallet. For amounts you spend rarely.</span>
      </span>
      <span class="ao-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 6 15 12 9 18"/>
        </svg>
      </span>
    </button>

    <!-- Vault -->
    <button class="add-option vault" type="button" onclick={() => pick('vault')}>
      <span class="ao-icon-wrap">
        <HoldingIcon type="vault" size={32} />
      </span>
      <span class="ao-text">
        <span class="ao-name">Vault</span>
        <span class="ao-desc">Multiple keys required. For amounts you rarely touch — years, not days.</span>
      </span>
      <span class="ao-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 6 15 12 9 18"/>
        </svg>
      </span>
    </button>

  </div>

  <button class="sheet-cancel" type="button" onclick={oncancel}>Cancel</button>
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    background: var(--color-overlay);
    z-index: 110;
    animation: fade-in 0.15s ease;
  }
  @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

  .sheet {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    background: var(--color-surface);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    padding: var(--space-2) var(--space-4) var(--space-5);
    z-index: 111;
    display: flex;
    flex-direction: column;
    max-height: 88%;
    animation: slide-up 0.22s ease;
    box-shadow: 0 -8px 24px rgba(26, 26, 26, 0.08);
    overflow: hidden; /* cancel stays pinned; options scroll if needed */
  }
  @keyframes slide-up {
    from { transform: translateY(100%); }
    to   { transform: translateY(0); }
  }

  .sheet-handle {
    width: 38px; height: 4px;
    background: var(--color-border-strong);
    border-radius: var(--radius-pill);
    margin: var(--space-2) auto var(--space-4);
    flex-shrink: 0;
  }
  .sheet-head { flex-shrink: 0; margin-bottom: var(--space-4); }
  .sheet-head h2 {
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0 0 var(--space-1);
    letter-spacing: -0.01em;
  }
  .sheet-sub {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: 0;
  }

  .add-options {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    flex: 1;
    overflow-y: auto;
    min-height: 0; /* required for flex child to shrink and scroll */
  }
  .add-option {
    display: grid;
    grid-template-columns: 44px 1fr 16px;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    color: var(--color-text);
    transition: border-color 0.15s ease, background 0.15s ease, transform 0.12s ease;
  }
  .add-option:hover {
    background: var(--color-surface-raised);
    border-color: var(--color-border-strong);
  }
  .add-option:active { transform: scale(0.99); }

  .ao-icon-wrap {
    width: 44px; height: 44px;
    display: flex; align-items: center; justify-content: center;
    background: var(--color-surface);
    border: 2px solid var(--ao-border, var(--color-border));
    border-radius: var(--radius-md);
    flex-shrink: 0;
  }
  .ao-icon-wrap :global(svg) { display: block; }

  .ao-text { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .ao-name {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    line-height: var(--line-height-tight);
    color: var(--color-text);
  }
  .ao-desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: 1.4;
  }
  .ao-arrow {
    color: var(--color-text-dim);
    display: inline-flex;
    align-items: center;
  }
  .ao-arrow svg { width: 16px; height: 16px; }

  .add-option.account   { --ao-border: var(--color-holding-account); }
  .add-option.purse     { --ao-border: var(--color-holding-purse); }
  .add-option.strongbox { --ao-border: var(--color-holding-strongbox); }
  .add-option.vault     { --ao-border: var(--color-holding-vault); }

  .sheet-cancel {
    margin-top: var(--space-4);
    width: 100%;
    padding: var(--space-3) var(--space-4);
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    cursor: pointer;
    flex-shrink: 0;
  }
  .sheet-cancel:hover { background: var(--color-bg); }
</style>
