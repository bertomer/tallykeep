<!--
  Onboarding 02 — Paired
  State machine: loading → initial (biometric) | no-biometric
    initial → skip-confirm (bottom sheet) | biometric-done
  Matches: specs/UI/mockups/mobile_onboarding_02_paired*.html (validated 2026-05-10)
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { preferences } from '$lib/stores/preferences.svelte';
  import { biometric, secureStorage } from '$lib/native-bridge';
  import WordmarkIcony from '$lib/components/WordmarkIcony.svelte';
  import DevGate from '$lib/components/DevGate.svelte';

  type PairedState = 'loading' | 'initial' | 'skip-confirm' | 'biometric-done' | 'no-biometric';

  let pairedState = $state<PairedState>('loading');
  let serverLabel = $state('');
  let serverEndpoint = $state('');

  onMount(async () => {
    if (!preferences.loaded) await preferences.load();

    const rawUrl = (await secureStorage.get('server_url')) ?? '';
    try {
      serverEndpoint = new URL(rawUrl).host;
    } catch {
      serverEndpoint = rawUrl;
    }

    try {
      const resp = await fetch(`${rawUrl}/api/v1/server/info`);
      if (resp.ok) {
        const data = await resp.json();
        serverLabel = data.server_label ?? '';
      }
    } catch { /* label stays empty */ }

    const canBio = await biometric.canUseBiometric();
    pairedState = canBio ? 'initial' : 'no-biometric';
  });

  async function handleEnableBiometric() {
    const ok = await biometric.unlock();
    if (ok) {
      await preferences.setBiometricEnabled(true);
      pairedState = 'biometric-done';
    }
  }

  async function handleConfirmPassphraseOnly() {
    await preferences.setBiometricEnabled(false);
    goto('/home');
  }

  function handleContinue() {
    goto('/home');
  }
</script>

<DevGate />

