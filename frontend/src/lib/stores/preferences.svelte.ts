/**
 * User preferences store.
 *
 * principlesAcknowledged lifecycle:
 *   1. Pre-pairing: stored in preferenceStorage (localStorage in dev,
 *      @capacitor/preferences on native — no DevGate, works everywhere).
 *   2. After pairing: syncToBackend() pushes it to user_profile on the server
 *      and clears the local flag. Server becomes authoritative from that point.
 *   3. Future app opens (already paired): load(serverUrl, authHeaders) reads
 *      from GET /api/v1/profile. Falls back to preferenceStorage on network error.
 *
 * biometricEnabled: session-only for now; will move server-side with device settings.
 */

import { preferenceStorage } from '$lib/native-bridge';

const PREF_KEYS = {
  principlesPending: 'principles_pending',
} as const;

function createPreferences() {
  let principlesAcknowledged = $state(false);
  let biometricEnabled = $state(false);
  let loaded = $state(false);

  /**
   * Load preferences.
   * When serverUrl + authHeaders are supplied (paired device), the backend
   * profile is the authoritative source. Falls back to the local pending flag.
   */
  async function load(serverUrl?: string, authHeaders?: Record<string, string>): Promise<void> {
    if (serverUrl && authHeaders) {
      try {
        const resp = await fetch(`${serverUrl}/api/v1/profile`, { headers: authHeaders });
        if (resp.ok) {
          const profile = await resp.json();
          principlesAcknowledged = profile.principles_acknowledged_at !== null;
          loaded = true;
          return;
        }
      } catch {
        // Network error — fall through to local flag.
      }
    }

    const pending = await preferenceStorage.get(PREF_KEYS.principlesPending);
    principlesAcknowledged = pending === 'true';
    loaded = true;
  }

  /**
   * Record the "I understand" tap. Stored locally via preferenceStorage so it
   * survives page reloads (important on native where the user may background
   * the app mid-onboarding). No backend call — no credential yet.
   */
  async function acknowledgePrinciples(): Promise<void> {
    await preferenceStorage.set(PREF_KEYS.principlesPending, 'true');
    principlesAcknowledged = true;
  }

  /**
   * Push the pending local acknowledgment to the server immediately after
   * pairing, using the freshly issued device credential. Clears the local flag
   * on success so the server becomes the sole source of truth going forward.
   */
  async function syncToBackend(serverUrl: string, authHeaders: Record<string, string>): Promise<void> {
    if (!principlesAcknowledged) return;
    try {
      const resp = await fetch(`${serverUrl}/api/v1/profile`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ principles_acknowledged: true }),
      });
      if (resp.ok) {
        await preferenceStorage.delete(PREF_KEYS.principlesPending);
      }
    } catch {
      // Non-fatal: local flag stays set; next syncToBackend call will retry.
    }
  }

  async function setBiometricEnabled(value: boolean): Promise<void> {
    biometricEnabled = value;
  }

  return {
    get principlesAcknowledged() { return principlesAcknowledged; },
    get biometricEnabled() { return biometricEnabled; },
    get loaded() { return loaded; },
    load,
    acknowledgePrinciples,
    syncToBackend,
    setBiometricEnabled,
  };
}

export const preferences = createPreferences();
