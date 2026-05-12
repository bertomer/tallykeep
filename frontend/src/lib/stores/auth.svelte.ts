/**
 * Auth store — device credential and session state.
 *
 * deviceCredential: the long-lived credential issued at pairing, stored in
 *   secureStorage. Sent as `Authorization: Bearer <credential>` on all API calls.
 * unlocked: true when the user has successfully unlocked the app this session
 *   (biometric or passphrase validated).
 */

import { secureStorage } from '$lib/native-bridge';

const CREDENTIAL_KEY = 'device_credential';
const DEVICE_ID_KEY = 'device_id';

function createAuthStore() {
  let deviceCredential = $state<string | null>(null);
  let deviceId = $state<string | null>(null);
  let unlocked = $state(false);
  let loaded = $state(false);

  async function load(): Promise<void> {
    const [cred, did] = await Promise.all([
      secureStorage.get(CREDENTIAL_KEY),
      secureStorage.get(DEVICE_ID_KEY),
    ]);
    deviceCredential = cred;
    deviceId = did;
    loaded = true;
  }

  async function storePairingResult(credential: string, id: string): Promise<void> {
    await Promise.all([
      secureStorage.set(CREDENTIAL_KEY, credential),
      secureStorage.set(DEVICE_ID_KEY, id),
    ]);
    deviceCredential = credential;
    deviceId = id;
  }

  function markUnlocked(): void {
    unlocked = true;
  }

  async function clearCredential(): Promise<void> {
    await Promise.all([
      secureStorage.delete(CREDENTIAL_KEY),
      secureStorage.delete(DEVICE_ID_KEY),
    ]);
    deviceCredential = null;
    deviceId = null;
    unlocked = false;
  }

  return {
    get deviceCredential() { return deviceCredential; },
    get deviceId() { return deviceId; },
    get unlocked() { return unlocked; },
    get loaded() { return loaded; },
    get isPaired() { return deviceCredential !== null; },
    load,
    storePairingResult,
    markUnlocked,
    clearCredential,
  };
}

export const auth = createAuthStore();

/** Convenience: return headers for authenticated API calls. */
export function authHeaders(): Record<string, string> {
  const cred = auth.deviceCredential;
  if (!cred) return {};
  return { Authorization: `Bearer ${cred}` };
}
