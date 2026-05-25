<!--
  Fix derivation metadata — two paths:
    Path A (default): re-export descriptor from hardware wallet
    Path B: manual fingerprint + derivation path entry
  Reached from the dashboard's missing-metadata row or from a
  Holding detail Settings tab "Fix this" CTA.
  Route param [id] is the holding_id.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { securityHealth } from '$lib/stores/security_health.svelte';
  import { secureStorage } from '$lib/native-bridge';

  const holdingId = $derived($page.params.id);

  let serverUrl = $state('');
  let path = $state<'reexport' | 'manual'>('reexport');

  // Item lookup (to get holding name, vendor, item_id)
  let itemId = $state<string | null>(null);
  let holdingName = $state('');
  let vendor = $state('');

  // Path A state
  let descriptorText = $state('');
  let submittingA = $state(false);
  let errorA = $state('');

  // Path B state
  let fingerprint = $state('');
  let derivPathChoice = $state("m/84'/0'/0'");
  let customPath = $state('');
  let submittingB = $state(false);
  let errorB = $state('');

  // Dismiss state
  let dismissing = $state(false);

  const DERIV_OPTIONS = [
    { label: "BIP 84 — m/84'/0'/0' (Native SegWit, default)", value: "m/84'/0'/0'" },
    { label: "BIP 49 — m/49'/0'/0' (Nested SegWit)",          value: "m/49'/0'/0'" },
    { label: "BIP 44 — m/44'/0'/0' (Legacy)",                 value: "m/44'/0'/0'" },
    { label: "BIP 86 — m/86'/0'/0' (Taproot)",                value: "m/86'/0'/0'" },
    { label: "Custom…",                                         value: "custom" },
  ];

  const VENDOR_HINTS: Record<string, { title: string; steps: string[] }> = {
    coldcard: {
      title: 'On your Coldcard',
      steps: [
        "Open the wallet's address book.",
        "Choose Export → Generic JSON (or Sparrow descriptor).",
        "Save to SD or paste over USB. The export string starts with <code>[fingerprint/derivation]</code>.",
      ],
    },
    trezor: {
      title: 'On your Trezor',
      steps: [
        "Open Trezor Suite and select the account.",
        "Go to Account details → Show public key.",
        "Copy the xPub or use Export → Descriptor format.",
      ],
    },
    ledger: {
      title: 'On your Ledger',
      steps: [
        "Open Ledger Live and go to the account.",
        "Settings → Advanced → Export account.",
        "The descriptor includes the full derivation origin.",
      ],
    },
  };

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }

    serverUrl = (await secureStorage.get('server_url')) ?? '';
    const credential = auth.deviceCredential ?? '';
    if (serverUrl && credential) {
      securityHealth.init(serverUrl, credential);
    }

    // Find the open item for this holding
    const item = securityHealth.openItems.find(
      i => i.holding_id === holdingId && i.item_type === 'missing_signing_metadata'
    );
    if (item) {
      itemId = item.id;
      holdingName = (item.raw_context?.holding_name as string) ?? '';
      vendor = ((item.raw_context?.vendor as string) ?? '').toLowerCase();
    } else {
      // Fetch from API if not in store (direct navigation)
      try {
        const resp = await fetch(
          `${serverUrl}/api/v1/security_health/items?state=open`,
          { headers: authHeaders() },
        );
        if (resp.ok) {
          const items = await resp.json();
          const found = items.find(
            (i: { holding_id: string; item_type: string }) =>
              i.holding_id === holdingId && i.item_type === 'missing_signing_metadata'
          );
          if (found) {
            itemId = found.id;
            holdingName = (found.raw_context?.holding_name as string) ?? '';
            vendor = ((found.raw_context?.vendor as string) ?? '').toLowerCase();
          }
        }
      } catch { /* offline */ }
    }
  });

  const vendorHint = $derived(vendor && VENDOR_HINTS[vendor] ? VENDOR_HINTS[vendor] : null);
  const canSubmitA = $derived(descriptorText.trim().length > 10 && !submittingA);
  const fingerprintValid = $derived(/^[0-9a-fA-F]{8}$/.test(fingerprint));
  const effectivePath = $derived(derivPathChoice === 'custom' ? customPath : derivPathChoice);
  const customPathValid = $derived(/^m(\/\d+'?)*$/.test(customPath));
  const canSubmitB = $derived(
    fingerprintValid &&
    (derivPathChoice !== 'custom' || customPathValid) &&
    !submittingB
  );

  async function submitReexport() {
    if (!canSubmitA) return;
    submittingA = true;
    errorA = '';
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/security_health/fix_metadata/${holdingId}/reexport`,
        {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ descriptor_expression: descriptorText.trim(), network: 'mainnet' }),
        },
      );
      const data = await resp.json();
      if (data.success) {
        goto('/security-health');
      } else {
        errorA = data.error ?? 'Verification failed.';
      }
    } catch {
      errorA = 'Network error — please try again.';
    }
    submittingA = false;
  }

  async function submitManual() {
    if (!canSubmitB) return;
    submittingB = true;
    errorB = '';
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/security_health/fix_metadata/${holdingId}/manual`,
        {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({
            master_fingerprint: fingerprint.toLowerCase(),
            derivation_path: effectivePath,
            network: 'mainnet',
          }),
        },
      );
      const data = await resp.json();
      if (data.success) {
        goto('/security-health');
      } else {
        errorB = data.error ?? 'Verification failed.';
      }
    } catch {
      errorB = 'Network error — please try again.';
    }
    submittingB = false;
  }

  async function markIntentional() {
    if (!itemId || dismissing) return;
    dismissing = true;
    try {
      const resp = await fetch(
        `${serverUrl}/api/v1/security_health/items/${itemId}/resolve`,
        {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ state: 'dismissed_intentional', dismissal_reason: null }),
        },
      );
      if (resp.ok) {
        goto('/security-health');
      }
    } catch { /* ignore */ }
    dismissing = false;
  }

  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) descriptorText = text;
    } catch { /* denied */ }
  }

  let fileInput = $state<HTMLInputElement | null>(null);
  function triggerUpload() { fileInput?.click(); }
  function handleFileChange(evt: Event) {
    const file = (evt.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => { descriptorText = (e.target?.result as string) ?? ''; };
    reader.readAsText(file);
  }
</script>

<div class="phone-screen safe-top safe-bottom">

  <div class="app-bar">
    <button
      class="app-bar-back"
      type="button"
      aria-label="Back"
      onclick={() => { if (path === 'manual') { path = 'reexport'; errorB = ''; } else { window.history.back(); } }}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="15 18 9 12 15 6"/>
      </svg>
    </button>
    <span class="app-bar-title">Fix derivation metadata</span>
    <div style="width:44px"></div>
  </div>

  <!-- Path A: Re-export -->
  {#if path === 'reexport'}
    <div class="scroll-area">

      <p class="page-intro">
        Re-export the descriptor from your hardware wallet with full origin metadata, then paste it below.
        TallyKeep will verify it matches <strong>{holdingName || 'this wallet'}</strong> and update the record in place.
      </p>

      {#if vendorHint}
        <div class="vendor-hint">
          <span class="hint-title">{vendorHint.title}</span>
          <ol>
            {#each vendorHint.steps as step}
              <li>{@html step}</li>
            {/each}
          </ol>
        </div>
      {/if}

      <div class="input-card">
        <span class="input-label">Re-exported descriptor</span>
        <textarea
          class="input-textarea"
          placeholder="Paste the export here, e.g. wpkh([abc12345/84'/0'/0']zpub…)"
          bind:value={descriptorText}
        ></textarea>
        <div class="triad">
          <button class="triad-btn" type="button" onclick={pasteFromClipboard}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            Paste
          </button>
          <button class="triad-btn" type="button" onclick={triggerUpload}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload
          </button>
          <button class="triad-btn" type="button" disabled>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="3" width="7" height="7"/>
              <rect x="14" y="3" width="7" height="7"/>
              <rect x="14" y="14" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/>
            </svg>
            Scan QR
          </button>
        </div>
      </div>

      {#if errorA}
        <div class="error-msg">{errorA}</div>
      {/if}

      <button
        class="cta-primary"
        type="button"
        disabled={!canSubmitA}
        onclick={submitReexport}
      >
        {submittingA ? 'Verifying…' : 'Verify and update'}
      </button>

      <button class="secondary-link" type="button" onclick={() => { path = 'manual'; errorA = ''; }}>
        Enter manually instead
      </button>

      {#if itemId}
        <button class="danger-link" type="button" disabled={dismissing} onclick={markIntentional}>
          {dismissing ? 'Saving…' : 'Mark as intentional · skip the fix'}
        </button>
      {/if}

    </div>

    <!-- hidden file input -->
    <input
      bind:this={fileInput}
      type="file"
      accept=".txt,.json"
      style="display:none"
      onchange={handleFileChange}
    />
  {/if}

  <!-- Path B: Manual -->
  {#if path === 'manual'}
    <div class="scroll-area">

      <p class="page-intro">
        Enter the metadata directly. TallyKeep will derive the first addresses with these values
        and compare them against the ones it's already watching for <strong>{holdingName || 'this wallet'}</strong>.
        The fix only goes through if they match.
      </p>

      <div class="input-card">
        <span class="input-label">Master fingerprint</span>
        <input
          class="input-text"
          class:invalid={fingerprint.length > 0 && !fingerprintValid}
          type="text"
          placeholder="e.g. a1b2c3d4"
          maxlength="8"
          bind:value={fingerprint}
          autocomplete="off"
          autocorrect="off"
          autocapitalize="none"
          spellcheck={false}
        />
        <span class="input-help">8 hex characters from the wallet's root metadata. Case-insensitive.</span>
      </div>

      <div class="input-card">
        <span class="input-label">Derivation path</span>
        <select class="input-select" bind:value={derivPathChoice}>
          {#each DERIV_OPTIONS as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
        {#if derivPathChoice === 'custom'}
          <input
            class="input-text"
            class:invalid={customPath.length > 0 && !customPathValid}
            type="text"
            placeholder="e.g. m/84'/0'/0'"
            bind:value={customPath}
            autocomplete="off"
            autocorrect="off"
            autocapitalize="none"
            spellcheck={false}
          />
        {/if}
        <span class="input-help">Matches the script type used when you set up the wallet.</span>
      </div>

      {#if errorB}
        <div class="error-msg">{errorB}</div>
      {/if}

      <button
        class="cta-primary"
        type="button"
        disabled={!canSubmitB}
        onclick={submitManual}
      >
        {submittingB ? 'Verifying…' : 'Verify and update'}
      </button>

      <button class="secondary-link" type="button" onclick={() => { path = 'reexport'; errorB = ''; }}>
        Re-export from the wallet instead
      </button>

    </div>
  {/if}

</div>

<style>
  .app-bar {
    height: var(--mobile-app-bar);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--space-2);
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }
  .app-bar-back {
    width: 44px;
    height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 0;
    cursor: pointer;
    padding: 0;
    color: var(--color-text);
    text-decoration: none;
  }
  .app-bar-back svg { width: 24px; height: 24px; }
  .app-bar-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    flex: 1;
    text-align: center;
    margin: 0 44px 0 0;
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding-bottom: calc(var(--space-4) + var(--space-6));
  }

  .page-intro {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
  }
  .page-intro :global(strong) {
    color: var(--color-text);
    font-weight: var(--font-weight-semibold);
  }

  .vendor-hint {
    background: var(--color-info-soft);
    border: 1px solid var(--color-info-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-sm);
    color: var(--color-info-text-on-soft);
    line-height: var(--line-height-default);
  }
  .hint-title {
    font-weight: var(--font-weight-semibold);
    display: block;
    margin-bottom: 4px;
  }
  .vendor-hint ol {
    margin: 0;
    padding-left: 18px;
  }
  .vendor-hint li { margin-top: 2px; }

  .input-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .input-label {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .input-help {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    margin-top: -4px;
  }
  .input-textarea {
    width: 100%;
    min-height: 100px;
    resize: vertical;
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--space-2) var(--space-3);
    box-sizing: border-box;
    background: var(--color-bg);
  }
  .input-textarea::placeholder { color: var(--color-text-dim); }
  .input-text {
    width: 100%;
    font-family: var(--font-mono);
    font-size: var(--font-size-base);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--space-3);
    box-sizing: border-box;
    background: var(--color-bg);
  }
  .input-text::placeholder { color: var(--color-text-dim); }
  .input-text.invalid { border-color: var(--color-danger); }
  .input-select {
    width: 100%;
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--space-3);
    box-sizing: border-box;
    background: var(--color-surface);
  }

  .triad {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: var(--space-2);
  }
  .triad-btn {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-text);
    cursor: pointer;
    font-family: inherit;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .triad-btn svg { width: 18px; height: 18px; color: var(--color-text-muted); }
  .triad-btn:disabled { opacity: 0.45; cursor: default; }

  .error-msg {
    font-size: var(--font-size-sm);
    color: var(--color-danger-text-on-soft);
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border, var(--color-danger));
    border-radius: var(--radius-sm);
    padding: var(--space-3) var(--space-4);
    line-height: var(--line-height-default);
  }

  .cta-primary {
    background: var(--color-primary);
    color: var(--color-on-primary);
    border: 0;
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    font-family: inherit;
  }
  .cta-primary:disabled {
    background: var(--color-border-strong);
    cursor: not-allowed;
  }

  .secondary-link {
    background: transparent;
    border: 0;
    padding: 0;
    color: var(--color-primary-strong);
    font-size: var(--font-size-sm);
    cursor: pointer;
    align-self: center;
    font-family: inherit;
    text-decoration: underline;
  }

  .danger-link {
    background: transparent;
    border: 0;
    padding: 0;
    color: var(--color-text-dim);
    font-size: var(--font-size-xs);
    cursor: pointer;
    align-self: center;
    font-family: inherit;
    margin-top: var(--space-4);
  }
  .danger-link:hover:not(:disabled) { color: var(--color-danger-text-on-soft); }
  .danger-link:disabled { opacity: 0.6; cursor: default; }
</style>