<div class="phone-screen safe-top safe-bottom" style="position: relative;">

  {#if pairedState === 'loading'}
    <!-- transitions out quickly on mount -->

  {:else if pairedState === 'biometric-done'}
    <div class="brand-strip">
      <WordmarkIcony width={280} />
    </div>

    <div class="allset-block">
      <div class="success-indicator lg" aria-hidden="true">✓</div>
      <div class="heading">All set</div>
      <div class="summary">
        Your TallyKeep is ready. We'll ask for your biometric each
        time you open the app.
      </div>

      <div class="facts">
        {#if serverLabel}
          <div class="fact-row">
            <span class="k">Connected to</span>
            <span class="v">{serverLabel}</span>
          </div>
        {/if}
        {#if serverEndpoint}
          <div class="fact-row">
            <span class="k">Endpoint</span>
            <span class="v mono">{serverEndpoint}</span>
          </div>
        {/if}
        <div class="fact-row">
          <span class="k">Daily unlock</span>
          <span class="v">Biometric · passphrase fallback</span>
        </div>
        <div class="fact-row">
          <span class="k">Deep recovery</span>
          <span class="v">Re-pair from desktop</span>
        </div>
      </div>

      <div class="recovery-note">
        Day-to-day, biometric unlocks the app and your TallyKeep
        passphrase is always available as a fallback — same passphrase
        as your server, nothing new to remember. If you ever lose
        access entirely (phone wiped, app reinstalled), re-pair from
        your desktop with a fresh QR.
      </div>
    </div>

    <div class="cta-stack">
      <button class="btn-primary-block" onclick={handleContinue}>Continue</button>
    </div>

  {:else}
    <!-- initial | skip-confirm | no-biometric share the header -->
    <div class="brand-strip">
      <WordmarkIcony width={280} />
    </div>

    <div class="paired-block">
      <div class="success-indicator" aria-hidden="true">✓</div>
      <div class="label-line">Paired with your TallyKeep</div>
      {#if serverLabel}
        <div class="server-label">{serverLabel}</div>
      {/if}
    </div>

    <div class="section-divider"></div>

    {#if pairedState === 'no-biometric'}
      <div class="no-biometric-block">
        <h1>This device doesn't have biometric</h1>
        <div class="lede">
          No Face ID, Touch ID, or fingerprint sensor available — that's fine.
        </div>
        <div class="info-block">
          <div class="info-label">How TallyKeep stays locked</div>
          <div class="info-body">
            You'll unlock TallyKeep with your <strong>passphrase</strong>
            each time you open the app — the same passphrase as your
            server, nothing new to remember. If you ever lose access
            entirely (phone wiped, app reinstalled), re-pair from your
            desktop with a fresh QR.
          </div>
        </div>
      </div>

      <div class="cta-stack">
        <button class="btn-primary-block" onclick={handleConfirmPassphraseOnly}>Continue</button>
      </div>

    {:else}
      <!-- initial and skip-confirm -->
      <div class="biometric-prompt">
        <h1>Faster unlock with biometric?</h1>
        <div class="modality-hint">
          Face ID, Touch ID, or fingerprint — your phone decides which.
          Without it, you'll type your TallyKeep passphrase each time.
        </div>
      </div>

      <div class="cta-stack">
        <button class="btn-primary-block" onclick={handleEnableBiometric}>Enable biometric</button>
        <button
          class="btn-text-link"
          onclick={() => { pairedState = 'skip-confirm'; }}
        >
          Skip — use passphrase only
        </button>
      </div>

      {#if pairedState === 'skip-confirm'}
        <div
          class="scrim"
          role="presentation"
          onclick={() => { pairedState = 'initial'; }}
        ></div>
        <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="skip-title">
          <div class="grab-handle" aria-hidden="true"></div>
          <h2 id="skip-title">Use passphrase only?</h2>
          <div class="sheet-body">
            You'll type your TallyKeep passphrase each time you open
            the app — the same passphrase as your server, nothing new
            to remember. <strong>You can enable biometric anytime in
            Settings.</strong>
          </div>
          <div class="sheet-actions">
            <button
              class="btn-cancel"
              onclick={() => { pairedState = 'initial'; }}
            >
              Cancel — set up biometric
            </button>
            <button class="btn-skip-confirm" onclick={handleConfirmPassphraseOnly}>
              Continue with passphrase only
            </button>
          </div>
        </div>
      {/if}
    {/if}
  {/if}

</div>

<style>
  .brand-strip {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-5) var(--space-4) var(--space-4);
  }

  /* ── Success indicator ── */
  .success-indicator {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--color-primary);
    color: var(--color-on-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-bold);
    flex-shrink: 0;
  }
  .success-indicator.lg {
    width: 64px;
    height: 64px;
    font-size: var(--font-size-xl);
  }

  /* ── Paired header block ── */
  .paired-block {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4) var(--space-4);
    text-align: center;
  }
  .paired-block .label-line {
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin-top: var(--space-2);
  }
  .paired-block .server-label {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
  }

  .section-divider {
    flex-shrink: 0;
    height: 1px;
    background: var(--color-border);
    margin: 0 var(--space-4);
  }

  /* ── Biometric prompt ── */
  .biometric-prompt {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: var(--space-5) var(--space-4) var(--space-4);
    overflow-y: auto;
  }
  .biometric-prompt h1 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    line-height: var(--line-height-tight);
    color: var(--color-text);
    margin: 0 0 var(--space-2);
    text-align: center;
  }
  .modality-hint {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    text-align: center;
    margin-bottom: var(--space-5);
    line-height: var(--line-height-default);
  }

  /* ── No biometric block ── */
  .no-biometric-block {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: var(--space-5) var(--space-4) var(--space-4);
    overflow-y: auto;
  }
  .no-biometric-block h1 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    line-height: var(--line-height-tight);
    color: var(--color-text);
    margin: 0 0 var(--space-2);
    text-align: center;
  }
  .lede {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    text-align: center;
    margin-bottom: var(--space-4);
    line-height: var(--line-height-default);
  }
  .info-block {
    background: var(--color-info-soft);
    border: 1px solid var(--color-info-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
  }
  .info-label {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    color: var(--color-info-text-on-soft);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--space-2);
  }
  .info-body {
    font-size: var(--font-size-sm);
    color: var(--color-info-text-on-soft);
    line-height: var(--line-height-default);
  }
  .info-body strong { font-weight: var(--font-weight-semibold); }

  /* ── All-set block (biometric done) ── */
  .allset-block {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-5) var(--space-4);
    text-align: center;
    gap: var(--space-3);
    overflow-y: auto;
  }
  .allset-block .heading {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin-top: var(--space-3);
  }
  .allset-block .summary {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 280px;
  }

  .facts {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    margin-top: var(--space-3);
    text-align: left;
    width: 100%;
    max-width: 320px;
  }
  .fact-row {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    font-size: var(--font-size-sm);
  }
  .fact-row:not(:last-child) { border-bottom: 1px dashed var(--color-border); }
  .fact-row .k { color: var(--color-text-muted); }
  .fact-row .v {
    color: var(--color-text);
    font-weight: var(--font-weight-medium);
    text-align: right;
  }
  .fact-row .v.mono {
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
  }
  .recovery-note {
    margin-top: var(--space-3);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    max-width: 320px;
    text-align: center;
  }

  /* ── CTA stack ── */
  .cta-stack {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: 0 var(--space-4) var(--space-4);
    margin-top: auto;
  }
  .btn-primary-block {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-family: var(--font-sans);
    font-weight: var(--font-weight-semibold);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-primary);
    background: var(--color-primary);
    color: var(--color-on-primary);
    text-align: center;
    cursor: pointer;
  }
  .btn-text-link {
    background: transparent;
    border: none;
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
    font-family: var(--font-sans);
    padding: var(--space-2);
    text-align: center;
    cursor: pointer;
  }
  .btn-text-link:hover { color: var(--color-text); }

  /* ── Bottom sheet + scrim ── */
  .scrim {
    position: absolute;
    inset: 0;
    background: var(--color-overlay);
    z-index: 50;
  }
  .sheet {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--color-surface);
    border-top-left-radius: var(--radius-xl);
    border-top-right-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
    padding: var(--space-4) var(--space-4) var(--space-5);
    z-index: 60;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .grab-handle {
    width: 36px;
    height: 4px;
    border-radius: var(--radius-pill);
    background: var(--color-border-strong);
    margin: 0 auto var(--space-1);
  }
  .sheet h2 {
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    margin: 0;
  }
  .sheet-body {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
  }
  .sheet-body strong {
    color: var(--color-text);
    font-weight: var(--font-weight-semibold);
  }
  .sheet-actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin-top: var(--space-2);
  }
  .btn-cancel {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-family: var(--font-sans);
    font-weight: var(--font-weight-semibold);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-strong);
    background: var(--color-surface);
    color: var(--color-text);
    cursor: pointer;
  }
  .btn-skip-confirm {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-family: var(--font-sans);
    font-weight: var(--font-weight-semibold);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-primary);
    background: var(--color-primary);
    color: var(--color-on-primary);
    cursor: pointer;
  }
</style>
