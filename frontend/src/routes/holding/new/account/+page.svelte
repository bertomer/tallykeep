<!--
  Add Holding — Account wizard (3 steps).
  Spec: specs/next_iteration.md — "Add Holding – Account wizard"
  Mockups (all validated 2026-05-16 at 360×800):
    step 1 default:       mobile_add_holding_account_01_connect.html
    step 1 overage error: mobile_add_holding_account_01_connect_error_overage.html
    step 2 parseback:     mobile_add_holding_account_02_parseback.html
    step 3 success:       mobile_add_holding_account_03_success.html

  State machine: connect → parseback → success
  Back navigation:
    connect   → history.back()
    parseback → connect  (validateResult cleared; no holding exists yet)
    success   → no back; Done CTA → /home

  API call timing:
    Step 1 "Continue"     → POST /holdings/account/validate  (no DB write)
    Step 2 "Looks right"  → POST /holdings/account           (DB write + secret store)
    No further API calls on Step 3.

  Tap-to-clear rule (ADR-0011 / mockup header comment):
    On focus of either credential input AFTER an overage OR underage rejection,
    clear BOTH fields AND dismiss all danger bands in one motion.
    Fires on focus event, not on edit. Paste button does NOT trigger it.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { secureStorage, clipboard } from '$lib/native-bridge';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import WizardShell from '$lib/components/WizardShell.svelte';

  // -------------------------------------------------------------------------
  // Types
  // -------------------------------------------------------------------------

  type Step = 'connect' | 'parseback' | 'success';

  interface LedgerEntryPreview {
    kind: string;
    asset: string;
    timestamp: string;
  }

  // From POST /holdings/account/validate — no holding created yet.
  interface ValidateResult {
    adapter_id: string;
    btc_balance_sats: number;
    other_asset_tickers: string[];
    other_asset_total_count: number;
    recent_ledger_entries: LedgerEntryPreview[];
    ledger_total_count: number;
  }

  // From POST /holdings/account — holding committed to DB.
  interface CreateResult {
    holding_id: string;
    provider_id: string;
    name: string;
    adapter_id: string;
    display_name: string;
    btc_balance_sats: number;
    other_asset_tickers: string[];
    other_asset_total_count: number;
  }

  // -------------------------------------------------------------------------
  // Provider constants (v1: Kraken only)
  // -------------------------------------------------------------------------

  const PROVIDER = {
    slug: 'kraken',
    displayName: 'Kraken',
    adapterId: 'kraken',
    kind: 'exchange',
  };

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  let step = $state<Step>('connect');

  // Step 1 — credentials
  let apiKey = $state('');
  let privateKey = $state('');
  let privateKeyRevealed = $state(false);
  let overageError = $state<{ permissions: string[] } | null>(null);
  let underageError = $state<{ permissions: string[] } | null>(null);
  let connectGenError = $state<string | null>(null);

  // Step 2 — parseback
  let holdingName = $state('');
  let nameEditing = $state(false);
  let nameDraft = $state('');
  let parsbackError = $state<string | null>(null);

  // Shared
  let loading = $state(false);
  let serverUrl = $state('');
  let validateResult = $state<ValidateResult | null>(null);  // set after Step 1 validate
  let createResult = $state<CreateResult | null>(null);      // set after Step 2 create
  let providerSupportsWithdrawal = $state(false);

  // -------------------------------------------------------------------------
  // Computed
  // -------------------------------------------------------------------------

  let connectCtaDisabled = $derived(apiKey.trim() === '' || privateKey.trim() === '');

  // -------------------------------------------------------------------------
  // Formatters
  // -------------------------------------------------------------------------

  function formatSats(n: number): string {
    return n.toLocaleString('en-US');
  }

  function formatOtherAssets(tickers: string[], totalCount: number): string {
    if (totalCount === 0) return '';
    const rest = totalCount - tickers.length;
    const base = tickers.join(', ');
    return rest > 0 ? `${base}, + ${rest} more` : base;
  }

  function formatRelativeTime(isoTs: string): string {
    const diffMs = Date.now() - new Date(isoTs).getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    if (diffMins < 60) return `${Math.max(1, diffMins)}m ago`;
    const diffHrs = Math.floor(diffMs / 3_600_000);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffMs / 86_400_000);
    if (diffDays === 1) return 'yesterday';
    return `${diffDays}d ago`;
  }

  function formatEntryTitle(kind: string, asset: string): string {
    return `${kind.charAt(0).toUpperCase()}${kind.slice(1)} · ${asset}`;
  }

  // -------------------------------------------------------------------------
  // Tap-to-clear (ADR-0011 / mockup rule)
  // -------------------------------------------------------------------------

  function handleCredentialFocus() {
    if (overageError !== null || underageError !== null || connectGenError !== null) {
      apiKey = '';
      privateKey = '';
      overageError = null;
      underageError = null;
      connectGenError = null;
    }
  }

  // -------------------------------------------------------------------------
  // Paste helpers
  // -------------------------------------------------------------------------

  async function handlePasteApiKey() {
    const text = await clipboard.paste();
    if (text) { apiKey = text; }
  }

  async function handlePastePrivateKey() {
    const text = await clipboard.paste();
    if (text) { privateKey = text; }
  }

  // -------------------------------------------------------------------------
  // Event handlers — Step 1
  // -------------------------------------------------------------------------

  async function handleConnect() {
    if (connectCtaDisabled || loading) return;
    overageError = null;
    connectGenError = null;
    loading = true;
    try {
      const body = {
        adapter_id: PROVIDER.adapterId,
        api_key: apiKey.trim(),
        api_secret: privateKey.trim(),
      };

      const res = await fetch(`${serverUrl}/api/v1/holdings/account/validate`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 401) {
        const msg = ((data?.detail ?? '') as string).toLowerCase();
        if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
        await auth.clearCredential(); goto('/'); return;
      }

      if (res.status === 409 && data?.detail?.code === 'permission_mismatch') {
        const overage: string[] = data.detail.overage ?? [];
        const underage: string[] = data.detail.underage ?? [];
        if (overage.length > 0) overageError = { permissions: overage };
        if (underage.length > 0) underageError = { permissions: underage };
        return;
      }

      if (res.status === 422) {
        connectGenError = 'Kraken rejected these credentials. Double-check your API Key and Private Key.';
        return;
      }
      if (res.status === 502) {
        connectGenError = 'Could not reach Kraken. Check your internet connection and try again.';
        return;
      }
      if (!res.ok) {
        connectGenError = 'Something went wrong. Try again.';
        return;
      }

      validateResult = data as ValidateResult;
      holdingName = `${PROVIDER.displayName} account`;
      nameDraft = holdingName;
      step = 'parseback';
    } catch {
      connectGenError = 'Network error. Check your connection and try again.';
    } finally {
      loading = false;
    }
  }

  // -------------------------------------------------------------------------
  // Event handlers — Step 2
  // -------------------------------------------------------------------------

  async function handleLooksRight() {
    if (loading || !validateResult) return;
    parsbackError = null;

    const finalName = nameEditing ? (nameDraft.trim() || holdingName) : holdingName;

    loading = true;
    try {
      const body = {
        name: finalName,
        purpose: 'transit',
        declared_security: {
          custody_model: 'third_party',
          signing_model: 'not_applicable',
        },
        display_color: '#9c9388',
        display_order: 0,
        custodial_provider: {
          provider_kind: PROVIDER.kind,
          display_name: PROVIDER.displayName,
          adapter_id: PROVIDER.adapterId,
          api_key: apiKey.trim(),
          api_secret: privateKey.trim(),
        },
      };

      const res = await fetch(`${serverUrl}/api/v1/holdings/account`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 401) {
        const msg = ((data?.detail ?? '') as string).toLowerCase();
        if (msg.includes('locked') || msg.includes('unlock')) { goto('/unlock'); return; }
        await auth.clearCredential(); goto('/'); return;
      }

      if (!res.ok) {
        parsbackError = 'Could not save the Account. Check your connection and try again.';
        return;
      }

      createResult = data as CreateResult;
      holdingName = data.name ?? finalName;
      if (nameEditing) { nameEditing = false; }
      step = 'success';
    } catch {
      parsbackError = 'Network error while saving. Check your connection and try again.';
    } finally {
      loading = false;
    }
  }

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  onMount(async () => {
    if (!auth.loaded) await auth.load();
    if (!auth.isPaired) { goto('/'); return; }
    if (!auth.unlocked) { goto('/unlock'); return; }
    serverUrl = (await secureStorage.get('server_url')) ?? '';

    // Fetch provider capability matrix to gate the auto-sweep suggestion card.
    try {
      const res = await fetch(`${serverUrl}/api/v1/treasury/providers`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const providers = await res.json() as Array<{ slug: string; supports_withdrawal_keys: boolean }>;
        const krakenCap = providers.find(p => p.slug === PROVIDER.slug);
        providerSupportsWithdrawal = krakenCap?.supports_withdrawal_keys ?? false;
      }
    } catch { /* capability defaults to false — suggestion card stays hidden */ }
  });
