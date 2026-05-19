<!--
  Purse detail · Send
  Mockup contract (validated 2026-05-19):
    mobile_purse_detail_send_blocked_watch_only.html

  Routing:
    WATCH_ONLY  → send-blocked screen (this mockup)
    ON_DEVICE_* → coming-soon stub (Send iteration)
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { secureStorage } from '$lib/native-bridge';

  interface HoldingSnapshot {
    id: string;
    holding_type: string;
    name: string;
    purse_mode: string | null;
  }

  let holdingId = $derived($page.params.id ?? '');
  let serverUrl = $state('');
  let snapshot = $state<HoldingSnapshot | null>(null);

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';
    if (!serverUrl || !holdingId) return;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/holdings/${holdingId}`, {
        headers: authHeaders(),
      });
      if (resp.ok) snapshot = await resp.json();
    } catch { /* offline */ }
  });
</script>

<div class="phone-screen safe-top safe-bottom">

  <div class="app-bar">
    <button class="back-btn" aria-label="Back to {snapshot?.name ?? 'Purse'}"
      onclick={() => history.back()}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="15 6 9 12 15 18"/>
      </svg>
    </button>
    <div class="app-bar-title">Send</div>
    <div></div>
  </div>

  <div class="scroll-area">

    {#if !snapshot}
      <!-- Loading skeleton -->
      <div class="loading-placeholder" aria-label="Loading…">
        <div class="skel skel-hero"></div>
        <div class="skel skel-card"></div>
        <div class="skel skel-card"></div>
      </div>

    {:else if snapshot.purse_mode === 'watch_only'}

      <!-- Send-blocked screen: WATCH_ONLY -->
      <div class="send-hero">
        <h1 class="title">Keys aren't on this device</h1>
        <p class="body">
          You added this Purse by importing a descriptor, so
          TallyKeep watches the wallet but doesn't hold its
          keys. To spend, the signing has to happen where the
          keys live.
        </p>
      </div>

      <div class="options-section-label">Pick how you want to sign</div>

      <button class="option-card" type="button"
        onclick={() => goto(`/holding/purse/${holdingId}/psbt-export`)}>
        <span class="option-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <rect x="3" y="3"  width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <line x1="14" y1="14" x2="17" y2="14"/>
            <line x1="14" y1="17" x2="14" y2="20"/>
            <line x1="17" y1="17" x2="21" y2="17"/>
            <line x1="20" y1="20" x2="21" y2="20"/>
          </svg>
        </span>
        <span class="option-body">
          <span class="option-title">Sign with your source wallet</span>
          <span class="option-desc">TallyKeep builds a payment for your source wallet to sign and broadcast. You'll scan a QR with your wallet app.</span>
        </span>
        <span class="option-chevron" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <polyline points="9 6 15 12 9 18"/>
          </svg>
        </span>
      </button>

      <button class="option-card" type="button"
        onclick={() => goto(`/holding/purse/${holdingId}/add-keys`)}>
        <span class="option-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <circle cx="9" cy="14" r="4"/>
            <line x1="12" y1="11" x2="20" y2="3"/>
            <line x1="17" y1="6" x2="20" y2="9"/>
            <line x1="14" y1="9" x2="17" y2="12"/>
          </svg>
        </span>
        <span class="option-body">
          <span class="option-title">Add the keys to this Purse</span>
          <span class="option-desc">Import the recovery phrase from your source wallet so TallyKeep can sign payments here directly.</span>
        </span>
        <span class="option-chevron" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <polyline points="9 6 15 12 9 18"/>
          </svg>
        </span>
      </button>

    {:else}

      <!-- Coming-soon for ON_DEVICE Send -->
      <div class="stub-body">
        <div class="stub-icon-wrap" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <line x1="5" y1="15" x2="19" y2="15"/>
            <line x1="12" y1="9" x2="12" y2="2"/>
            <polyline points="8 6 12 2 16 6"/>
          </svg>
        </div>
        <h1 class="stub-heading">Send BTC</h1>
        <h2 class="stub-subheading">Coming in an upcoming iteration</h2>
        <p class="stub-body-text">
          Native on-device signing, amount entry, address validation, and
          fee selection ship in the Send iteration.
        </p>
        <button class="stub-cta" type="button" onclick={() => history.back()}>
          Back to {snapshot.name}
        </button>
      </div>

    {/if}

  </div>

</div>

<style>
  .phone-screen { background: var(--color-bg); position: relative; }

  /* ── App bar ── */
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: grid;
    grid-template-columns: 44px 1fr 44px;
    align-items: center;
    padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    position: relative;
    z-index: 2;
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
  .back-btn svg {
    width: 22px; height: 22px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .app-bar-title {
    text-align: center;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }

  /* ── Scroll area ── */
  .scroll-area { flex: 1; overflow-y: auto; }

  /* ── Send-hero ── */
  .send-hero {
    padding: var(--space-6) var(--space-5) var(--space-4);
    text-align: left;
  }
  .send-hero .title {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0 0 var(--space-3);
    line-height: var(--line-height-tight);
  }
  .send-hero .body {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: 0;
  }

  /* ── Options section ── */
  .options-section-label {
    margin: var(--space-4) var(--space-5) var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
  }
  .option-card {
    display: grid;
    grid-template-columns: 40px 1fr 18px;
    align-items: center;
    gap: var(--space-3);
    margin: 0 var(--space-4) var(--space-3);
    padding: var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    width: calc(100% - var(--space-4) * 2);
  }
  .option-card:hover {
    background: var(--color-surface-raised);
    border-color: var(--color-border-strong);
  }
  .option-icon {
    width: 40px; height: 40px;
    border-radius: var(--radius-md);
    background: var(--color-primary-soft);
    color: var(--color-primary-strong);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .option-icon svg {
    width: 22px; height: 22px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .option-body {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .option-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
  }
  .option-desc {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
  }
  .option-chevron {
    width: 18px; height: 18px;
    color: var(--color-text-dim);
  }
  .option-chevron svg {
    width: 18px; height: 18px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }

  /* ── Loading skeleton ── */
  .loading-placeholder { padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }
  .skel {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    animation: pulse 1.5s ease-in-out infinite;
  }
  .skel-hero { height: 120px; }
  .skel-card { height: 80px; }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* ── Coming-soon stub (ON_DEVICE) ── */
  .stub-body {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--space-8) var(--space-5) var(--space-5);
    gap: var(--space-3);
  }
  .stub-icon-wrap {
    width: 64px; height: 64px;
    border-radius: var(--radius-lg);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-2);
  }
  .stub-icon-wrap svg {
    width: 32px; height: 32px;
    color: var(--color-text-muted);
  }
  .stub-heading {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0;
  }
  .stub-subheading {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-muted);
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
