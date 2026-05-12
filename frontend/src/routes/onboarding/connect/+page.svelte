<!--
  Onboarding 01 — Connect to your TallyKeep
  Matches: specs/UI/mockups/mobile_onboarding_01_connect.html (validated 2026-05-10)
-->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { preferences } from '$lib/stores/preferences.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { qrScanner } from '$lib/native-bridge';
  import WordmarkIcony from '$lib/components/WordmarkIcony.svelte';
  import DevGate from '$lib/components/DevGate.svelte';

  // State
  let showManualEntry = $state(false);
  let serverUrl = $state('');
  let pairingToken = $state('');
  let errorMessage = $state('');
  let loading = $state(false);

  async function handleQrScan() {
    const result = await qrScanner.scan(); // returns null in browser-dev (gate shown)
    if (result) {
      await redeemFromQr(result);
    }
  }

  function redeemFromQr(qrPayload: string) {
    // Expected QR format: tallykeep://pair?url=<serverUrl>&token=<pairingToken>
    // or a plain URL with query params.
    try {
      const url = new URL(qrPayload);
      const serverParam = url.searchParams.get('url') || `${url.protocol}//${url.host}`;
      const tokenParam = url.searchParams.get('token') || '';
      serverUrl = serverParam;
      pairingToken = tokenParam;
      return handleManualRedeem();
    } catch {
      errorMessage = 'Could not parse the QR code. Try entering the URL manually.';
    }
  }

  async function handleManualRedeem() {
    errorMessage = '';
    loading = true;
    try {
      const baseUrl = serverUrl.replace(/\/$/, '');
      const resp = await fetch(`${baseUrl}/api/v1/pairing/redeem`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pairing_token: pairingToken }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        errorMessage = data.detail ?? `Error ${resp.status}`;
        return;
      }
      const data = await resp.json();

      // Store credential + server URL for subsequent API calls.
      await auth.storePairingResult(data.device_credential, data.device_id);
      import('$lib/native-bridge').then(({ secureStorage }) => {
        secureStorage.set('server_url', baseUrl);
      });

      // Push any pending local acknowledgment to the server now that we have a credential.
      await preferences.syncToBackend(baseUrl, { Authorization: `Bearer ${data.device_credential}` });

      await goto('/onboarding/paired');
    } catch (err) {
      errorMessage = 'Could not connect. Check the URL and try again.';
    } finally {
      loading = false;
    }
  }

  async function acknowledgeAndContinue() {
    await preferences.acknowledgePrinciples();
  }
</script>

<DevGate />

