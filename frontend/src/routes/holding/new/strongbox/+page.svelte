<!--
  Add Holding — Strongbox wizard (3 steps).
  Spec: specs/next_iteration.md — "Add Holding — Strongbox wizard"
  Mockups (all validated 2026-05-14 at 360×800):
    step 1 default:          mobile_add_holding_strongbox_input.html
    step 1 error inline:     mobile_add_holding_strongbox_input_error_inline.html
    step 1 error redirect:   mobile_add_holding_strongbox_input_error_redirect.html
    step 1 advisory:         mobile_add_holding_strongbox_input_advisory_no_metadata.html
    step 2 parseback:        mobile_add_holding_strongbox_parseback.html
    step 2 parseback no-meta: mobile_add_holding_strongbox_parseback_no_metadata.html
    step 3 success:          mobile_add_holding_strongbox_success.html

  State machine: input → parseback → success
  Back navigation:
    input     → history.back()
    parseback → input
    success   → no back; Done CTA → /home

  Key differences from Purse wizard (per mockup design notes):
    1. No Generate path.
    2. Vendor dropdown (hardware wallet vendor) not source dropdown.
    3. Two extra input affordances: Upload file (always), Scan QR (Capacitor-only).
    4. signing_metadata_present flag from validate response drives advisory state.
    5. Derivation row tinted warning on parseback when signing_metadata_present is false.
    6. declared_security: hardware_offline + self_single; purpose: reserve.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { DEV_MODE, secureStorage, clipboard, capabilities, filePicker, qrScanner } from '$lib/native-bridge';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import WizardShell from '$lib/components/WizardShell.svelte';

  // -------------------------------------------------------------------------
  // Types
  // -------------------------------------------------------------------------

  type Step = 'input' | 'parseback' | 'success';

  type ErrorState =
    | { kind: 'single_address_input' }
    | { kind: 'lsp_coordinated_wallet' }
    | { kind: 'multi_path_miniscript' }
    | { kind: 'unsupported_form' }
    | { kind: 'unparseable' }
    | { kind: 'redirect'; bestFit: string }
    | { kind: 'network'; message: string }
    | { kind: 'create'; message: string };

  interface ValidateResult {
    best_fit: string | null;
    rejection_category: string | null;
    canonical_expression: string | null;
    canonical_change_expression: string | null;
    script_type: string;
    is_multisig: boolean;
    required_signers?: number;
    total_signers?: number;
    timelock_kind?: string | null;
    first_addresses: string[];
    signing_metadata_present: boolean;
  }

  // -------------------------------------------------------------------------
  // Vendor catalogue (10 options; null slug = "Don't specify")
  // -------------------------------------------------------------------------

  interface VendorOption {
    slug: string | null;
    label: string;
    hintTitle: string | null;
    hintBody: string | null;
  }

  const VENDORS: VendorOption[] = [
    { slug: null, label: "Don't specify", hintTitle: null, hintBody: null },
    {
      slug: 'airgapped_laptop',
      label: 'Airgapped laptop',
      hintTitle: 'From an airgapped laptop — export via Sparrow or Specter.',
      hintBody: 'Open your air-gapped Sparrow or Specter wallet, go to File → Export Wallet (Sparrow) or Wallet Settings → Export (Specter) to get the output descriptor. Transfer via USB drive or QR.',
    },
    {
      slug: 'bitbox02',
      label: 'BitBox02',
      hintTitle: 'From BitBox02 — export via BitBoxApp.',
      hintBody: 'In BitBoxApp, open your wallet, go to Receive → Show account extended public key, then copy the descriptor. Or use Account → Export to get a descriptor file.',
    },
    {
      slug: 'coldcard',
      label: 'Coldcard',
      hintTitle: 'From Coldcard — export the wallet descriptor.',
      hintBody: 'On Coldcard: Advanced/Tools → Export Wallet → Generic JSON to SD card, or Export Wallet → QR if your model supports it. Use Scan QR or Upload file below.',
    },
    {
      slug: 'jade',
      label: 'Jade',
      hintTitle: 'From Jade — export via companion app.',
      hintBody: 'In the Jade companion app (Blockstream Green or Sparrow), export the wallet descriptor. In Sparrow: File → Export Wallet → Output Descriptor.',
    },
    {
      slug: 'ledger',
      label: 'Ledger',
      hintTitle: 'From Ledger — use Ledger Live or Sparrow.',
      hintBody: 'Ledger Live shows the xpub under Account → Edit account → Advanced logs. For a full descriptor with derivation path, pair with Sparrow and use File → Export Wallet → Output Descriptor.',
    },
    {
      slug: 'sparrow',
      label: 'Sparrow (as signer)',
      hintTitle: 'From Sparrow — export the output descriptor.',
      hintBody: 'File → Export Wallet → Output Descriptor. Copy the descriptor text or save the file and use Upload file below.',
    },
    {
      slug: 'specter_diy',
      label: 'Specter DIY',
      hintTitle: 'From Specter DIY — export via Specter Desktop.',
      hintBody: 'In Specter Desktop, open your wallet and go to Wallet Settings → Advanced → Export → Public Key (output descriptor). Copy or download the file.',
    },
    {
      slug: 'trezor',
      label: 'Trezor',
      hintTitle: 'From Trezor — use Trezor Suite or Sparrow.',
      hintBody: 'Trezor Suite: Account → Details → Public key (xpub). For a full descriptor with derivation path, pair with Sparrow (via USB or Trezor Bridge) and use File → Export Wallet → Output Descriptor.',
    },
    {
      slug: 'other',
      label: 'Other…',
      hintTitle: 'From your hardware wallet — export the descriptor or xpub.',
      hintBody: 'Most hardware wallets export an xpub or output descriptor — check the wallet\'s manual for "export wallet" or "show xpub". An output descriptor with derivation path ([fingerprint/path]xpub…) enables signing.',
    },
  ];

  const SCRIPT_TYPE_LABELS: Record<string, string> = {
    p2wpkh:      'Native SegWit · P2WPKH',
    'p2sh-p2wpkh': 'Wrapped SegWit · P2SH-P2WPKH',
    p2sh_p2wpkh: 'Wrapped SegWit · P2SH-P2WPKH',
    p2pkh:       'Legacy · P2PKH',
    p2tr:        'Taproot · P2TR',
  };

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  let step = $state<Step>('input');

  // Step 1
  let vendorSlug = $state<string | null>(null);
  let descriptorText = $state('');

  // Derived from validate
  let derivedExpression = $state('');
  let derivedChangeExpression = $state<string | null>(null);
  let derivedNetwork = $state<'mainnet' | 'regtest'>('regtest');
  let parseResult = $state<ValidateResult | null>(null);
  let signingMetadataPresent = $state<boolean>(true);

  // Parseback display
  let scriptTypeLabel = $state('');
  let derivationPath = $state('');
  let masterKeyTrunc = $state('');
  let holdingName = $state('');
  let nameEditing = $state(false);
  let nameDraft = $state('');

  // Shared
  let error = $state<ErrorState | null>(null);
  let loading = $state(false);
  let serverUrl = $state('');
  let autoWrapNote = $state<string | null>(null);

  // Paste-time validation state
  let pendingResult = $state<ValidateResult | null>(null);
  let lastValidatedText = $state('');
  let validateTimer: ReturnType<typeof setTimeout> | null = null;

  // -------------------------------------------------------------------------
  // Computed
  // -------------------------------------------------------------------------

  let selectedVendor = $derived(VENDORS.find(v => v.slug === vendorSlug) ?? VENDORS[0]);

  let inputCtaDisabled = $derived(
    descriptorText.trim() === '' || loading ||
    (error !== null &&
      error.kind !== 'redirect' &&
      error.kind !== 'create' &&
      error.kind !== 'network')
  );

  let canScanQR = $derived(capabilities.canScanQR());

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  function detectNetwork(input: string): 'mainnet' | 'regtest' {
    if (/tpub|tprv|upub|uprv|vpub|vprv/.test(input)) return 'regtest';
    return 'mainnet';
  }

  function extractApiError(err: Record<string, unknown>): string {
    function flatten(val: unknown): string {
      if (typeof val === 'string') return val;
      if (Array.isArray(val)) return val.map(flatten).filter(Boolean).join('; ');
      if (val && typeof val === 'object') {
        const o = val as Record<string, unknown>;
        return flatten(o.msg ?? o.message ?? o.detail ?? o.error ?? '') || JSON.stringify(o);
      }
      return String(val ?? '');
    }
    return flatten((err as Record<string, unknown>)?.message ?? (err as Record<string, unknown>)?.detail ?? (err as Record<string, unknown>)?.error ?? '').toLowerCase();
  }

  function extractDescriptorMeta(descriptor: string): { derivation: string; xpub: string } {
    const bracketed = descriptor.match(/\[([^\]]+)\]([a-zA-Z0-9]+)/);
    if (bracketed) {
      const parts = bracketed[1].split('/').slice(1);
      return {
        derivation: parts.length ? `m/${parts.join('/')}` : 'unknown',
        xpub: bracketed[2],
      };
    }
    const bare = descriptor.match(/\(([a-zA-Z0-9]{4,})\//);
    if (bare) return { derivation: 'not provided', xpub: bare[1] };
    return { derivation: 'not provided', xpub: '' };
  }

  function truncateKey(key: string): string {
    if (key.length <= 12) return key;
    return `${key.slice(0, 6)}…${key.slice(-5)}`;
  }

  function deriveAutoName(scriptType: string): string {
    if (vendorSlug && vendorSlug !== 'other') {
      const vendor = VENDORS.find(v => v.slug === vendorSlug);
      if (vendor) return `${vendor.label} Strongbox`;
    }
    const scriptLabel = SCRIPT_TYPE_LABELS[scriptType] ?? scriptType;
    const prefix = scriptLabel.includes('·') ? scriptLabel.split('·')[0].trim() : scriptLabel;
    return `${prefix} Strongbox`;
  }

  async function validateDescriptor(expression: string, network: 'mainnet' | 'regtest'): Promise<ValidateResult> {
    const res = await fetch(`${serverUrl}/api/v1/descriptors/validate`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: expression, network }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw { ...data, _status: res.status };
    }
    return res.json();
  }

  function applyDescriptorToState(raw: string, result: ValidateResult) {
    const expression = result.canonical_expression ?? raw;
    const changeExpr = result.canonical_change_expression ?? null;
    const network = detectNetwork(raw);

    parseResult = result;
    derivedExpression = expression;
    derivedChangeExpression = changeExpr;
    derivedNetwork = network;
    signingMetadataPresent = result.signing_metadata_present;
    autoWrapNote = result.canonical_expression ? 'Bare key auto-wrapped to descriptor' : null;

    const meta = extractDescriptorMeta(expression);
    derivationPath = meta.derivation;
    masterKeyTrunc = truncateKey(meta.xpub);
    scriptTypeLabel = SCRIPT_TYPE_LABELS[result.script_type] ?? result.script_type;
    holdingName = deriveAutoName(result.script_type);
    nameDraft = holdingName;
  }

  // -------------------------------------------------------------------------
  // Paste-time validation
  // -------------------------------------------------------------------------

  function setRejectionError(category: string | null): void {
    switch (category) {
      case 'single_address_input':   error = { kind: 'single_address_input' }; break;
      case 'lsp_coordinated_wallet': error = { kind: 'lsp_coordinated_wallet' }; break;
      case 'multi_path_miniscript':  error = { kind: 'multi_path_miniscript' }; break;
      case 'unsupported_form':       error = { kind: 'unsupported_form' }; break;
      default:                       error = { kind: 'unparseable' }; break;
    }
  }

  async function runPasteTimeValidation(raw: string): Promise<void> {
    const network = detectNetwork(raw);
    try {
      const result = await validateDescriptor(raw, network);
      if (result.best_fit === null) {
        setRejectionError(result.rejection_category);
        pendingResult = null;
      } else if (result.best_fit !== 'strongbox' && result.best_fit !== 'purse') {
        error = { kind: 'redirect', bestFit: result.best_fit };
        pendingResult = null;
      } else {
        error = null;
        pendingResult = result;
        lastValidatedText = raw;
        // Pre-populate signingMetadataPresent for advisory (shown before parseback).
        signingMetadataPresent = result.signing_metadata_present;
      }
    } catch (e: unknown) {
      const err = e as Record<string, unknown>;
      if (err?._status === 401) {
        const msg = extractApiError(err);
        if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
        await auth.clearCredential(); goto('/'); return;
      }
      error = { kind: 'network', message: 'Could not reach the server. Check your connection.' };
      pendingResult = null;
    }
  }

  function scheduleValidation(): void {
    error = null;
    pendingResult = null;
    parseResult = null;
    if (validateTimer) clearTimeout(validateTimer);
    const raw = descriptorText.trim();
    if (!raw) return;
    validateTimer = setTimeout(() => { void runPasteTimeValidation(raw); }, 300);
  }

  // -------------------------------------------------------------------------
  // Event handlers — Step 1
  // -------------------------------------------------------------------------

  async function handlePaste() {
    const text = await clipboard.paste();
    if (text) {
      descriptorText = text;
      error = null;
    }
  }

  async function handleScanQR() {
    const result = await qrScanner.scan();
    if (result) {
      descriptorText = result;
      error = null;
    }
  }

  async function handleUploadFile() {
    const content = await filePicker.pick('.txt,.json,.psbt');
    if (content) {
      descriptorText = content.trim();
      error = null;
    }
  }

  async function handleContinueInput() {
    const raw = descriptorText.trim();
    if (!raw) return;

    // Advisory visible and already validated — advance.
    if (parseResult !== null && !signingMetadataPresent) {
      step = 'parseback';
      return;
    }

    error = null;
    loading = true;
    try {
      if (!pendingResult || lastValidatedText !== raw) {
        await runPasteTimeValidation(raw);
      }
      if (!pendingResult || error) return;
      if (pendingResult.best_fit === 'vault') {
        error = { kind: 'redirect', bestFit: 'vault' };
        return;
      }
      applyDescriptorToState(raw, pendingResult);
      // Stay on step 1 to show advisory; second Continue advances.
      if (!pendingResult.signing_metadata_present) return;
      step = 'parseback';
    } finally {
      loading = false;
    }
  }

  // -------------------------------------------------------------------------
  // Event handlers — Step 2
  // -------------------------------------------------------------------------

  async function handleLooksRight() {
    if (loading) return;
    const finalName = nameEditing ? (nameDraft.trim() || holdingName) : holdingName;
    error = null;
    loading = true;
    try {
      const body: Record<string, unknown> = {
        name: finalName,
        purpose: 'reserve',
        declared_security: {
          custody_model: 'self_single',
          signing_model: 'hardware_offline',
          geographic_distribution: false,
          inheritance_configured: false,
        },
        descriptors: [{
          name: 'main',
          expression: derivedExpression,
          ...(derivedChangeExpression ? { change_expression: derivedChangeExpression } : {}),
          network: derivedNetwork,
          gap_limit: 20,
        }],
        signing_metadata_present: signingMetadataPresent,
      };
      if (vendorSlug !== null) {
        body.vendor = vendorSlug;
      }

      const res = await fetch(`${serverUrl}/api/v1/holdings/strongbox`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = ((data?.message ?? data?.detail ?? '') as string).toLowerCase();
        if (res.status === 401) {
          if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
          await auth.clearCredential(); goto('/'); return;
        }
        const rawMsg: string = (data?.message ?? data?.detail ?? '') as string;
        const friendlyMsg = rawMsg.toLowerCase().includes('already exists')
          ? 'A Strongbox with this descriptor already exists.'
          : rawMsg || 'Could not create the Strongbox. Try again.';
        error = { kind: 'create', message: friendlyMsg };
        return;
      }
      if (nameEditing) { holdingName = finalName; nameEditing = false; }

      const descriptorIds: string[] = data?.descriptor_ids ?? [];
      await Promise.all(
        descriptorIds.map((id: string) =>
          fetch(`${serverUrl}/api/v1/descriptors/${id}/rescan`, {
            method: 'POST',
            headers: authHeaders(),
          }).catch(() => {})
        )
      );
      step = 'success';
    } catch {
      error = { kind: 'create', message: 'Network error. Check your connection and try again.' };
    } finally {
      loading = false;
    }
  }

  async function handleCopyAddress(addr: string) {
    try { await navigator.clipboard.writeText(addr); } catch { /* silent */ }
  }

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';
  });
