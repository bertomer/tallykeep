<!--
  Add Holding — Purse wizard (3 steps).
  Spec: specs/next_iteration.md — "Add Holding — Purse wizard"
  Mockups (all validated 2026-05-13 at 360×800):
    step 1 input:            mobile_add_holding_purse_input.html
    step 1 generate pre:     mobile_add_holding_purse_generate.html
    step 1 generate revealed: mobile_add_holding_purse_generate_revealed.html
    step 1 error inline:     mobile_add_holding_purse_input_error_inline.html
    step 1 error redirect:   mobile_add_holding_purse_input_error_redirect.html
    step 2 parseback:        mobile_add_holding_purse_parseback.html
    step 3 success imported: mobile_add_holding_purse_success_imported.html
    step 3 success generated: mobile_add_holding_purse_success_generated.html

  State machine: input → generate (generate path only) → parseback → success
  Mode 1 (import): input → parseback → success
  Mode 3 (generate): input → generate → parseback → success

  Back navigation:
    input     → history.back() (reopens picker if user came from ?sheet=add)
    generate  → input
    parseback → generate (generate mode) | input (import mode)
    success   → no back button; Done CTA → /home

  Vocabulary: "recovery phrase" (never "seed phrase") per mobile.md lock.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { DEV_MODE, secureStorage, clipboard } from '$lib/native-bridge';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { generateMnemonic, mnemonicToSeedSync } from '@scure/bip39';
  import { wordlist } from '@scure/bip39/wordlists/english.js';
  import { HDKey } from '@scure/bip32';
  import WizardShell from '$lib/components/WizardShell.svelte';

  // -------------------------------------------------------------------------
  // Types
  // -------------------------------------------------------------------------

  type Step = 'input' | 'generate' | 'parseback' | 'success';
  type Mode = 'import' | 'generate';

  type ErrorState =
    | { kind: 'single-address' }
    | { kind: 'multisig' }
    | { kind: 'parse'; message: string }
    | { kind: 'network'; message: string }
    | { kind: 'create'; message: string };

  interface ValidateResult {
    script_type: string;
    is_multisig: boolean;
    required_signers?: number;
    total_signers?: number;
    first_addresses: string[];
  }

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  let step = $state<Step>('input');
  let mode = $state<Mode>('import');

  // Step 1 — import path
  let source = $state('');
  let descriptorText = $state('');

  // Step 1 — generate path
  let generateRevealed = $state(false);
  let mnemonic = $state<string[]>([]);

  // Derived descriptor / key state (populated by generate or import)
  let derivedExpression = $state('');
  let derivedChangeExpression = $state<string | null>(null);
  let derivedNetwork = $state<'mainnet' | 'regtest'>('regtest');

  // Parseback display data (set after /descriptors/validate)
  let parseResult = $state<ValidateResult | null>(null);
  let scriptTypeLabel = $state('');
  let derivationPath = $state('');
  let masterKeyTrunc = $state('');

  // Parseback — name
  let holdingName = $state('');
  let nameEditing = $state(false);
  let nameDraft = $state('');

  // Shared
  let error = $state<ErrorState | null>(null);
  let errorDetailsOpen = $state(false);
  let loading = $state(false);
  let serverUrl = $state('');
  let autoWrapNote = $state<string | null>(null);

  // -------------------------------------------------------------------------
  // Constants
  // -------------------------------------------------------------------------

  const TESTNET_VERSIONS = { private: 0x04358394, public: 0x043587CF };

  const SOURCE_LABELS: Record<string, string> = {
    bluewallet: 'BlueWallet',
    electrum: 'Electrum',
    mutiny: 'Mutiny',
    nunchuk: 'Nunchuk',
    phoenix: 'Phoenix',
    sparrow: 'Sparrow',
    specter: 'Specter',
    other: 'Other',
  };

  const WALLET_TIPS: Record<string, string> = {
    bluewallet: 'Settings → Wallet → Export / Backup → Copy the Master Public Key (xpub).',
    electrum: 'Wallet → Information → Master Public Key.',
    mutiny: 'From the (self-hosted or Emergency Kit) export, copy the master public key or recover the 12-word seed in Sparrow to derive a descriptor.',
    nunchuk: 'Wallet → Settings → Wallet Configuration → Copy Wallet Descriptor.',
    phoenix: 'Settings → Wallet info → Wallet final → Copy the master public key (zpub…, path m/84\'/0\'/0). The swap-in wallet descriptors aren\'t supported here yet — paste the "Wallet final" zpub instead.',
    sparrow: 'File → Wallet Settings → Export → Output Descriptor.',
    specter: 'Wallet Settings → Advanced → Export → Public Key (output descriptor).',
    other: 'Paste any standard xpub / ypub / zpub or BIP 380 output descriptor. Single Bitcoin addresses (bc1q…, 1…, 3…) are rejected.',
  };

  const SCRIPT_TYPE_LABELS: Record<string, string> = {
    p2wpkh:      'Native SegWit · P2WPKH',
    p2sh_p2wpkh: 'Wrapped SegWit · P2SH-P2WPKH',
    p2pkh:       'Legacy · P2PKH',
    p2tr:        'Taproot · P2TR',
  };

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  // ── Base58check version-byte conversion ────────────────────────────────────
  // BDK only accepts standard xpub/tpub version bytes inside descriptors.
  // zpub/ypub/vpub/upub must be re-encoded with the standard bytes first.

  const B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

  function b58decode(s: string): Uint8Array {
    let n = 0n;
    for (const c of s) { const d = B58.indexOf(c); if (d < 0) throw new Error('bad b58'); n = n * 58n + BigInt(d); }
    let lead = 0; for (const c of s) { if (c === '1') lead++; else break; }
    const out: number[] = [];
    while (n > 0n) { out.unshift(Number(n & 0xffn)); n >>= 8n; }
    return new Uint8Array([...new Array(lead).fill(0), ...out]);
  }

  function b58encode(bytes: Uint8Array): string {
    let n = 0n; for (const b of bytes) n = n * 256n + BigInt(b);
    let s = ''; while (n > 0n) { s = B58[Number(n % 58n)] + s; n /= 58n; }
    for (const b of bytes) { if (b === 0) s = '1' + s; else break; }
    return s;
  }

  async function convertKeyVersion(key: string, ver: number[]): Promise<string> {
    const full = b58decode(key);              // 82 bytes: 78 payload + 4 checksum
    const payload = new Uint8Array(full.slice(0, 78));
    payload[0] = ver[0]; payload[1] = ver[1]; payload[2] = ver[2]; payload[3] = ver[3];
    const h1 = new Uint8Array(await crypto.subtle.digest('SHA-256', payload));
    const h2 = new Uint8Array(await crypto.subtle.digest('SHA-256', h1));
    return b58encode(new Uint8Array([...payload, ...h2.slice(0, 4)]));
  }

  // ── Auto-wrap helpers ───────────────────────────────────────────────────────

  function isBareExtendedKey(raw: string): boolean {
    if (!raw || /[([/]/.test(raw)) return false;
    const lo = raw.toLowerCase();
    return ['xpub','ypub','zpub','tpub','upub','vpub'].some(p => lo.startsWith(p));
  }

  interface AutoWrap { expression: string; changeExpression: string; note: string; }

  async function buildAutoWrapDescriptor(raw: string): Promise<AutoWrap | null> {
    if (!isBareExtendedKey(raw)) return null;
    const lo = raw.toLowerCase();
    // zpub → xpub version bytes, then wpkh()
    if (lo.startsWith('zpub')) {
      const k = await convertKeyVersion(raw, [0x04,0x88,0xB2,0x1E]);
      return { expression: `wpkh(${k}/0/*)`, changeExpression: `wpkh(${k}/1/*)`,
               note: 'Native SegWit (P2WPKH) — auto-detected from zpub' };
    }
    // vpub → tpub version bytes, then wpkh()
    if (lo.startsWith('vpub')) {
      const k = await convertKeyVersion(raw, [0x04,0x35,0x87,0xCF]);
      return { expression: `wpkh(${k}/0/*)`, changeExpression: `wpkh(${k}/1/*)`,
               note: 'Native SegWit (P2WPKH) — auto-detected from vpub' };
    }
    // ypub → xpub version bytes, then sh(wpkh())
    if (lo.startsWith('ypub')) {
      const k = await convertKeyVersion(raw, [0x04,0x88,0xB2,0x1E]);
      return { expression: `sh(wpkh(${k}/0/*))`, changeExpression: `sh(wpkh(${k}/1/*))`,
               note: 'Wrapped SegWit (P2SH-P2WPKH) — auto-detected from ypub' };
    }
    // upub → tpub version bytes, then sh(wpkh())
    if (lo.startsWith('upub')) {
      const k = await convertKeyVersion(raw, [0x04,0x35,0x87,0xCF]);
      return { expression: `sh(wpkh(${k}/0/*))`, changeExpression: `sh(wpkh(${k}/1/*))`,
               note: 'Wrapped SegWit (P2SH-P2WPKH) — auto-detected from upub' };
    }
    // xpub / tpub — already standard bytes, just wrap
    if (lo.startsWith('xpub'))
      return { expression: `wpkh(${raw}/0/*)`, changeExpression: `wpkh(${raw}/1/*)`,
               note: 'Native SegWit (P2WPKH) — auto-detected from xpub' };
    if (lo.startsWith('tpub'))
      return { expression: `wpkh(${raw}/0/*)`, changeExpression: `wpkh(${raw}/1/*)`,
               note: 'Native SegWit (P2WPKH) — auto-detected from tpub' };
    return null;
  }

  function detectNetwork(input: string): 'mainnet' | 'regtest' {
    if (/tpub|tprv|upub|uprv|vpub|vprv|Upub|Uprv|Vpub|Vprv/.test(input)) return 'regtest';
    return 'mainnet';
  }

  function formatScriptType(raw: string): string {
    return SCRIPT_TYPE_LABELS[raw] ?? raw;
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
    return flatten(err?.message ?? err?.detail ?? err?.error ?? '').toLowerCase();
  }

  function extractDescriptorMeta(descriptor: string): { derivation: string; xpub: string } {
    // Bracketed form: wpkh([fingerprint/84h/0h/0h]xpub.../0/*)
    const bracketed = descriptor.match(/\[([^\]]+)\]([a-zA-Z0-9]+)/);
    if (bracketed) {
      const parts = bracketed[1].split('/').slice(1); // drop fingerprint
      return {
        derivation: parts.length ? `m/${parts.join('/')}` : 'unknown',
        xpub: bracketed[2],
      };
    }
    // Bare xpub: wpkh(xpub.../0/*)
    const bare = descriptor.match(/\(([a-zA-Z0-9]{4,})\//);
    if (bare) return { derivation: 'unknown', xpub: bare[1] };
    return { derivation: 'unknown', xpub: '' };
  }

  function truncateKey(key: string): string {
    if (key.length <= 12) return key;
    return `${key.slice(0, 6)}…${key.slice(-5)}`;
  }

  function deriveAutoName(m: Mode, src: string, sType: string): string {
    if (m === 'generate') {
      return 'TallyKeep Purse';
    }
    if (src && src !== '') return `${SOURCE_LABELS[src] ?? src} Purse`;
    const scriptName = SCRIPT_TYPE_LABELS[sType];
    return scriptName ? scriptName.split('·')[0].trim() + ' Purse' : 'Purse';
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
  // Computed
  // -------------------------------------------------------------------------

  let inputCtaDisabled = $derived(
    descriptorText.trim() === '' || error?.kind === 'multisig'
  );

  let bareKeyDetected = $derived(isBareExtendedKey(descriptorText.trim()));

  // -------------------------------------------------------------------------
  // Event handlers
  // -------------------------------------------------------------------------

  async function handlePaste() {
    const text = await clipboard.paste();
    if (text) {
      descriptorText = text;
      error = null;
    }
  }

  async function handleGenerate() {
    // Generate mnemonic, derive BIP84 tpub, store mnemonic securely
    const phrase = generateMnemonic(wordlist);
    mnemonic = phrase.split(' ');

    const seed = mnemonicToSeedSync(phrase);
    const root = HDKey.fromMasterSeed(seed, TESTNET_VERSIONS);
    const account = root.derive("m/84'/1'/0'");
    const tpub = account.publicExtendedKey;

    derivedExpression = `wpkh(${tpub}/0/*)`;
    derivedChangeExpression = `wpkh(${tpub}/1/*)`;
    derivedNetwork = 'regtest';
    derivationPath = "m/84'/1'/0'";
    masterKeyTrunc = truncateKey(tpub);
    scriptTypeLabel = 'Native SegWit · P2WPKH';
    mode = 'generate';

    await secureStorage.set('purse-pending-mnemonic', phrase);

    generateRevealed = false;
    step = 'generate';
  }

  async function handleContinueInput() {
    const raw = descriptorText.trim();
    if (!raw) return;
    error = null;
    errorDetailsOpen = false;
    autoWrapNote = null;
    loading = true;
    try {
      const wrapped = await buildAutoWrapDescriptor(raw);
      const expression = wrapped ? wrapped.expression : raw;
      const changeExpr = wrapped ? wrapped.changeExpression : null;
      const network = detectNetwork(raw);
      const result = await validateDescriptor(expression, network);
      if (result.is_multisig) {
        error = { kind: 'multisig' };
        return;
      }
      parseResult = result;
      derivedExpression = expression;
      derivedChangeExpression = changeExpr;
      derivedNetwork = network;
      if (wrapped) autoWrapNote = wrapped.note;
      const meta = extractDescriptorMeta(expression);
      derivationPath = meta.derivation;
      masterKeyTrunc = truncateKey(meta.xpub);
      scriptTypeLabel = formatScriptType(result.script_type);
      holdingName = deriveAutoName('import', source, result.script_type);
      nameDraft = holdingName;
      step = 'parseback';
    } catch (e: unknown) {
      const err = e as Record<string, unknown>;
      const msg = extractApiError(err);
      if (err?._status === 401) {
        if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
        await auth.clearCredential(); goto('/'); return;
      }
      if (msg.includes('address') || msg.includes('single') || msg.includes('bech32')) {
        error = { kind: 'single-address' };
      } else if (msg) {
        error = { kind: 'parse', message: msg };
      } else {
        error = { kind: 'network', message: 'Could not reach the server. Check your connection.' };
      }
    } finally {
      loading = false;
    }
  }

  async function handleContinueGenerate() {
    error = null;
    loading = true;
    try {
      const result = await validateDescriptor(derivedExpression, derivedNetwork);
      parseResult = result;
      holdingName = deriveAutoName('generate', '', result.script_type);
      nameDraft = holdingName;
      step = 'parseback';
    } catch (e: unknown) {
      const err = e as Record<string, unknown>;
      const msg = extractApiError(err);
      if (err?._status === 401) {
        if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
        await auth.clearCredential(); goto('/'); return;
      }
      error = { kind: 'parse', message: msg || 'Could not validate the generated descriptor.' };
    } finally {
      loading = false;
    }
  }

  async function handleLooksRight() {
    if (loading) return;
    const finalName = nameEditing ? nameDraft.trim() || holdingName : holdingName;
    error = null;
    loading = true;
    try {
      const body = {
        name: finalName,
        purpose: 'spending',
        declared_security: {
          custody_model: 'self_single',
          signing_model: mode === 'generate' ? 'software_hot' : 'unknown',
          geographic_distribution: false,
          inheritance_configured: false,
        },
        purse_mode: mode === 'generate' ? 'on_device_tk_generated' : 'watch_only',
        descriptors: [{
          name: 'main',
          expression: derivedExpression,
          ...(derivedChangeExpression ? { change_expression: derivedChangeExpression } : {}),
          network: derivedNetwork,
          gap_limit: 20,
        }],
      };
      const res = await fetch(`${serverUrl}/api/v1/holdings/purse`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (data?.message ?? data?.detail ?? '').toLowerCase();
        if (res.status === 401) {
          if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
          await auth.clearCredential(); goto('/'); return;
        }
        const rawMsg: string = data?.message ?? data?.detail ?? '';
        const friendlyMsg = rawMsg.toLowerCase().includes('already exists')
          ? 'A Purse with this descriptor already exists.'
          : rawMsg || 'Could not create the Purse. Try again.';
        error = { kind: 'create', message: friendlyMsg };
        return;
      }
      // Trigger initial scan for each descriptor — synchronous on the backend,
      // so by the time we reach the success screen the holding shows "scanned".
      const descriptorIds: string[] = data?.descriptor_ids ?? [];
      await Promise.all(
        descriptorIds.map((id: string) =>
          fetch(`${serverUrl}/api/v1/descriptors/${id}/rescan`, {
            method: 'POST',
            headers: authHeaders(),
          }).catch(() => { /* non-critical — home will show "scanning" if bitcoind is unreachable */ })
        )
      );
      if (nameEditing) { holdingName = finalName; nameEditing = false; }
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

  function handleBackFromParseback() {
    error = null;
    autoWrapNote = null;
    step = mode === 'generate' ? 'generate' : 'input';
  }

  function handleBackFromGenerate() {
    step = 'input';
    mode = 'import';
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
     STEP 1 — INPUT (default path: generate button + import form)
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
      <h1 class="step-heading">Add a Purse</h1>
    </div>

    <!-- Generate accent card -->
    <button class="generate-btn" type="button" onclick={handleGenerate}>
      <span class="gen-icon-wrap" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M 12 3 L 13.5 9 L 19.5 10.5 L 13.5 12 L 12 18 L 10.5 12 L 4.5 10.5 L 10.5 9 Z"/>
          <line x1="18" y1="3" x2="18" y2="6"/>
          <line x1="19.5" y1="4.5" x2="16.5" y2="4.5"/>
          <line x1="6" y1="16" x2="6" y2="20"/>
          <line x1="8" y1="18" x2="4" y2="18"/>
        </svg>
      </span>
      <span>
        <span class="gen-label">Let TallyKeep generate a fresh Purse</span>
        <span class="gen-sub">Privately and securely stored on this device</span>
      </span>
      <svg class="gen-chevron" viewBox="0 0 24 24" aria-hidden="true" fill="none"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 6 15 12 9 18"/>
      </svg>
    </button>

    <div class="or-separator" aria-hidden="true">or</div>

    <!-- Import section -->
    <div class="import-block">
      <p class="section-header">Import from another wallet</p>

      <div class="source-block">
        <label class="field-label" for="source-pick">
          Source <span class="optional">optional</span>
        </label>
        <div class="select-wrap">
          <select id="source-pick" bind:value={source}
                  onchange={() => { error = null; }}>
            <option value="">Don't specify</option>
            <option value="bluewallet">BlueWallet</option>
            <option value="electrum">Electrum</option>
            <option value="mutiny">Mutiny</option>
            <option value="nunchuk">Nunchuk</option>
            <option value="phoenix">Phoenix</option>
            <option value="sparrow">Sparrow</option>
            <option value="specter">Specter</option>
          </select>
        </div>
      </div>

      <!-- Wallet tip banner — appears when source is selected -->
      {#if WALLET_TIPS[source] || !source}
        <div class="wallet-tip" role="note">
          <svg class="tip-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12" y2="16.5"/>
          </svg>
          <span>{WALLET_TIPS[source] ?? WALLET_TIPS['other']}</span>
        </div>
      {/if}

      <div class="descriptor-block">
        <label class="field-label" for="descriptor-input">Descriptor or xpub</label>
        <div class="descriptor-input-wrap">
          <textarea
            id="descriptor-input"
            class="descriptor-textarea"
            class:textarea--error={error?.kind === 'single-address' || error?.kind === 'parse' || error?.kind === 'network'}
            class:textarea--warn={error?.kind === 'multisig'}
            aria-label="Descriptor or xpub"
            aria-invalid={!!error}
            placeholder="Paste your xpub or output descriptor here…"
            bind:value={descriptorText}
            oninput={() => { error = null; errorDetailsOpen = false; }}
          ></textarea>
          <button class="paste-btn" type="button" aria-label="Paste from clipboard"
                  onclick={handlePaste}>
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="3" width="6" height="4" rx="1"/>
              <rect x="5" y="5" width="14" height="16" rx="2"/>
            </svg>
            Paste
          </button>
        </div>
      </div>

      {#if bareKeyDetected}
        <p class="auto-wrap-hint">
          Looks like a bare extended key — we'll try building a descriptor from it automatically.
        </p>
      {/if}
    </div>

  </div>
  {/snippet}

  {#snippet errorRegion()}
    {#if error?.kind === 'single-address'}
      <div class="wizard-error" role="alert">
        <svg class="error-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="error-title">That's a single Bitcoin address.</p>
          <p class="error-body">
            TallyKeep tracks wallets, not isolated addresses — paste
            the wallet's xpub or output descriptor instead.
          </p>
        </div>
      </div>
    {:else if error?.kind === 'network'}
      <div class="wizard-error" role="alert">
        <svg class="error-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="error-title">Couldn't read that descriptor.</p>
          <p class="error-body">{error.message}</p>
        </div>
      </div>
    {:else if error?.kind === 'parse'}
      <div class="wizard-error" role="alert">
        <svg class="error-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div class="error-content">
          <p class="error-title">Couldn't read that descriptor.</p>
          <p class="error-body">Check it came from a compatible wallet and try again.</p>
          <button class="error-details-toggle" type="button"
                  onclick={() => { errorDetailsOpen = !errorDetailsOpen; }}>
            {errorDetailsOpen ? 'Hide details' : 'Show details'}
          </button>
          {#if errorDetailsOpen}
            <p class="error-details-text">{error.message}</p>
          {/if}
        </div>
      </div>
    {:else if error?.kind === 'multisig'}
      <div class="wizard-error redirect" role="alert">
        <svg class="error-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M 12 2 L 2 22 L 22 22 Z"/>
          <line x1="12" y1="9" x2="12" y2="14"/>
          <line x1="12" y1="17" x2="12" y2="17.5"/>
        </svg>
        <div class="error-content">
          <p class="error-title">This is a multisig descriptor.</p>
          <p class="error-body">
            Multisig Holdings are Vaults in TallyKeep — multiple keys
            are required to move funds. Set this up as a Vault instead.
          </p>
          <button class="redirect-cta" type="button"
                  onclick={() => goto('/holding/new/vault')}>
            Set up as Vault
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 6 15 12 9 18"/>
            </svg>
          </button>
        </div>
      </div>
    {/if}
  {/snippet}

</WizardShell>

<!-- =========================================================================
     STEP 1 (alternate) — GENERATE path (pre-reveal and revealed)
     ========================================================================= -->
{:else if step === 'generate'}
<WizardShell
  stepNumber={1}
  showBack={true}
  onBack={handleBackFromGenerate}
  ctaLabel="Continue"
  ctaDisabled={false}
  {loading}
  onCta={handleContinueGenerate}
>
  {#snippet children()}
  <div class="scroll-pad gen-scroll">

    {#if DEV_MODE}
      <div class="dev-banner" role="note">
        <strong>Dev mode</strong>
        Browser builds store these keys in localStorage — fine for
        testing with trivial amounts. Real value belongs on the
        Capacitor app (Keychain / Keystore).
      </div>
    {/if}

    {#if !generateRevealed}
      <!-- Pre-reveal state -->
      <div class="step-head">
        <h1 class="step-heading">Your new Purse is ready</h1>
        <p class="step-sub">
          Twelve recovery words have been generated and stored
          privately on this device. Reveal them now to write them
          down — or come back to it later.
        </p>
      </div>

      <div class="seed-vault" aria-label="Recovery phrase, hidden until revealed">
        <div class="seed-vault-content">
          <button class="reveal-btn" type="button"
                  onclick={() => { generateRevealed = true; }}>
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M 1 12 C 4 5 8 3 12 3 C 16 3 20 5 23 12 C 20 19 16 21 12 21 C 8 21 4 19 1 12 Z"/>
              <circle cx="12" cy="12" r="3.5"/>
            </svg>
            Reveal my recovery phrase
          </button>
          <p class="reveal-note">
            Make sure you're somewhere private — no shoulder-surfers,
            no shared screens, no recording.
          </p>
        </div>
      </div>

    {:else}
      <!-- Revealed state -->
      <div class="step-head" style="margin-bottom: var(--space-3)">
        <h1 class="step-heading">Your recovery phrase</h1>
        <p class="step-sub">Write these 12 words down on paper, in order.</p>
      </div>

      <div class="seed-card">
        <div class="seed-aux-top">
          <span class="seed-card-label">12-word recovery phrase</span>
          <button class="hide-btn" type="button" aria-label="Hide the phrase"
                  onclick={() => { generateRevealed = false; }}>
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M 3 3 L 21 21"/>
              <path d="M 9.88 9.88 A 3.5 3.5 0 0 0 14.12 14.12"/>
              <path d="M 6 6 C 4 7.5 2.5 9.5 1 12 C 4 19 8 21 12 21 C 13.5 21 14.9 20.75 16.2 20.3"/>
              <path d="M 18 18 C 20 16.5 21.5 14.5 23 12 C 20 5 16 3 12 3 C 10.5 3 9.1 3.25 7.8 3.7"/>
            </svg>
            Hide
          </button>
        </div>
        <div class="seed-grid" aria-label="12-word recovery phrase">
          {#each mnemonic as word, i}
            <div class="seed-word">
              <span class="seed-num">{i + 1}</span>
              <span class="seed-word-text">{word}</span>
            </div>
          {/each}
        </div>
      </div>

    {/if}

    <!-- Warning block — visible in both pre-reveal and revealed states -->
    <div class="warning-block">
      <strong>Losing these words means losing this Purse and any
      funds in it.</strong> TallyKeep can't recover them. Write
      them on paper and store the paper somewhere only you can find.
    </div>

    {#if !generateRevealed}
      <p class="later-note">
        You can also reveal them later from
        <strong>Holdings → Purse → Information</strong>.
      </p>
    {:else}
      <p class="later-note">
        You can return to this view anytime from
        <strong>Holdings → Purse → Information</strong>.
      </p>
    {/if}

    {#if error?.kind === 'parse'}
      <div class="gen-error" role="alert">{error.message}</div>
    {/if}

  </div>
  {/snippet}

</WizardShell>

<!-- =========================================================================
     STEP 2 — PARSEBACK
     ========================================================================= -->
{:else if step === 'parseback'}
<WizardShell
  stepNumber={2}
  showBack={true}
  onBack={handleBackFromParseback}
  ctaLabel="Looks right"
  ctaDisabled={false}
  {loading}
  onCta={handleLooksRight}
>
  {#snippet children()}
  <div class="scroll-pad">

    <div class="step-head">
      <h1 class="step-heading">
        {mode === 'generate' ? "Here's what we generated for you" : "Here's what we read"}
      </h1>
      {#if mode === 'generate'}
        <div class="generated-badge">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px">
            <path d="M 12 3 L 13.5 9 L 19.5 10.5 L 13.5 12 L 12 18 L 10.5 12 L 4.5 10.5 L 10.5 9 Z"/>
          </svg>
          Generated by TallyKeep · seed on this device
        </div>
      {:else}
        <p class="step-sub">
          Check the first addresses match what your existing wallet
          shows. If they don't, go back and re-check the descriptor.
        </p>
      {/if}
    </div>

    <!-- Auto-wrap notice -->
    {#if autoWrapNote}
      <div class="auto-wrap-notice" role="note">
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <span><strong>Auto-detected:</strong> {autoWrapNote}. Verify the first addresses match your wallet before continuing.</span>
      </div>
    {/if}

    <!-- Auto-name preview row -->
    <div class="name-preview" aria-label="Purse name preview">
      {#if nameEditing}
        <input
          class="name-input"
          type="text"
          bind:value={nameDraft}
          aria-label="Edit Purse name"
          onkeydown={(e) => {
            if (e.key === 'Enter') { holdingName = nameDraft.trim() || holdingName; nameEditing = false; }
            if (e.key === 'Escape') { nameDraft = holdingName; nameEditing = false; }
          }}
        />
        <div class="name-edit-actions">
          <button class="name-save-btn" type="button"
                  onclick={() => { holdingName = nameDraft.trim() || holdingName; nameEditing = false; }}>
            Save
          </button>
          <button class="name-cancel-btn" type="button"
                  onclick={() => { nameDraft = holdingName; nameEditing = false; }}>
            Cancel
          </button>
        </div>
      {:else}
        <div>
          <span class="name-label">Will be named</span>
          <span class="name-value">{holdingName}</span>
        </div>
        <button class="rename-btn" type="button" aria-label="Rename this Purse"
                onclick={() => { nameDraft = holdingName; nameEditing = true; }}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 4 20 L 4 16 L 16 4 L 20 8 L 8 20 Z"/>
            <line x1="13" y1="7" x2="17" y2="11"/>
          </svg>
          Rename
        </button>
      {/if}
    </div>

    <!-- Parse metadata card -->
    <div class="parse-card" aria-label="Parsed descriptor metadata">
      <div class="parse-row">
        <span class="parse-key">Script type</span>
        <span class="parse-val">{scriptTypeLabel}</span>
      </div>
      {#if derivationPath && derivationPath !== 'unknown'}
        <div class="parse-row">
          <span class="parse-key">Derivation</span>
          <span class="parse-val mono">{derivationPath}</span>
        </div>
      {/if}
      {#if masterKeyTrunc}
        <div class="parse-row">
          <span class="parse-key">Master key</span>
          <span class="parse-val mono">{masterKeyTrunc}</span>
        </div>
      {/if}
    </div>

    <!-- First addresses card -->
    {#if parseResult?.first_addresses?.length}
      <div class="addresses-card" aria-label="First derived addresses">
        <div class="addr-card-title">First three addresses</div>
        <p class="addr-card-sub">
          {#if mode === 'import'}
            Open your other wallet (Sparrow, Electrum, BlueWallet…) and
            confirm these match its first three receive addresses.
          {:else}
            These are the first receive addresses your new Purse will use.
          {/if}
        </p>
        {#each parseResult.first_addresses.slice(0, 3) as addr, i}
          <div class="addr-row">
            <span class="addr-idx">{i}</span>
            <span class="addr-text">{addr}</span>
            <button class="copy-icon-btn" type="button" aria-label="Copy address {i}"
                    onclick={() => handleCopyAddress(addr)}>
              <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="3" width="6" height="4" rx="1"/>
                <rect x="5" y="5" width="14" height="16" rx="2"/>
              </svg>
            </button>
          </div>
        {/each}
      </div>
    {/if}

  </div>
  {/snippet}

  {#snippet errorRegion()}
    {#if error?.kind === 'create'}
      <div class="wizard-error" role="alert">
        <svg class="error-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12" y2="16.5"/>
        </svg>
        <div>
          <p class="error-title">Couldn't create the Purse.</p>
          <p class="error-body">{error.message}</p>
        </div>
      </div>
    {/if}
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
  <div class="success-scroll">
    <div class="success-body">

      <div class="success-indicator-lg" aria-hidden="true">✓</div>

      {#if mode === 'import'}
        <h1 class="success-heading">Purse added</h1>
        <p class="success-sub">
          We're scanning the chain to load this Purse's balance and
          history. It usually takes a few seconds.
        </p>
        <div class="scan-row" role="status">
          <div class="spinner" aria-hidden="true"></div>
          <span class="scan-label">Scanning…</span>
          <span class="scan-hint">balance will appear on Home shortly</span>
        </div>
      {:else}
        <h1 class="success-heading">Purse ready</h1>
        <p class="success-sub">
          Your new Purse is set up. The keys live on this device.
          It has no funds yet — receive your first deposit when
          you're ready.
        </p>
        <div class="balance-row">
          <span class="balance-amount">0</span>
          <span class="balance-unit">sats</span>
          <span class="balance-hint">· fresh wallet</span>
        </div>
        <button class="receive-link" type="button" disabled aria-disabled="true">
          Show a receive address
          <span class="future-label">· next iteration</span>
        </button>
      {/if}

    </div>
  </div>
  {/snippet}

</WizardShell>
{/if}

<style>
  /* ---------- Shared scroll padding ---------- */
  .scroll-pad {
    padding: var(--space-4) var(--space-4) var(--space-5);
  }

  /* ---------- Step heading ---------- */
  .step-head { margin-bottom: var(--space-4); }
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

  /* ---------- STEP 1 — generate button ---------- */
  .generate-btn {
    width: 100%;
    display: grid;
    grid-template-columns: 36px 1fr 18px;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-primary-soft);
    border: 1.5px solid var(--color-primary);
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    color: var(--color-text);
    cursor: pointer;
    text-align: left;
  }
  .generate-btn:hover { background: var(--color-primary-soft); border-color: var(--color-primary-strong); }
  .gen-icon-wrap {
    width: 36px; height: 36px;
    display: inline-flex; align-items: center; justify-content: center;
    background: var(--color-surface);
    border-radius: var(--radius-md);
    color: var(--color-primary-strong);
  }
  .gen-icon-wrap svg { width: 22px; height: 22px; }
  .gen-label {
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary-strong);
    display: block;
  }
  .gen-sub {
    display: block;
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-normal);
    margin-top: 2px;
  }
  .gen-chevron {
    width: 18px; height: 18px;
    stroke: var(--color-primary-strong);
  }

  /* ---------- STEP 1 — or separator ---------- */
  .or-separator {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin: var(--space-4) 0 var(--space-3);
    color: var(--color-text-dim);
    font-size: var(--font-size-xs);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: var(--font-weight-semibold);
  }
  .or-separator::before,
  .or-separator::after {
    content: ''; flex: 1; height: 1px;
    background: var(--color-border);
  }

  /* ---------- STEP 1 — import section ---------- */
  .section-header {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    margin: 0 0 var(--space-3);
  }
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
  .optional {
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
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    color: var(--color-text);
    appearance: none;
    cursor: pointer;
  }
  .select-wrap::after {
    content: '';
    position: absolute;
    top: 50%; right: var(--space-3);
    width: 8px; height: 8px;
    border-right: 2px solid var(--color-text-muted);
    border-bottom: 2px solid var(--color-text-muted);
    transform: translateY(-75%) rotate(45deg);
    pointer-events: none;
  }

  /* ---------- Wallet tip banner ---------- */
  .wallet-tip {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    margin-bottom: var(--space-3);
    padding: var(--space-3);
    background: var(--color-info-soft);
    border: 1px solid var(--color-info-border);
    border-radius: var(--radius-md);
    color: var(--color-info-text-on-soft);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
  }
  .tip-icon {
    width: 16px; height: 16px; flex-shrink: 0;
    margin-top: 1px;
  }

  /* ---------- Descriptor textarea ---------- */
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
  .descriptor-textarea:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 2px var(--color-primary-soft);
  }
  .descriptor-textarea.textarea--error { border-color: var(--color-danger-border); }
  .descriptor-textarea.textarea--error:focus {
    border-color: var(--color-danger);
    box-shadow: 0 0 0 2px var(--color-danger-soft);
  }
  .descriptor-textarea.textarea--warn { border-color: var(--color-warning-border); }
  .descriptor-textarea.textarea--warn:focus {
    border-color: var(--color-warning);
    box-shadow: 0 0 0 2px var(--color-warning-soft);
  }
  .paste-btn {
    position: absolute;
    top: var(--space-2);
    right: var(--space-2);
    padding: var(--space-1) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-pill);
    font-family: var(--font-sans);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .paste-btn:hover { background: var(--color-bg); }
  .paste-btn svg { width: 12px; height: 12px; }

  /* ---------- Auto-wrap hint (below textarea) ---------- */
  .auto-wrap-hint {
    margin: var(--space-2) 0 0;
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
  }

  /* ---------- Auto-wrap notice (parseback) ---------- */
  .auto-wrap-notice {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    margin-bottom: var(--space-3);
    padding: var(--space-3);
    background: var(--color-info-soft);
    border: 1px solid var(--color-info-border);
    border-radius: var(--radius-md);
    color: var(--color-info-text-on-soft);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
  }
  .auto-wrap-notice svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }
  .auto-wrap-notice strong { font-weight: var(--font-weight-semibold); }

  /* ---------- Footer error regions ---------- */
  .wizard-error {
    margin-bottom: var(--space-3);
    padding: var(--space-3);
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius-md);
    color: var(--color-danger-text-on-soft);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .wizard-error.redirect {
    background: var(--color-warning-soft);
    border-color: var(--color-warning-border);
    color: var(--color-warning-text-on-soft);
  }
  .error-icon {
    width: 18px; height: 18px; flex-shrink: 0;
    margin-top: 1px;
  }
  .error-content { flex: 1; min-width: 0; }
  .wizard-error > div { min-width: 0; }
  .error-title { font-weight: var(--font-weight-semibold); margin: 0 0 2px; }
  .error-body  { margin: 0 0 var(--space-3); overflow-wrap: break-word; }
  .error-body:last-child { margin-bottom: 0; }
  .redirect-cta {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: var(--space-2) var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-warning-text-on-soft);
    cursor: pointer;
  }
  .redirect-cta svg { width: 14px; height: 14px; }

  .error-details-toggle {
    background: transparent;
    border: none;
    padding: 0;
    font-family: var(--font-sans);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-danger-text-on-soft);
    cursor: pointer;
    text-decoration: underline;
    text-underline-offset: 2px;
    margin-top: var(--space-1);
  }
  .error-details-text {
    margin: var(--space-2) 0 0;
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    color: var(--color-danger-text-on-soft);
    line-height: 1.5;
    overflow-wrap: break-word;
    word-break: break-word;
    opacity: 0.8;
  }

  /* ---------- STEP 1 generate — scroll area ---------- */
  .gen-scroll {
    display: flex;
    flex-direction: column;
    padding: var(--space-4) var(--space-4) var(--space-5);
  }

  /* ---------- DEV MODE banner ---------- */
  .dev-banner {
    margin-bottom: var(--space-4);
    padding: var(--space-3);
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    border-left: 4px solid var(--color-danger);
    border-radius: var(--radius-sm);
    color: var(--color-danger-text-on-soft);
    font-size: var(--font-size-xs);
    line-height: var(--line-height-default);
  }
  .dev-banner strong {
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 2px;
    font-weight: var(--font-weight-bold);
  }

  /* ---------- Seed vault (pre-reveal) ---------- */
  .seed-vault {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: var(--space-4) 0;
    padding: var(--space-5) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-purse);
    border-radius: var(--radius-md);
    min-height: 280px;
    position: relative;
  }
  .seed-vault::before {
    content: '';
    position: absolute;
    inset: 12px;
    background:
      repeating-linear-gradient(
        45deg,
        transparent 0,
        transparent 12px,
        rgba(0,0,0,0.03) 12px,
        rgba(0,0,0,0.03) 24px
      );
    border-radius: var(--radius-sm);
    pointer-events: none;
  }
  .seed-vault-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .reveal-btn {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-5);
    background: var(--color-primary);
    color: var(--color-on-primary);
    border: 0;
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    box-shadow: var(--shadow-md);
  }
  .reveal-btn:hover { background: var(--color-primary-strong); }
  .reveal-btn svg { width: 20px; height: 20px; }
  .reveal-note {
    position: relative;
    z-index: 1;
    margin-top: var(--space-3);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-align: center;
    line-height: var(--line-height-default);
    max-width: 240px;
  }

  /* ---------- Seed card (revealed) ---------- */
  .seed-card {
    margin: var(--space-3) 0;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-purse);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4) var(--space-4);
  }
  .seed-aux-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-3);
  }
  .seed-card-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
  }
  .hide-btn {
    background: transparent; border: 0; padding: 0;
    font-family: var(--font-sans); font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary-strong);
    cursor: pointer;
    display: inline-flex; align-items: center; gap: 4px;
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .hide-btn svg { width: 12px; height: 12px; }
  .seed-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-2) var(--space-3);
  }
  .seed-word {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
    padding: var(--space-2);
    background: var(--color-bg);
    border-radius: var(--radius-sm);
  }
  .seed-num {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    font-variant-numeric: tabular-nums;
    width: 14px;
    flex-shrink: 0;
    text-align: right;
  }
  .seed-word-text {
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
  }

  /* ---------- Warning block (both generate states) ---------- */
  .warning-block {
    margin: var(--space-3) 0 0;
    padding: var(--space-3);
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    color: var(--color-warning-text-on-soft);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
  }
  .warning-block strong { font-weight: var(--font-weight-semibold); }
  .later-note {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    text-align: center;
    margin: var(--space-3) 0 0;
  }
  .later-note strong { color: var(--color-text); font-weight: var(--font-weight-semibold); }
  .gen-error {
    margin-top: var(--space-3);
    padding: var(--space-3);
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius-md);
    color: var(--color-danger-text-on-soft);
    font-size: var(--font-size-sm);
  }

  /* ---------- STEP 2 — parseback ---------- */
  .generated-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-2);
    padding: var(--space-1) var(--space-3);
    background: var(--color-primary-soft);
    border: 1px solid var(--color-primary);
    border-radius: var(--radius-pill);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary-strong);
  }

  /* Name preview row */
  .name-preview {
    margin-bottom: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-purse);
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
  .rename-btn {
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-family: var(--font-sans);
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
  .rename-btn svg { width: 12px; height: 12px; }
  .name-input {
    flex: 1;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border-focus);
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    color: var(--color-text);
    background: var(--color-surface);
    min-width: 0;
  }
  .name-input:focus { outline: none; box-shadow: 0 0 0 2px var(--color-primary-soft); }
  .name-edit-actions {
    display: flex;
    gap: var(--space-2);
    flex-shrink: 0;
  }
  .name-save-btn,
  .name-cancel-btn {
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    border: 1px solid var(--color-border-strong);
  }
  .name-save-btn {
    background: var(--color-primary);
    color: var(--color-on-primary);
    border-color: var(--color-primary);
  }
  .name-save-btn:hover { background: var(--color-primary-strong); }
  .name-cancel-btn {
    background: transparent;
    color: var(--color-text);
  }
  .name-cancel-btn:hover { background: var(--color-bg); }

  /* Parse card */
  .parse-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    margin-bottom: var(--space-3);
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
    flex-shrink: 0;
  }
  .parse-val {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
    text-align: right;
  }
  .parse-val.mono {
    font-family: var(--font-mono);
    font-weight: var(--font-weight-normal);
  }

  /* Addresses card */
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
    margin: var(--space-2) 0 var(--space-2);
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
  .copy-icon-btn {
    width: 28px; height: 28px;
    display: inline-flex; align-items: center; justify-content: center;
    background: transparent; border: 0;
    border-radius: var(--radius-sm);
    color: var(--color-text-dim);
    cursor: pointer;
  }
  .copy-icon-btn:hover { background: var(--color-bg); color: var(--color-text); }
  .copy-icon-btn svg { width: 14px; height: 14px; }

  /* ---------- STEP 3 — success ---------- */
  .success-scroll {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }
  .success-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-7) var(--space-5);
    gap: var(--space-3);
    text-align: center;
  }
  .success-indicator-lg {
    width: 72px; height: 72px;
    border-radius: 50%;
    background: var(--color-success-soft);
    color: var(--color-success-text-on-soft);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
    font-weight: var(--font-weight-bold);
    line-height: 1;
    flex-shrink: 0;
  }
  .success-heading {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: var(--line-height-tight);
    margin: var(--space-3) 0 0;
  }
  .success-sub {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 280px;
    margin: 0;
  }

  /* Scan row (import success) */
  .scan-row {
    margin-top: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-purse);
    border-radius: var(--radius-md);
    display: inline-flex;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--font-size-sm);
    color: var(--color-text);
  }
  .spinner {
    width: 18px; height: 18px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .scan-label { font-weight: var(--font-weight-semibold); }
  .scan-hint { color: var(--color-text-muted); }

  /* Balance row (generate success) */
  .balance-row {
    margin-top: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-purse);
    border-radius: var(--radius-md);
    display: inline-flex;
    align-items: baseline;
    gap: var(--space-2);
    font-size: var(--font-size-sm);
  }
  .balance-amount {
    font-family: var(--font-sans);
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }
  .balance-unit { color: var(--color-text-muted); font-size: var(--font-size-sm); }
  .balance-hint { color: var(--color-text-muted); margin-left: var(--space-2); }

  .receive-link {
    margin-top: var(--space-3);
    background: transparent;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-5);
    font-family: var(--font-sans);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    cursor: not-allowed;
    opacity: 0.6;
  }
  .future-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    margin-left: var(--space-2);
  }
</style>
