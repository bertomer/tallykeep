<!--
  Unlock — daily lock screen.
  State: loading → biometric (auto-fires) | passphrase
  Biometric default: fires immediately on mount; "Use passphrase instead" escapes.
  Passphrase: POST /api/v1/auth/passphrase-validate, rate-limit aware.
  Matches: specs/UI/mockups/mobile_unlock_biometric.html + mobile_unlock_passphrase.html (validated 2026-05-10)
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth, authHeaders } from '$lib/stores/auth.svelte';
  import { preferences } from '$lib/stores/preferences.svelte';
  import { biometric, secureStorage } from '$lib/native-bridge';
  import WordmarkIcony from '$lib/components/WordmarkIcony.svelte';
  import DevGate from '$lib/components/DevGate.svelte';
  import Icon from '$lib/components/Icon.svelte';

  type UnlockState = 'loading' | 'biometric' | 'passphrase';

  let unlockState = $state<UnlockState>('loading');
  let passphrase = $state('');
  let errorMessage = $state('');
  let loading = $state(false);
  let serverLabel = $state('');
  let serverUrl = $state('');
  let canBio = $state(false);

  onMount(async () => {
    await Promise.all([
      auth.loaded ? Promise.resolve() : auth.load(),
      preferences.loaded ? Promise.resolve() : preferences.load(),
    ]);

    serverUrl = (await secureStorage.get('server_url')) ?? '';

    try {
      const resp = await fetch(`${serverUrl}/api/v1/server/info`);
      if (resp.ok) {
        const data = await resp.json();
        serverLabel = data.server_label ?? '';
      }
    } catch { /* label stays empty */ }

    canBio = await biometric.canUseBiometric();

    if (preferences.biometricEnabled && canBio) {
      unlockState = 'biometric';
      attemptBiometric();
    } else {
      unlockState = 'passphrase';
    }
  });

  async function attemptBiometric() {
    const ok = await biometric.unlock();
    if (ok) {
      auth.markUnlocked();
      goto('/home');
    } else {
      unlockState = 'passphrase';
    }
  }

  async function handlePassphraseUnlock() {
    if (!passphrase || loading) return;
    errorMessage = '';
    loading = true;
    try {
      const base = serverUrl;
      const resp = await fetch(`${base}/api/v1/auth/passphrase-validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ passphrase }),
      });
      if (resp.ok) {
        auth.markUnlocked();
        goto('/home');
        return;
      }
      if (resp.status === 429) {
        const retryAfter = resp.headers.get('Retry-After');
        errorMessage = retryAfter
          ? `Too many attempts. Try again in ${retryAfter}s.`
          : 'Too many attempts. Please wait before trying again.';
        return;
      }
      errorMessage = 'Incorrect passphrase. Try again.';
    } catch {
      errorMessage = 'Could not reach your TallyKeep. Check your connection.';
    } finally {
      loading = false;
    }
  }
</script>

<DevGate />

<div class="phone-screen safe-top safe-bottom">

  <div class="brand-strip">
    <WordmarkIcony width={280} />
  </div>

  {#if unlockState === 'biometric'}
    <div class="unlock-body biometric">
      <div class="bio-glyph" aria-hidden="true">
        <Icon name="biometric" size={56} />
      </div>
      <div class="heading">Unlock TallyKeep</div>
      <div class="hint">
        Use your biometric to open the app. Look at your phone or
        place your finger on the sensor.
      </div>
      <button
        class="alt-action"
        onclick={() => { unlockState = 'passphrase'; }}
      >
        Use passphrase instead
      </button>
    </div>

  {:else if unlockState === 'passphrase'}
    <div class="unlock-body passphrase">
      <div class="heading">Enter your passphrase</div>
      <div class="hint">
        Type your TallyKeep passphrase — the same one you set for
        your server. Sent over the secure connection for verification.
      </div>

      <input
        type="password"
        class="passphrase-input"
        placeholder="••••••••••••"
        aria-label="TallyKeep passphrase"
        autocomplete="current-password"
        bind:value={passphrase}
        onkeydown={(e) => { if (e.key === 'Enter') handlePassphraseUnlock(); }}
      />

      {#if errorMessage}
        <p class="error-text">{errorMessage}</p>
      {/if}

      <div class="unlock-actions">
        <button
          class="btn-unlock"
          disabled={loading || !passphrase}
          onclick={handlePassphraseUnlock}
        >
          {loading ? 'Checking…' : 'Unlock'}
        </button>
        {#if canBio && preferences.biometricEnabled}
          <button
            class="alt-action"
            onclick={() => { unlockState = 'biometric'; attemptBiometric(); }}
          >
            Use biometric instead
          </button>
        {/if}
      </div>
    </div>
  {/if}

  <div class="connection-status">
    <span class="status-dot" aria-hidden="true"></span>
    {serverLabel ? `Connected · ${serverLabel}` : 'Connected'}
  </div>

</div>

<style>
  .brand-strip {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-5) var(--space-4) var(--space-4);
  }

  /* ── Biometric variant ── */
  .unlock-body.biometric {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-5) var(--space-4);
    text-align: center;
    gap: var(--space-3);
  }
  .bio-glyph {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: var(--color-primary-soft);
    border: 2px solid var(--color-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-primary-strong);
    flex-shrink: 0;
  }

  /* ── Passphrase variant ── */
  .unlock-body.passphrase {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: center;
    padding: var(--space-3) var(--space-4);
    gap: var(--space-3);
  }

  /* ── Shared body elements ── */
  .heading {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    text-align: center;
    margin-bottom: var(--space-2);
  }
  .hint {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height-default);
    text-align: center;
    max-width: 280px;
    align-self: center;
    margin-bottom: var(--space-4);
  }
  .alt-action {
    background: transparent;
    border: none;
    color: var(--color-primary-strong);
    font-size: var(--font-size-sm);
    font-family: var(--font-sans);
    font-weight: var(--font-weight-medium);
    padding: var(--space-2) var(--space-4);
    cursor: pointer;
    text-decoration: underline;
    text-underline-offset: 3px;
    align-self: center;
    margin-top: var(--space-5);
  }

  /* ── Passphrase input ── */
  .passphrase-input {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-family: var(--font-mono);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text);
    letter-spacing: 4px;
    outline: none;
  }
  .passphrase-input:focus {
    border-color: var(--color-border-focus);
  }
  .error-text {
    color: var(--color-danger);
    font-size: var(--font-size-xs);
    margin: 0;
    text-align: center;
  }
  .unlock-actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin-top: var(--space-3);
  }
  .btn-unlock {
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
  .btn-unlock:disabled { opacity: 0.5; cursor: not-allowed; }

  /* ── Connection status ── */
  .connection-status {
    flex-shrink: 0;
    padding: 0 var(--space-4) var(--space-4);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-success);
    flex-shrink: 0;
  }
</style>