</script>

<!-- =========================================================================
     STEP 1 — INPUT
     ========================================================================= -->
{#if step === 'input'}
<WizardShell
  stepNumber={1}
  showBack={true}
  onBack={() => history.back()}
  ctaLabel="Continue"
  ctaDisabled={inputCtaDisabled}
  {loading}
  onCta={handleContinueInput}
>
  {#snippet children()}
  <div class="scroll-pad">

    <div class="step-head">
      <h1 class="step-heading">Add a Strongbox</h1>
    </div>

    <!-- Vendor dropdown -->
    <div class="source-block">
      <label class="field-label" for="vendor-pick">
        Hardware wallet <span class="optional">optional</span>
      </label>
      <div class="select-wrap">
        <select
          id="vendor-pick"
          value={vendorSlug ?? ''}
          onchange={(e) => {
            vendorSlug = (e.target as HTMLSelectElement).value || null;
          }}
        >
          {#each VENDORS as v (v.slug)}
            <option value={v.slug ?? ''}>{v.label}</option>
          {/each}
        </select>
        <span class="select-chevron" aria-hidden="true"></span>
      </div>

      {#if selectedVendor.hintTitle}
        <div class="wallet-hint" role="note">
          <svg class="hint-icon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8"  x2="12" y2="13"/>
            <line x1="12" y1="16" x2="12" y2="16.5"/>
          </svg>
          <div>
            <p class="hint-title">{selectedVendor.hintTitle}</p>
            <p class="hint-body">{selectedVendor.hintBody}</p>
          </div>
        </div>
      {/if}
    </div>

    <!-- Descriptor textarea -->
    <div class="descriptor-block">
      <label class="field-label" for="descriptor-input">Descriptor</label>
      <div class="descriptor-input-wrap">
        <textarea
          id="descriptor-input"
          class="descriptor-textarea"
          class:descriptor-error={error !== null && error.kind !== 'redirect' && error.kind !== 'create' && error.kind !== 'network'}
          placeholder="wpkh([abc12345/84h/0h/0h]xpub6CUGRUo…"
          aria-label="Descriptor"
          aria-invalid={error !== null && error.kind !== 'redirect' && error.kind !== 'create' && error.kind !== 'network' ? true : undefined}
          bind:value={descriptorText}
          oninput={scheduleValidation}
        ></textarea>
        <button class="paste-btn" type="button" aria-label="Paste from clipboard" onclick={handlePaste}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="9" y="3"  width="6"  height="4"  rx="1"/>
            <rect x="5" y="5"  width="14" height="16" rx="2"/>
          </svg>
          Paste
        </button>
      </div>

      <!-- Alt-input affordances -->
      <div class="alt-inputs" class:alt-inputs--single={!canScanQR}>
        {#if canScanQR}
          <button class="alt-btn" type="button" aria-label="Scan a QR code with the camera" onclick={handleScanQR}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="3"  y="3"  width="7" height="7" rx="1"/>
              <rect x="14" y="3"  width="7" height="7" rx="1"/>
              <rect x="3"  y="14" width="7" height="7" rx="1"/>
              <line x1="14" y1="14" x2="14" y2="17"/>
              <line x1="14" y1="20" x2="17" y2="20"/>
              <line x1="17" y1="14" x2="17" y2="17"/>
              <line x1="20" y1="17" x2="20" y2="20"/>
            </svg>
            Scan QR
          </button>
        {/if}
        <button class="alt-btn" type="button" aria-label="Upload a descriptor file" onclick={handleUploadFile}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M 14 3 H 7 a 2 2 0 0 0 -2 2 v 14 a 2 2 0 0 0 2 2 h 10 a 2 2 0 0 0 2 -2 V 8 Z"/>
            <polyline points="14 3 14 8 19 8"/>
            <line x1="12" y1="12" x2="12" y2="17"/>
            <polyline points="10 14 12 12 14 14"/>
          </svg>
          Upload file
        </button>
      </div>

    </div>

  </div>
  {/snippet}

  {#snippet errorRegion()}
    {#if error?.kind === 'single_address_input'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8"  x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">That looks like an address.</p>
          <p class="fe-body">To watch a wallet, TallyKeep needs the wallet's descriptor or extended public key, not a single receive address. Look for "Export descriptor", "Show extended public key", or "Account public key" in your wallet's settings.</p>
        </div>
      </div>
    {:else if error?.kind === 'lsp_coordinated_wallet'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8"  x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">This looks like a Lightning-coordinated wallet.</p>
          <p class="fe-body">Wallets like Phoenix hold their on-chain balance jointly with a Lightning service provider, using a script TallyKeep can't watch independently yet. We don't support these wallets today.</p>
        </div>
      </div>
    {:else if error?.kind === 'multi_path_miniscript'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8"  x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">This descriptor has multiple spending paths.</p>
          <p class="fe-body">TallyKeep currently supports single-path descriptors (one spending route per wallet). Descriptors with branching script logic such as recovery paths, conditional spends, or hash preimage gates aren't supported yet.</p>
        </div>
      </div>
    {:else if error?.kind === 'unsupported_form' || error?.kind === 'unparseable'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8"  x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">{error.kind === 'unparseable' ? "TallyKeep can't read this." : "Unsupported descriptor."}</p>
          <p class="fe-body">
            {#if error.kind === 'unparseable'}
              This doesn't parse as a Bitcoin descriptor or an extended public key. Check for missing characters, copy errors, or paste truncation.
            {:else}
              Supported forms are listed in each wizard's input help text. If you're sure this descriptor describes a single-key wallet, a multisig, or a timelocked vault, double-check the export format from your wallet.
            {/if}
          </p>
        </div>
      </div>
    {:else if error?.kind === 'redirect'}
      <div class="footer-error footer-error--warning" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M 12 2 L 2 22 L 22 22 Z"/>
          <line x1="12" y1="9"  x2="12" y2="14"/>
          <line x1="12" y1="17" x2="12" y2="17.5"/>
        </svg>
        <div class="fe-content">
          <p class="fe-title">This looks like a Vault descriptor.</p>
          <p class="fe-body">Multisig or timelocked Holdings are Vaults in TallyKeep. Set this up as a Vault instead.</p>
          <button class="fe-redirect-cta" type="button" onclick={() => goto('/holding/new/vault')}>
            Set up as Vault
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <polyline points="9 6 15 12 9 18"/>
            </svg>
          </button>
        </div>
      </div>
    {:else if error?.kind === 'network'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8"  x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">Couldn't reach the server.</p>
          <p class="fe-body">{error.message}</p>
        </div>
      </div>
    {:else if parseResult !== null && !signingMetadataPresent}
      <!-- Advisory: signing metadata absent. CTA stays enabled; second Continue advances. -->
      <div class="footer-advisory" role="note">
        <svg class="adv-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M 12 2 L 2 22 L 22 22 Z"/>
          <line x1="12" y1="9"  x2="12" y2="14"/>
          <line x1="12" y1="17" x2="12" y2="17.5"/>
        </svg>
        <p class="adv-body"><strong>Missing derivation metadata.</strong> Your hardware wallet may refuse to sign transactions with this descriptor. Receiving funds will work as expected. Re-export your descriptor to enable signing, or continue as is.</p>
      </div>
    {/if}
  {/snippet}
</WizardShell>

<!-- =========================================================================
     STEP 2 — PARSEBACK
     ========================================================================= -->
{:else if step === 'parseback'}
<WizardShell
  stepNumber={2}
  showBack={true}
  onBack={() => { error = null; step = 'input'; }}
  ctaLabel="Looks right"
  ctaDisabled={false}
  {loading}
  onCta={handleLooksRight}
>
  {#snippet children()}
  <div class="scroll-pad">

    <div class="step-head">
      <h1 class="step-heading">Here's what we read</h1>
      <p class="step-sub">Check the first addresses match what your hardware wallet (or its companion app) shows. If they don't, go back and re-check the descriptor.</p>
    </div>

    <!-- Auto-name preview (iron stripe = Strongbox color) -->
    <div class="name-preview">
      {#if nameEditing}
        <input
          class="name-input"
          type="text"
          aria-label="Holding name"
          bind:value={nameDraft}
          onkeydown={(e) => { if (e.key === 'Enter') { holdingName = nameDraft.trim() || holdingName; nameEditing = false; } if (e.key === 'Escape') { nameDraft = holdingName; nameEditing = false; } }}
        />
        <button class="rename-btn" type="button" onclick={() => { holdingName = nameDraft.trim() || holdingName; nameEditing = false; }}>
          Done
        </button>
      {:else}
        <div>
          <span class="name-label">Will be named</span>
          <span class="name-value">{holdingName}</span>
        </div>
        <button class="rename-btn" type="button" aria-label="Rename this Strongbox" onclick={() => { nameDraft = holdingName; nameEditing = true; }}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M 4 20 L 4 16 L 16 4 L 20 8 L 8 20 Z"/>
            <line x1="13" y1="7" x2="17" y2="11"/>
          </svg>
          Rename
        </button>
      {/if}
    </div>

    <!-- Parse-back card -->
    <div class="parse-card" aria-label="Parsed descriptor metadata">
      <div class="parse-row">
        <span class="parse-key">Script type</span>
        <span class="parse-val">{scriptTypeLabel || parseResult?.script_type}</span>
      </div>
      <div class="parse-row" class:parse-row--advisory={!signingMetadataPresent}>
        <span class="parse-key">Derivation</span>
        {#if !signingMetadataPresent}
          <span class="parse-val parse-val--advisory">
            <span class="val-with-icon">
              <span>not provided</span>
              <svg class="info-icon" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8"  x2="12" y2="13"/>
                <line x1="12" y1="16" x2="12" y2="16.5"/>
              </svg>
            </span>
          </span>
        {:else}
          <span class="parse-val parse-val--mono">{derivationPath}</span>
        {/if}
      </div>
      <div class="parse-row">
        <span class="parse-key">Master key</span>
        <span class="parse-val parse-val--mono">{masterKeyTrunc}</span>
      </div>
    </div>

    <!-- First addresses -->
    {#if parseResult?.first_addresses?.length}
      <div class="addresses-card" aria-label="First derived addresses">
        <p class="addr-card-title">First addresses</p>
        <p class="addr-card-sub">Verify these match your hardware wallet's receive addresses.</p>
        {#each parseResult.first_addresses as addr, i (addr)}
          <div class="addr-row">
            <span class="addr-idx">{i}</span>
            <span class="addr-text">{addr}</span>
            <button class="copy-btn" type="button" aria-label="Copy address" onclick={() => handleCopyAddress(addr)}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="9" y="9" width="13" height="13" rx="2"/>
                <path d="M 5 15 H 4 a 2 2 0 0 1 -2 -2 V 4 a 2 2 0 0 1 2 -2 h 9 a 2 2 0 0 1 2 2 v 1"/>
              </svg>
            </button>
          </div>
        {/each}
      </div>
    {/if}

    {#if error?.kind === 'create'}
      <p class="create-error">{error.message}</p>
    {/if}

  </div>
  {/snippet}
</WizardShell>

<!-- =========================================================================
     STEP 3 — SUCCESS
     ========================================================================= -->
{:else if step === 'success'}
<WizardShell
  stepNumber={3}
  showBack={false}
  ctaLabel="Done"
  ctaDisabled={false}
  loading={false}
  onCta={() => goto('/home')}
>
  {#snippet children()}
  <div class="success-body">
    <div class="success-check" aria-hidden="true">✓</div>
    <h1 class="success-heading">Strongbox added</h1>
    <p class="success-sub">We're scanning the chain to load this Strongbox's balance and history. It usually takes a few seconds.</p>
    <div class="scan-row" role="status">
      <span class="scan-spinner" aria-hidden="true"></span>
      <span class="scan-label">Scanning…</span>
      <span class="scan-hint">balance will appear on Home shortly</span>
    </div>
  </div>
  {/snippet}
</WizardShell>
{/if}

<style>
  /* ---- shared scroll pad ---- */
  .scroll-pad {
    padding: var(--space-4) var(--space-4) var(--space-5);
  }

  /* ---- step 1 heading ---- */
  .step-heading {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
    margin: 0;
    letter-spacing: -0.01em;
  }
  .step-head { margin-bottom: var(--space-4); }

  /* ---- vendor picker ---- */
  .source-block { margin-bottom: var(--space-4); }
  .field-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    display: block;
    margin: var(--space-2) 0;
  }
  .field-label .optional {
    text-transform: none;
    color: var(--color-text-dim);
    font-weight: var(--font-weight-normal);
    letter-spacing: 0;
    margin-left: var(--space-2);
  }
  .select-wrap { position: relative; }
  .select-wrap select {
    width: 100%;
    padding: var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-base);
    color: var(--color-text);
    appearance: none;
    cursor: pointer;
  }
  .select-wrap select:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 2px var(--color-primary-soft);
  }
  .select-chevron {
    position: absolute;
    top: 50%; right: var(--space-3);
    width: 8px; height: 8px;
    border-right: 2px solid var(--color-text-muted);
    border-bottom: 2px solid var(--color-text-muted);
    transform: translateY(-75%) rotate(45deg);
    pointer-events: none;
  }

  /* ---- vendor hint banner ---- */
  .wallet-hint {
    margin-top: var(--space-3);
    padding: var(--space-3);
    background: var(--color-info-soft);
    border: 1px solid var(--color-info-border);
    border-radius: var(--radius-md);
    color: var(--color-info-text-on-soft);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .hint-icon {
    width: 18px; height: 18px; flex-shrink: 0;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    margin-top: 1px;
  }
  .hint-title {
    font-weight: var(--font-weight-semibold);
    margin: 0 0 2px;
  }
  .hint-body { margin: 0; }

  /* ---- descriptor input ---- */
  .descriptor-block { margin-top: var(--space-3); }
  .descriptor-input-wrap { position: relative; }
  .descriptor-textarea {
    width: 100%;
    min-height: 120px;
    padding: var(--space-3);
    padding-right: 72px;
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    color: var(--color-text);
    line-height: 1.5;
    resize: vertical;
    box-sizing: border-box;
  }
  .descriptor-textarea::placeholder { color: var(--color-text-dim); }
  .descriptor-textarea:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 2px var(--color-primary-soft);
  }
  .descriptor-textarea.descriptor-error {
    border-color: var(--color-danger-border, #f87171);
  }
  .paste-btn {
    position: absolute;
    top: var(--space-2); right: var(--space-2);
    padding: var(--space-1) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-pill);
    font-family: inherit;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .paste-btn:hover { background: var(--color-bg); }
  .paste-btn svg { width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; }


  /* ---- alt-input buttons ---- */
  .alt-inputs {
    margin-top: var(--space-3);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-2);
  }
  .alt-inputs--single {
    grid-template-columns: 1fr;
  }
  .alt-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    cursor: pointer;
  }
  .alt-btn:hover { background: var(--color-bg); }
  .alt-btn svg {
    width: 16px; height: 16px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }

  /* ---- footer error/advisory regions ---- */
  .footer-error {
    margin-bottom: var(--space-3);
    padding: var(--space-3);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .footer-error--danger {
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    color: var(--color-danger-text-on-soft);
  }
  .footer-error--warning {
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    color: var(--color-warning-text-on-soft);
  }
  .fe-icon {
    width: 18px; height: 18px; flex-shrink: 0;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    margin-top: 1px;
  }
  .fe-content { flex: 1; }
  .fe-title { font-weight: var(--font-weight-semibold); margin: 0 0 2px; }
  .fe-body  { margin: 0 0 var(--space-3); }
  .fe-redirect-cta {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: var(--space-2) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-warning-text-on-soft);
    cursor: pointer;
  }
  .fe-redirect-cta svg {
    width: 14px; height: 14px; stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }

  .footer-advisory {
    margin-bottom: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    color: var(--color-warning-text-on-soft);
    font-size: var(--font-size-xs);
    line-height: 1.4;
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .adv-icon {
    width: 14px; height: 14px; flex-shrink: 0;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    margin-top: 1px;
  }
  .adv-body { margin: 0; }

  /* ---- parseback step ---- */
  .step-sub {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: var(--space-2) 0 0;
  }

  /* name preview — Strongbox iron stripe */
  .name-preview {
    margin-bottom: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-strongbox);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
  }
  .name-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    display: block;
    margin-bottom: 2px;
  }
  .name-value {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .name-input {
    flex: 1;
    padding: var(--space-2) var(--space-3);
    background: var(--color-bg);
    border: 1px solid var(--color-border-focus);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .name-input:focus { outline: none; box-shadow: 0 0 0 2px var(--color-primary-soft); }
  .rename-btn {
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-family: inherit;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }
  .rename-btn:hover { background: var(--color-bg); }
  .rename-btn svg { width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; }

  /* parse card */
  .parse-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    margin-bottom: var(--space-3);
    overflow: hidden;
  }
  .parse-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--space-3);
    padding: var(--space-2) 0;
  }
  .parse-row + .parse-row { border-top: 1px solid var(--color-border); }
  .parse-key {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
  }
  .parse-val {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
    text-align: right;
  }
  .parse-val--mono {
    font-family: var(--font-mono);
    font-weight: var(--font-weight-normal);
  }
  /* Advisory tint on Derivation row when signing metadata is missing */
  .parse-row--advisory {
    background: var(--color-warning-soft);
    margin-left: calc(-1 * var(--space-4));
    margin-right: calc(-1 * var(--space-4));
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }
  .parse-row--advisory + .parse-row { border-top-color: var(--color-warning-border); }
  .parse-val--advisory { color: var(--color-warning-text-on-soft); }
  .val-with-icon {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .info-icon {
    width: 14px; height: 14px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    flex-shrink: 0;
  }

  /* addresses card */
  .addresses-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4) var(--space-4);
    margin-bottom: var(--space-2);
  }
  .addr-card-title {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    margin: var(--space-2) 0;
  }
  .addr-card-sub {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    line-height: var(--line-height-default);
    margin: 0 0 var(--space-3);
  }
  .addr-row {
    display: grid;
    grid-template-columns: 18px 1fr 28px;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) 0;
  }
  .addr-row + .addr-row { border-top: 1px solid var(--color-border); }
  .addr-idx {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .addr-text {
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    color: var(--color-text);
    word-break: break-all;
    line-height: 1.35;
  }
  .copy-btn {
    width: 28px; height: 28px;
    display: inline-flex; align-items: center; justify-content: center;
    background: transparent;
    border: 0;
    border-radius: var(--radius-sm);
    color: var(--color-text-dim);
    cursor: pointer;
  }
  .copy-btn:hover { background: var(--color-bg); color: var(--color-text); }
  .copy-btn svg { width: 14px; height: 14px; stroke: currentColor; fill: none; stroke-width: 2; }

  .create-error {
    font-size: var(--font-size-sm);
    color: var(--color-danger-text-on-soft, #dc2626);
    margin: var(--space-3) 0 0;
    text-align: center;
  }

  /* ---- success step ---- */
  .success-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-7) var(--space-5);
    gap: var(--space-4);
    text-align: center;
  }
  .success-check {
    width: 64px; height: 64px;
    display: flex; align-items: center; justify-content: center;
    background: var(--color-holding-strongbox, #4a4d4f);
    color: #fff;
    border-radius: 50%;
    font-size: 28px;
    font-weight: var(--font-weight-semibold);
  }
  .success-heading {
    font-size: var(--font-size-xl, 1.25rem);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0;
    line-height: var(--line-height-tight);
  }
  .success-sub {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 280px;
    margin: 0;
  }
  .scan-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-strongbox, #4a4d4f);
    border-radius: var(--radius-md);
    width: 100%;
    max-width: 300px;
    box-sizing: border-box;
  }
  .scan-spinner {
    width: 16px; height: 16px; flex-shrink: 0;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-text-muted);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .scan-label {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
  }
  .scan-hint {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    flex: 1;
    text-align: right;
  }
</style>