</script>

<!-- =========================================================================
     STEP 1 — CONNECT
     ========================================================================= -->
{#if step === 'connect'}
<WizardShell
  stepNumber={1}
  showBack={true}
  onBack={() => history.back()}
  ctaLabel="Continue"
  loadingLabel="Connecting…"
  ctaDisabled={connectCtaDisabled}
  {loading}
  onCta={handleConnect}
>
  {#snippet children()}
  <div class="scroll-pad">

    <div class="step-head">
      <h1 class="step-heading">Connect a provider</h1>
      <p class="step-sub">
        An exchange, broker, or custodial bank where you hold funds. TallyKeep
        observes your balance with a read-only key. Automated withdrawal can be
        configured separately.
      </p>
    </div>

    <!-- Provider dropdown (v1: Kraken only) -->
    <label class="field-label" for="provider-pick">Provider</label>
    <button id="provider-pick" class="provider-dropdown" type="button"
            aria-haspopup="listbox" aria-expanded="false" disabled>
      <span class="provider-picked">
        <span class="provider-logo" aria-hidden="true">K</span>
        <span class="provider-name">Kraken</span>
      </span>
      <svg class="dropdown-chevron" viewBox="0 0 24 24" aria-hidden="true">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>

    <!-- Per-provider helper banner -->
    <div class="provider-hint" role="note">
      <svg class="hint-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8"  x2="12.01" y2="8"/>
      </svg>
      <div>
        <p class="hint-title">Create a read-only API key on Kraken Pro</p>
        <p class="hint-body">
          <strong>Settings → Connection and API → Create an API key.</strong>
          Name it <code>TallyKeep Read</code> and tick
          <strong>only</strong> <code>Query funds</code> and
          <code>Query ledger entries</code>.
        </p>
      </div>
    </div>

    <!-- Shown-once warning -->
    <div class="shown-once" role="alert">
      <svg class="warn-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M 12 3 L 22 21 L 2 21 Z"/>
        <line x1="12" y1="10" x2="12" y2="15"/>
        <line x1="12" y1="18" x2="12.01" y2="18"/>
      </svg>
      <div>
        <strong>Copy both keys before closing Kraken's dialog.</strong>
        If you lose one, you'll need to delete this key on Kraken and create a new one.
      </div>
    </div>

    <!-- Credentials -->
    <div class="credentials-section">

      <div class="field-group">
        <label class="field-label" for="api-key-input">
          API Key
          <span class="label-alias">Kraken: Clé API</span>
        </label>
        <div class="input-wrap">
          <input
            id="api-key-input"
            class="key-input"
            class:has-error={overageError !== null || underageError !== null}
            type="text"
            placeholder="bd4pcvVPyOem3l5k9+NV3…"
            aria-label="API Key"
            aria-invalid={overageError !== null || underageError !== null ? true : undefined}
            bind:value={apiKey}
            onfocus={handleCredentialFocus}
            onclick={handleCredentialFocus}
            ontouchstart={handleCredentialFocus}
          >
          <div class="input-actions">
            <button class="icon-btn paste-btn" type="button" aria-label="Paste API Key"
                    onclick={handlePasteApiKey}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="9" y="3"  width="6"  height="4"  rx="1"/>
                <rect x="5" y="5"  width="14" height="16" rx="2"/>
              </svg>
              Paste
            </button>
          </div>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label" for="private-key-input">
          Private Key
          <span class="label-alias">Kraken: Clé privée</span>
        </label>
        <div class="input-wrap">
          <input
            id="private-key-input"
            class="key-input"
            class:has-error={overageError !== null || underageError !== null}
            type={privateKeyRevealed ? 'text' : 'password'}
            placeholder="qRiDRMEYytD/oXc0vFUpQ70k7s…"
            aria-label="Private Key"
            aria-invalid={overageError !== null || underageError !== null ? true : undefined}
            bind:value={privateKey}
            onfocus={handleCredentialFocus}
            onclick={handleCredentialFocus}
            ontouchstart={handleCredentialFocus}
          >
          <div class="input-actions">
            <button class="icon-btn" type="button"
                    aria-label={privateKeyRevealed ? 'Hide Private Key' : 'Reveal Private Key'}
                    onclick={() => { privateKeyRevealed = !privateKeyRevealed; }}>
              {#if privateKeyRevealed}
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <line x1="2" y1="2" x2="22" y2="22"/>
                  <path d="M 6.7 6.7 Q 2 10 2 12 Q 6 19 12 19 Q 15 19 17.3 17.3"/>
                  <path d="M 9.9 4.2 Q 10.9 4 12 4 Q 18 4 22 12 Q 21 14 19.3 15.8"/>
                </svg>
              {:else}
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M 2 12 Q 6 5 12 5 Q 18 5 22 12 Q 18 19 12 19 Q 6 19 2 12 Z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              {/if}
            </button>
            <button class="icon-btn paste-btn" type="button" aria-label="Paste Private Key"
                    onclick={handlePastePrivateKey}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="9" y="3"  width="6"  height="4"  rx="1"/>
                <rect x="5" y="5"  width="14" height="16" rx="2"/>
              </svg>
              Paste
            </button>
          </div>
        </div>
      </div>

    </div>

    <!-- Danger band — overage error -->
    {#if overageError !== null}
      <div class="danger-band" role="alert">
        <svg class="danger-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <p class="danger-title">This key has too many permissions</p>
          <p class="danger-body">
            We accept only read access to keep your account exposure to a minimum.
            This one also has:
          </p>
          <ul class="danger-list">
            {#each overageError.permissions as perm (perm)}
              <li><code>{perm}</code></li>
            {/each}
          </ul>
          <p class="danger-body mt2">
            Replace these keys on Kraken Pro with ones that have
            <strong>ONLY</strong> <code>Query funds</code> and
            <code>Query ledger entries</code> ticked.
            Then paste the new pair here.
          </p>
        </div>
      </div>
    {/if}

    <!-- Danger band — underage error -->
    {#if underageError !== null}
      <div class="danger-band" role="alert">
        <svg class="danger-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <p class="danger-title">This API key is missing required permissions</p>
          <p class="danger-body">
            This key needs the following permissions to observe your account:
          </p>
          <ul class="danger-list">
            {#each underageError.permissions as perm (perm)}
              <li><code>{perm}</code></li>
            {/each}
          </ul>
          <p class="danger-body mt2">
            Replace these keys on Kraken Pro with ones that have
            <strong>ONLY</strong> <code>Query funds</code> and
            <code>Query ledger entries</code> ticked.
            Then paste the new pair here.
          </p>
        </div>
      </div>
    {/if}

    <!-- Generic connect error -->
    {#if connectGenError !== null}
      <div class="danger-band" role="alert">
        <svg class="danger-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <p class="danger-title">Connection failed</p>
          <p class="danger-body">{connectGenError}</p>
        </div>
      </div>
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
  onBack={() => { validateResult = null; parsbackError = null; nameEditing = false; step = 'connect'; }}
  ctaLabel="Looks right"
  ctaDisabled={validateResult === null}
  {loading}
  onCta={handleLooksRight}
>
  {#snippet children()}
  <div class="scroll-pad">

    <div class="step-head">
      <h1 class="step-heading">Here's what we read</h1>
      <p class="step-sub">
        Last check before we save it — does this match what you set up on Kraken?
      </p>
    </div>

    <!-- Name preview — limestone stripe -->
    <div class="name-preview" aria-label="Account name preview">
      {#if nameEditing}
        <input
          class="name-input"
          type="text"
          aria-label="Holding name"
          bind:value={nameDraft}
          onkeydown={(e) => {
            if (e.key === 'Enter') { holdingName = nameDraft.trim() || holdingName; nameEditing = false; }
            if (e.key === 'Escape') { nameDraft = holdingName; nameEditing = false; }
          }}
        />
        <button class="rename-btn" type="button"
                onclick={() => { holdingName = nameDraft.trim() || holdingName; nameEditing = false; }}>
          Done
        </button>
      {:else}
        <div>
          <span class="name-label">Will be named</span>
          <span class="name-value">{holdingName}</span>
        </div>
        <button class="rename-btn" type="button" aria-label="Rename this Account"
                onclick={() => { nameDraft = holdingName; nameEditing = true; }}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M 4 20 L 4 16 L 16 4 L 20 8 L 8 20 Z"/>
            <line x1="13" y1="7" x2="17" y2="11"/>
          </svg>
          Rename
        </button>
      {/if}
    </div>

    <!-- Parse card — 3 rows -->
    {#if validateResult}
    <div class="parse-card" aria-label="What the key gives us">
      <div class="parse-row">
        <span class="parse-key">Provider</span>
        <span class="parse-val">{PROVIDER.displayName}</span>
      </div>
      <div class="parse-row">
        <span class="parse-key">Permission</span>
        <span class="parse-val">
          Observe only
          <span class="parse-qualifier">Read-only — this key cannot move funds</span>
        </span>
      </div>
      {#if validateResult.other_asset_total_count > 0}
      <div class="parse-row">
        <span class="parse-key">Other assets</span>
        <span class="parse-val">
          {formatOtherAssets(validateResult.other_asset_tickers, validateResult.other_asset_total_count)}
          <span class="parse-qualifier">Read-only summary · not actionable from TallyKeep</span>
        </span>
      </div>
      {/if}
    </div>
    {/if}

    <!-- Activity preview card -->
    {#if validateResult}
    <div class="activity-preview" aria-label="Recent activity from Kraken ledger">
      <div class="activity-head">
        <span class="activity-label">Recent activity</span>
        <span class="activity-meta">From your ledger</span>
      </div>
      {#if validateResult.recent_ledger_entries.length === 0}
        <p class="activity-empty">No activity yet — your entries will surface here as they happen on Kraken.</p>
      {:else}
        <ul class="activity-list">
          {#each validateResult.recent_ledger_entries as entry (entry.timestamp + entry.kind + entry.asset)}
          <li class="activity-entry">
            <span class="activity-title">{formatEntryTitle(entry.kind, entry.asset)}</span>
            <span class="activity-time">{formatRelativeTime(entry.timestamp)}</span>
          </li>
          {/each}
        </ul>
        {#if validateResult.ledger_total_count > 3}
        <p class="activity-overflow">+ {validateResult.ledger_total_count - 3} more on your Account page</p>
        {/if}
      {/if}
    </div>
    {/if}

    {#if parsbackError !== null}
      <p class="parsback-error">{parsbackError}</p>
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

    <h1 class="success-heading">{createResult?.display_name ?? 'Account'} account connected</h1>
    <p class="success-sub">
      Your balance is live. It'll appear on Home alongside your other Holdings.
    </p>

    {#if createResult}
    <div class="balance-card" aria-label="Current BTC balance on {createResult.display_name}">
      <span class="balance-label">BTC balance</span>
      <span class="balance-amount">
        {formatSats(createResult.btc_balance_sats)}<span class="balance-unit">sats</span>
      </span>
    </div>

    {#if providerSupportsWithdrawal}
    <div class="suggestion-card" aria-label="Suggested next step">
      <h2 class="suggestion-title">Keep these sats under your control</h2>
      <p class="suggestion-body">
        {createResult.display_name} supports automated withdrawals. Let TallyKeep move
        your balance to one of your Holdings when it crosses a threshold you set.
      </p>
      <button class="suggestion-cta" type="button"
              onclick={() => goto(`/account/${createResult!.holding_id}/withdraw/configure`)}>
        Set up auto-sweep
      </button>
    </div>
    {/if}
    {/if}

  </div>
  {/snippet}
</WizardShell>
{/if}

<style>
  /* ---- shared scroll pad ---- */
  .scroll-pad {
    padding: var(--space-4) var(--space-4) var(--space-5);
  }

  /* ---- step headings ---- */
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

  /* ---- field label ---- */
  .field-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    display: block;
    margin: 0 0 var(--space-2);
  }
  .label-alias {
    text-transform: none;
    color: var(--color-text-dim);
    font-weight: var(--font-weight-normal);
    letter-spacing: 0;
    margin-left: var(--space-2);
  }

  /* ---- provider dropdown ---- */
  .provider-dropdown {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    cursor: default;
    text-align: left;
    font-family: inherit;
    color: var(--color-text);
    opacity: 0.9;
  }
  .provider-picked {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-width: 0;
  }
  .provider-logo {
    width: 32px; height: 32px; flex-shrink: 0;
    border-radius: var(--radius-sm);
    background: var(--color-bg);
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-base);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }
  .provider-name {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    line-height: 1.2;
  }
  .dropdown-chevron {
    width: 16px; height: 16px; flex-shrink: 0;
    color: var(--color-text-muted);
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }

  /* ---- helper banner ---- */
  .provider-hint {
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
    margin: 0 0 var(--space-1);
  }
  .hint-body { margin: 0; }
  .provider-hint code {
    font-family: var(--font-mono);
    font-size: 0.95em;
    background: rgba(0,0,0,0.04);
    padding: 1px 4px;
    border-radius: var(--radius-sm);
  }

  /* ---- shown-once warning ---- */
  .shown-once {
    margin-top: var(--space-2);
    padding: var(--space-3);
    background: var(--color-warning-soft);
    border: 1px solid var(--color-warning-border);
    border-radius: var(--radius-md);
    color: var(--color-warning-text-on-soft);
    font-size: var(--font-size-sm);
    line-height: var(--line-height-default);
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .warn-icon {
    width: 18px; height: 18px; flex-shrink: 0;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    margin-top: 1px;
  }
  .shown-once strong { font-weight: var(--font-weight-semibold); }

  /* ---- credentials section ---- */
  .credentials-section { margin-top: var(--space-5); }
  .field-group + .field-group { margin-top: var(--space-3); }

  .input-wrap { position: relative; }
  .key-input {
    width: 100%;
    padding: var(--space-3);
    padding-right: 110px;
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    color: var(--color-text);
    line-height: 1.4;
    box-sizing: border-box;
  }
  .key-input::placeholder { color: var(--color-text-dim); }
  .key-input:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 2px var(--color-primary-soft);
  }
  .key-input.has-error { border-color: var(--color-danger); }

  .input-actions {
    position: absolute;
    top: 50%;
    right: var(--space-2);
    transform: translateY(-50%);
    display: flex;
    gap: var(--space-1);
  }
  .icon-btn {
    width: 32px; height: 32px;
    display: inline-flex; align-items: center; justify-content: center;
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    color: var(--color-text);
    cursor: pointer;
  }
  .icon-btn:hover { background: var(--color-bg); }
  .icon-btn svg {
    width: 16px; height: 16px;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  }
  .paste-btn {
    width: auto;
    padding: 0 var(--space-2);
    gap: 4px;
    font-family: inherit;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    border-radius: var(--radius-pill);
  }
  .paste-btn svg { width: 12px; height: 12px; }

  /* ---- danger band ---- */
  .danger-band {
    margin-top: var(--space-4);
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
  .danger-icon {
    width: 18px; height: 18px; flex-shrink: 0;
    stroke: currentColor; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
    margin-top: 1px;
  }
  .danger-title {
    font-weight: var(--font-weight-semibold);
    margin: 0 0 var(--space-1);
  }
  .danger-body { margin: 0; }
  .danger-list {
    margin: var(--space-2) 0 0;
    padding-left: var(--space-4);
  }
  .danger-list li { margin-bottom: 2px; }
  .danger-band code {
    font-family: var(--font-mono);
    font-size: 0.95em;
    background: rgba(0,0,0,0.06);
    padding: 1px 4px;
    border-radius: var(--radius-sm);
  }
  .mt2 { margin-top: var(--space-2); }

  /* ---- name preview — account limestone stripe ---- */
  .name-preview {
    margin-bottom: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-account);
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

  /* ---- parse card ---- */
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
    min-width: 100px;
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
  .parse-qualifier {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-normal);
  }

  .parsback-error {
    font-size: var(--font-size-sm);
    color: var(--color-danger-text-on-soft, #dc2626);
    margin: var(--space-3) 0 0;
    text-align: center;
  }

  /* ---- activity preview card ---- */
  .activity-preview {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    margin-bottom: var(--space-3);
  }
  .activity-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: var(--space-2);
  }
  .activity-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
  }
  .activity-meta {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-normal);
  }
  .activity-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .activity-entry {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    min-width: 0;
  }
  .activity-entry + .activity-entry { border-top: 1px solid var(--color-border); }
  .activity-title {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
  }
  .activity-time {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-normal);
    flex-shrink: 0;
  }
  .activity-overflow {
    margin: var(--space-2) 0 0;
    padding-top: var(--space-2);
    border-top: 1px solid var(--color-border);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-align: center;
  }
  .activity-empty {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    margin: 0;
    line-height: var(--line-height-default);
  }

  /* ---- success step ---- */
  .success-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-6) var(--space-5);
    gap: var(--space-3);
    text-align: center;
  }
  .success-check {
    width: 64px; height: 64px;
    display: flex; align-items: center; justify-content: center;
    background: var(--color-holding-account);
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

  /* ---- balance card ---- */
  .balance-card {
    margin-top: var(--space-5);
    padding: var(--space-4) var(--space-5);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-account);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
    min-width: 260px;
  }
  .balance-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    margin-bottom: var(--space-1);
  }
  .balance-amount {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
    line-height: var(--line-height-tight);
    letter-spacing: -0.01em;
  }
  .balance-unit {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-muted);
    margin-left: var(--space-1);
  }

  /* ---- suggestion card ---- */
  .suggestion-card {
    margin-top: var(--space-5);
    padding: var(--space-4);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-holding-account);
    border-radius: var(--radius-md);
    text-align: left;
    min-width: 260px;
    max-width: 320px;
  }
  .suggestion-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0 0 var(--space-2);
    line-height: var(--line-height-tight);
  }
  .suggestion-body {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    margin: 0 0 var(--space-3);
  }
  .suggestion-cta {
    width: 100%;
    padding: var(--space-2) var(--space-3);
    background: transparent;
    color: var(--color-primary-strong);
    border: 1px solid var(--color-primary);
    border-radius: var(--radius-md);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
  }
  .suggestion-cta:hover { background: var(--color-primary-soft); }
</style>