<div class="phone-screen safe-top safe-bottom">

  <!-- Brand strip -->
  <div class="brand-strip">
    <WordmarkIcony width={280} />
  </div>

  <!-- Heading -->
  <div class="heading-block">
    <h1>Connect to your TallyKeep</h1>
    <p class="subtitle">
      Your TallyKeep runs on infrastructure you control.
      Scan the QR your desktop or server is showing.
    </p>
  </div>

  <!-- Scrollable body -->
  <div class="screen-body" style="padding: 0 var(--space-4); display: flex; flex-direction: column; gap: var(--space-3);">

    <!-- QR scan card -->
    {#if !showManualEntry}
      <div class="scan-card">
        <div class="scan-viewfinder">
          <span class="corner tr"></span>
          <span class="corner bl"></span>
          <button
            class="scan-trigger"
            onclick={handleQrScan}
            aria-label="Scan QR code"
          >
            <span class="scan-hint">Point at the QR shown by your TallyKeep</span>
          </button>
        </div>
      </div>

      <div class="secondary-actions">
        <button
          class="btn-block"
          onclick={() => { showManualEntry = true; }}
        >
          Enter server URL manually
        </button>
        <a
          href="https://tallykeep.io/docs/setup"
          target="_blank"
          rel="noopener noreferrer"
          class="btn-block ghost"
        >
          Don't have a TallyKeep yet? <span class="arrow">→</span>
        </a>
      </div>
    {/if}

    <!-- Manual URL entry form -->
    {#if showManualEntry}
      <div class="manual-entry-card">
        <p class="manual-entry-label">Server URL</p>
        <input
          type="url"
          class="input-field"
          placeholder="http://192.168.1.100:8000"
          bind:value={serverUrl}
          autocomplete="url"
          autocorrect="off"
          autocapitalize="none"
          spellcheck="false"
        />
        <p class="manual-entry-label" style="margin-top: var(--space-3);">Pairing token</p>
        <input
          type="text"
          class="input-field"
          placeholder="Paste the token shown on your server"
          bind:value={pairingToken}
          autocomplete="off"
          autocorrect="off"
          autocapitalize="none"
          spellcheck="false"
        />
        {#if errorMessage}
          <p class="error-text">{errorMessage}</p>
        {/if}
        <button
          class="btn-primary"
          disabled={loading || !serverUrl || !pairingToken}
          onclick={handleManualRedeem}
        >
          {loading ? 'Connecting…' : 'Connect'}
        </button>
        <button
          class="btn-block ghost"
          style="margin-top: var(--space-1);"
          onclick={() => { showManualEntry = false; errorMessage = ''; }}
        >
          ← Back to QR scan
        </button>
      </div>
    {/if}

  </div>

  <!-- Principles disclosure — footer acknowledgment card -->
  {#if !preferences.principlesAcknowledged}
    <div class="principles-card">
      <div class="title">How TallyKeep works</div>
      <ul class="principles-list">
        <li><span><strong>Open source.</strong> Every line auditable.</span></li>
        <li><span><strong>No accounts.</strong> Never required, anywhere.</span></li>
        <li><span><strong>Your keys stay yours.</strong> TallyKeep never holds them.</span></li>
      </ul>
      <button class="ack-btn" onclick={acknowledgeAndContinue}>I understand</button>
    </div>
  {/if}

</div>

<style>
  .brand-strip {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-5) var(--space-4) var(--space-3);
  }

  .heading-block {
    flex-shrink: 0;
    padding: var(--space-3) var(--space-5) var(--space-4);
    text-align: center;
  }
  .heading-block h1 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    line-height: var(--line-height-tight);
    color: var(--color-text);
    margin: 0 0 var(--space-2);
  }
  .subtitle {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: 0;
  }

  .scan-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
  }
  .scan-viewfinder {
    width: 100%;
    aspect-ratio: 1 / 1;
    max-height: 200px;
    background: #1a1a1a;
    border-radius: var(--radius-md);
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  /* Corner brackets */
  .scan-viewfinder::before,
  .scan-viewfinder::after {
    content: '';
    position: absolute;
    width: 28px;
    height: 28px;
    border-color: var(--color-on-primary);
    border-style: solid;
    pointer-events: none;
  }
  .scan-viewfinder::before {
    top: 12px; left: 12px;
    border-width: 2px 0 0 2px;
    border-top-left-radius: var(--radius-sm);
  }
  .scan-viewfinder::after {
    bottom: 12px; right: 12px;
    border-width: 0 2px 2px 0;
    border-bottom-right-radius: var(--radius-sm);
  }
  .corner {
    position: absolute;
    width: 28px;
    height: 28px;
    border-color: var(--color-on-primary);
    border-style: solid;
    pointer-events: none;
  }
  .corner.tr { top: 12px; right: 12px; border-width: 2px 2px 0 0; border-top-right-radius: var(--radius-sm); }
  .corner.bl { bottom: 12px; left: 12px; border-width: 0 0 2px 2px; border-bottom-left-radius: var(--radius-sm); }

  .scan-trigger {
    background: none;
    border: none;
    cursor: pointer;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .scan-hint {
    color: var(--color-on-primary);
    font-size: var(--font-size-xs);
    text-align: center;
    padding: 0 var(--space-4);
    line-height: var(--line-height-default);
    pointer-events: none;
  }

  .secondary-actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .btn-block {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-sm);
    font-family: var(--font-sans);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-strong);
    background: var(--color-surface);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
    text-align: center;
    cursor: pointer;
    line-height: var(--line-height-default);
    text-decoration: none;
    display: block;
  }
  .btn-block.ghost {
    background: transparent;
    border-color: transparent;
    color: var(--color-text-muted);
    font-weight: var(--font-weight-normal);
    font-size: var(--font-size-xs);
    padding: var(--space-2);
  }
  .btn-primary {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-sm);
    font-family: var(--font-sans);
    border-radius: var(--radius-md);
    border: none;
    background: var(--color-primary);
    color: var(--color-on-primary);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    margin-top: var(--space-4);
  }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .manual-entry-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    display: flex;
    flex-direction: column;
  }
  .manual-entry-label {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 var(--space-1);
  }
  .input-field {
    width: 100%;
    padding: var(--space-2) var(--space-3);
    font-size: var(--font-size-sm);
    font-family: var(--font-mono);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    outline: none;
  }
  .input-field:focus { border-color: var(--color-border-focus); }
  .error-text {
    color: var(--color-danger);
    font-size: var(--font-size-xs);
    margin: var(--space-2) 0 0;
  }

  /* Principles card */
  .principles-card {
    flex-shrink: 0;
    background: var(--color-sidebar);
    border-top: 1px solid var(--color-border);
    padding: var(--space-3) var(--space-4);
  }
  .principles-card .title {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--space-2);
  }
  .principles-list {
    list-style: none;
    margin: 0 0 var(--space-3);
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .principles-list li {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .principles-list li::before {
    content: '·';
    color: var(--color-primary);
    font-weight: var(--font-weight-bold);
    flex-shrink: 0;
  }
  .principles-list strong { color: var(--color-text); font-weight: var(--font-weight-semibold); }
  .ack-btn {
    display: block;
    width: 100%;
    padding: var(--space-2) var(--space-3);
    font-family: var(--font-sans);
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    cursor: pointer;
  }
</style>
