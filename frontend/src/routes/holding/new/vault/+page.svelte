<!--
  Add Holding — Vault wizard (3 steps).
  Spec: specs/next_iteration.md — "Add Vault wizard (all v1 shapes)"
  Mockups (all validated 2026-05-15 at 360×800):
    step 1 default:            mobile_add_holding_vault_input.html
    step 1 error inline:       mobile_add_holding_vault_input_error_inline.html
    step 1 error redirect:     mobile_add_holding_vault_input_error_redirect.html
    step 2 parseback (unified): mobile_add_holding_vault_parseback.html
    step 3 success:            mobile_add_holding_vault_success.html

  State machine: input → parseback → success
  Back navigation:
    input     → history.back()
    parseback → input
    success   → no back; Done CTA → /home

  Key differences from Strongbox wizard:
    1. No vendor dropdown.
    2. best_fit from validate drives routing:
       vault → step 2; purse/strongbox → redirect error; null → rejection error.
    3. Four parseback rows instead of three:
       Signers required, Signing keys, Script type, Timelock.
    4. Auto-name comes from backend (validate response.auto_name).
    5. declared_security derived from is_multisig.
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
    | { kind: 'redirect'; bestFit: 'purse' | 'strongbox' }
    | { kind: 'network'; message: string }
    | { kind: 'create'; message: string };

  interface ValidateResult {
    script_type: string;
    is_multisig: boolean;
    required_signers: number | null;
    total_signers: number | null;
    timelock_kind: string | null;
    timelock_value: number | null;
    cosigner_fingerprints: string[];
    auto_name: string | null;
    best_fit: string | null;
    rejection_category: string | null;
    canonical_expression: string | null;
    canonical_change_expression: string | null;
    first_addresses: string[];
    signing_metadata_present: boolean;
  }

  // -------------------------------------------------------------------------
  // Label maps
  // -------------------------------------------------------------------------

  const SCRIPT_TYPE_LABELS: Record<string, string> = {
    'p2wsh':              'Native SegWit · P2WSH',
    'p2wsh miniscript':   'Native SegWit · P2WSH miniscript',
    'p2tr':               'Taproot · P2TR',
    'p2sh-multisig':      'Legacy · P2SH',
    'p2sh-p2wsh':         'Legacy · P2SH-P2WSH',
    'p2sh miniscript':    'Legacy · P2SH miniscript',
  };

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  let step = $state<Step>('input');

  // Step 1
  let descriptorText = $state('');

  // Derived from validate
  let derivedExpression = $state('');
  let derivedNetwork = $state<'mainnet' | 'regtest'>('regtest');
  let parseResult = $state<ValidateResult | null>(null);
  let pendingResult = $state<ValidateResult | null>(null);
  let lastValidatedText = $state('');
  let validateTimer: ReturnType<typeof setTimeout> | null = null;

  // Parseback display values
  let holdingName = $state('');
  let nameEditing = $state(false);
  let nameDraft = $state('');

  // Shared
  let error = $state<ErrorState | null>(null);
  let loading = $state(false);
  let serverUrl = $state('');

  // -------------------------------------------------------------------------
  // Computed
  // -------------------------------------------------------------------------

  let inputCtaDisabled = $derived(
    descriptorText.trim() === '' ||
    (error !== null && error.kind !== 'network' && error.kind !== 'create')
  );

  let canScanQR = $derived(capabilities.canScanQR());

  // -------------------------------------------------------------------------
  // Formatters
  // -------------------------------------------------------------------------

  const _GENESIS_TS = 1230940905; // 2009-01-03T18:15:05Z

  function cltvDate(blockHeight: number): string {
    const ts = (_GENESIS_TS + blockHeight * 600) * 1000;
    return new Date(ts).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }

  function csvDuration(blockCount: number): string {
    if (blockCount >= 52560) return `${Math.floor(blockCount / 52560)} year${Math.floor(blockCount / 52560) > 1 ? 's' : ''}`;
    if (blockCount >= 4320)  return `${Math.floor(blockCount / 4320)} month${Math.floor(blockCount / 4320) > 1 ? 's' : ''}`;
    const days = Math.max(1, Math.floor(blockCount / 144));
    return `${days} day${days > 1 ? 's' : ''}`;
  }

  function formatN(n: number): string {
    return n.toLocaleString('en-US');
  }

  function timelockPrimary(kind: string | null, value: number | null): string {
    if (!kind || value === null) return 'None';
    if (kind === 'cltv') return `CLTV — unlocks on block ${formatN(value)}`;
    if (kind === 'csv')  return `CSV — each deposit locks for ${formatN(value)} blocks`;
    return 'None';
  }

  function timelockSub(kind: string | null, value: number | null): string | null {
    if (!kind || value === null) return null;
    if (kind === 'cltv') return `~ ${cltvDate(value)}`;
    if (kind === 'csv')  return `~ ${csvDuration(value)}`;
    return null;
  }

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

  // -------------------------------------------------------------------------
  // Event handlers — Step 1
  // -------------------------------------------------------------------------

  async function handlePaste() {
    const text = await clipboard.paste();
    if (text) { descriptorText = text; error = null; }
  }

  async function handleScanQR() {
    const result = await qrScanner.scan();
    if (result) { descriptorText = result; error = null; }
  }

  async function handleUploadFile() {
    const content = await filePicker.pick('.txt,.json');
    if (content) { descriptorText = content.trim(); error = null; }
  }

  function setRejectionError(category: string) {
    switch (category) {
      case 'single_address_input':   error = { kind: 'single_address_input' }; break;
      case 'lsp_coordinated_wallet': error = { kind: 'lsp_coordinated_wallet' }; break;
      case 'multi_path_miniscript':  error = { kind: 'multi_path_miniscript' }; break;
      case 'unsupported_form':       error = { kind: 'unsupported_form' }; break;
      default:                       error = { kind: 'unparseable' }; break;
    }
  }

  async function runPasteTimeValidation(raw: string) {
    if (!raw) return;
    const network = detectNetwork(raw);
    try {
      const result = await validateDescriptor(raw, network);
      pendingResult = result;
      lastValidatedText = raw;
      if (result.best_fit === null) {
        setRejectionError(result.rejection_category ?? 'unsupported_form');
      } else if (result.best_fit !== 'vault') {
        error = { kind: 'redirect', bestFit: result.best_fit as 'purse' | 'strongbox' };
      } else {
        error = null;
      }
    } catch (e: unknown) {
      const err = e as Record<string, unknown>;
      if (err?._status === 401) return;
      pendingResult = null;
    }
  }

  function scheduleValidation() {
    if (error?.kind === 'network' || error?.kind === 'create') error = null;
    parseResult = null;
    pendingResult = null;
    if (validateTimer !== null) clearTimeout(validateTimer);
    const text = descriptorText.trim();
    if (!text) return;
    validateTimer = setTimeout(() => runPasteTimeValidation(text), 300);
  }

  async function handleContinueInput() {
    const raw = descriptorText.trim();
    if (!raw) return;

    error = null;
    loading = true;
    try {
      if (!pendingResult || lastValidatedText !== raw) {
        await runPasteTimeValidation(raw);
      }
      if (!pendingResult || error) return;
      const result = pendingResult;
      if (result.best_fit === null) {
        setRejectionError(result.rejection_category ?? 'unsupported_form');
        return;
      }
      if (result.best_fit !== 'vault') {
        error = { kind: 'redirect', bestFit: result.best_fit as 'purse' | 'strongbox' };
        return;
      }

      const network = detectNetwork(raw);
      parseResult = result;
      derivedExpression = result.canonical_expression ?? raw;
      derivedNetwork = network;
      holdingName = result.auto_name ?? 'Vault';
      nameDraft = holdingName;
      step = 'parseback';
    } catch (e: unknown) {
      const err = e as Record<string, unknown>;
      if (err?._status === 401) {
        const msg = extractApiError(err);
        if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
        await auth.clearCredential(); goto('/'); return;
      }
      const status = err?._status as number | undefined;
      if (!status || status >= 500) {
        error = { kind: 'network', message: 'Could not reach the server. Check your connection.' };
      } else {
        error = { kind: 'unsupported_form' };
      }
    } finally {
      loading = false;
    }
  }

  // -------------------------------------------------------------------------
  // Event handlers — Step 2
  // -------------------------------------------------------------------------

  async function handleLooksRight() {
    if (loading || !parseResult) return;
    const finalName = nameEditing ? (nameDraft.trim() || holdingName) : holdingName;
    error = null;
    loading = true;
    try {
      const isMultisig = parseResult.is_multisig;
      const body: Record<string, unknown> = {
        name: finalName,
        purpose: 'long_term',
        declared_security: {
          custody_model: isMultisig ? 'self_multisig' : 'self_single',
          signing_model: 'ceremonial',
          geographic_distribution: false,
          inheritance_configured: false,
        },
        descriptors: [{
          name: 'main',
          expression: derivedExpression,
          network: derivedNetwork,
          gap_limit: 20,
        }],
      };

      const res = await fetch(`${serverUrl}/api/v1/holdings/vault`, {
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
          ? 'A Vault with this descriptor already exists.'
          : rawMsg || 'Could not create the Vault. Try again.';
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
      <h1 class="step-heading">Add a Vault</h1>
      <p class="step-sub">A Vault is a wallet whose spending is locked behind a script-enforced timelock, multiple keys, or both. Paste the descriptor of your locked wallet below.</p>
    </div>

    <!-- Descriptor textarea -->
    <div class="descriptor-block">
      <label class="field-label" for="descriptor-input">Vault descriptor</label>
      <div class="descriptor-input-wrap">
        <textarea
          id="descriptor-input"
          class="descriptor-textarea"
          class:descriptor-warning={error?.kind === 'redirect'}
          class:descriptor-error={error !== null && error.kind !== 'redirect' && error.kind !== 'network' && error.kind !== 'create'}
          placeholder="wsh(and_v(v:after(900000),pk([abc12345/86h/0h/0h]xpub6D…/0/*)))"
          aria-label="Descriptor"
          aria-invalid={error !== null && error.kind !== 'network' && error.kind !== 'create' ? true : undefined}
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
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">That looks like an address.</p>
          <p class="fe-body">
            To watch a wallet, TallyKeep needs the wallet's descriptor
            or extended public key, not a single receive address. Look
            for "Export descriptor", "Show extended public key", or
            "Account public key" in your wallet's settings.
          </p>
        </div>
      </div>
    {:else if error?.kind === 'lsp_coordinated_wallet'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">This looks like a Lightning-coordinated wallet.</p>
          <p class="fe-body">
            Wallets like Phoenix hold their on-chain balance jointly with
            a Lightning service provider, using a script TallyKeep can't
            watch independently yet. We don't support these wallets today.
          </p>
        </div>
      </div>
    {:else if error?.kind === 'multi_path_miniscript'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">This descriptor has multiple spending paths.</p>
          <p class="fe-body">
            TallyKeep currently supports single-path descriptors (one
            spending route per wallet). Descriptors with branching
            script logic such as recovery paths, conditional spends,
            or hash preimage gates aren't supported yet.
          </p>
        </div>
      </div>
    {:else if error?.kind === 'unsupported_form' || error?.kind === 'unparseable'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">
            {error.kind === 'unparseable' ? "TallyKeep can't read this." : "Unsupported descriptor."}
          </p>
          <p class="fe-body">
            {#if error.kind === 'unparseable'}
              This doesn't parse as a Bitcoin descriptor or an extended
              public key. Check for missing characters, copy errors, or
              paste truncation.
            {:else}
              Supported forms are listed in each wizard's input help
              text. If you're sure this descriptor describes a
              single-key wallet, a multisig, or a timelocked vault,
              double-check the export format from your wallet.
            {/if}
          </p>
        </div>
      </div>
    {:else if error?.kind === 'redirect'}
      {@const redirectTarget = error.bestFit}
      <div class="footer-error footer-error--warning" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M 12 2 L 2 22 L 22 22 Z"/>
          <line x1="12" y1="9" x2="12" y2="14"/>
          <line x1="12" y1="17" x2="12" y2="17.5"/>
        </svg>
        <div class="fe-content">
          <p class="fe-title">No timelock or multi-signature detected.</p>
          <p class="fe-body">
            Set this up as a {redirectTarget === 'purse' ? 'Purse' : 'Strongbox'} instead.
            If you meant to add a timelock, export the descriptor again with the lock fragment.
          </p>
          <button class="fe-redirect-cta" type="button"
                  onclick={() => goto(`/holding/new/${redirectTarget}`)}>
            Set up as {redirectTarget === 'purse' ? 'Purse' : 'Strongbox'}
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 6 15 12 9 18"/>
            </svg>
          </button>
        </div>
      </div>
    {:else if error?.kind === 'network'}
      <div class="footer-error footer-error--danger" role="alert">
        <svg class="fe-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8"  x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="fe-title">Connection error</p>
          <p class="fe-body">{error.message}</p>
        </div>
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
      <p class="step-sub">Check the parameters match what you set when you built the descriptor.</p>
    </div>

    <!-- Auto-name preview (Vault stripe) -->
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
        <button class="rename-btn" type="button" aria-label="Rename this Vault" onclick={() => { nameDraft = holdingName; nameEditing = true; }}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M 4 20 L 4 16 L 16 4 L 20 8 L 8 20 Z"/>
            <line x1="13" y1="7" x2="17" y2="11"/>
          </svg>
          Rename
        </button>
      {/if}
    </div>

    <!-- Parse-back card — 4 rows -->
    {#if parseResult}
    <div class="parse-card" aria-label="Parsed descriptor metadata">
      <!-- Signers required -->
      <div class="parse-row">
        <span class="parse-key">Signers required</span>
        <span class="parse-val">
          {parseResult.required_signers ?? 1} of {parseResult.total_signers ?? 1}
        </span>
      </div>

      <!-- Signing keys -->
      <div class="parse-row">
        <span class="parse-key">Signing keys</span>
        <span class="parse-val parse-val--mono">
          {#if parseResult.cosigner_fingerprints.length > 0}
            {parseResult.cosigner_fingerprints.join(' · ')}
          {:else}
            not provided
          {/if}
        </span>
      </div>

      <!-- Script type -->
      <div class="parse-row">
        <span class="parse-key">Script type</span>
        <span class="parse-val">
          {SCRIPT_TYPE_LABELS[parseResult.script_type] ?? parseResult.script_type}
        </span>
      </div>

      <!-- Timelock -->
      <div class="parse-row">
        <span class="parse-key">Timelock</span>
        <span class="parse-val">
          <span class="timelock-primary">
            {timelockPrimary(parseResult.timelock_kind, parseResult.timelock_value)}
          </span>
          {#if timelockSub(parseResult.timelock_kind, parseResult.timelock_value)}
            <span class="timelock-sub">
              {timelockSub(parseResult.timelock_kind, parseResult.timelock_value)}
            </span>
          {/if}
        </span>
      </div>
    </div>
    {/if}

    <!-- First addresses -->
    {#if parseResult?.first_addresses?.length}
      <div class="addresses-card" aria-label="First derived addresses">
        <p class="addr-card-title">First three addresses</p>
        <p class="addr-card-sub">Open the wallet you exported this descriptor from and confirm these match its first three receive addresses.</p>
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
    <h1 class="success-heading">Vault added</h1>
    <p class="success-sub">We're scanning the chain to load this Vault's balance and history. It usually takes a few seconds.</p>
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

  /* ---- step headings (shared) ---- */
  .step-heading {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
    margin: 0;
    letter-spacing: -0.01em;
  }
  .step-sub {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: var(--space-2) 0 0;
  }
  .step-head { margin-bottom: var(--space-4); }

  /* ---- descriptor input ---- */
  .descriptor-block { margin-top: var(--space-3); }
  .field-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    display: block;
    margin: var(--space-2) 0;
  }
  .descriptor-input-wrap { position: relative; }
  .descriptor-textarea {
    width: 100%;
    min-height: 140px;
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
  .descriptor-textarea.descriptor-warning {
    border-color: var(--color-warning-border);
  }
  .descriptor-textarea.descriptor-warning:focus {
    border-color: var(--color-warning);
    box-shadow: 0 0 0 2px var(--color-warning-soft);
  }
  .descriptor-textarea.descriptor-error {
    border-color: var(--color-danger-border);
  }
  .descriptor-textarea.descriptor-error:focus {
    border-color: var(--color-danger);
    box-shadow: 0 0 0 2px var(--color-danger-soft);
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
  .alt-inputs--single { grid-template-columns: 1fr; }
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

  /* ---- footer error regions ---- */
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
  .footer-error code {
    font-family: var(--font-mono);
    font-size: 0.95em;
    background: rgba(0,0,0,0.05);
    padding: 1px 4px;
    border-radius: var(--radius-sm);
  }
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

  /* name preview — Vault colour stripe */
  .name-preview {
    margin-bottom: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-vault);
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
    align-items: flex-start;
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
    flex-shrink: 0;
  }
  .parse-val {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
    text-align: right;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }
  .parse-val--mono {
    font-family: var(--font-mono);
    font-weight: var(--font-weight-normal);
    word-break: break-all;
  }
  .timelock-primary {
    font-weight: var(--font-weight-medium);
  }
  .timelock-sub {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-normal);
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
    background: var(--color-holding-vault);
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
    border-left: 4px solid var(--color-holding-vault);
    border-radius: var(--radius-md);
    width: 100%;
    max-width: 300px;
    box-sizing: border-box;
  }
  .scan-spinner {
    width: 16px; height: 16px; flex-shrink: 0;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
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
