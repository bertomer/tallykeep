/**
 * NativeBridge — interface for Capacitor-only capabilities (ADR-0007).
 *
 * Browser implementation: stubs that return fixtures or throw, with a
 * visible DEV_GATE notification. Capacitor implementation lands at private-ship.
 *
 * Consumers use the bridge exclusively — never call Capacitor APIs directly.
 * This makes the irreconcilable corner (browser vs Capacitor) visible at
 * compile time: stub calls surface in dev mode banners, not at launch.
 */

export const DEV_MODE = import.meta.env.DEV;

// ---------------------------------------------------------------------------
// Gate notification — emits a Svelte store event so UI can show a banner.
// ---------------------------------------------------------------------------

type GateListener = (capability: string) => void;
const _gateListeners: GateListener[] = [];

export function onDevGate(listener: GateListener): () => void {
  _gateListeners.push(listener);
  return () => {
    const index = _gateListeners.indexOf(listener);
    if (index >= 0) _gateListeners.splice(index, 1);
  };
}

function _notifyGate(capability: string): void {
  for (const listener of _gateListeners) listener(capability);
}

// ---------------------------------------------------------------------------
// PreferenceStorage — non-sensitive key-value store.
// No DevGate: this capability works in browsers (localStorage) so there is
// nothing to warn about. On native it will use @capacitor/preferences.
// Browser-dev: localStorage.
// Capacitor: @capacitor/preferences (swap stub at private-ship).
// ---------------------------------------------------------------------------

const PREF_PREFIX = 'tallykeep_pref_';

export const preferenceStorage = {
  async set(key: string, value: string): Promise<void> {
    if (DEV_MODE) {
      localStorage.setItem(PREF_PREFIX + key, value);
    } else {
      // Replace with: await Preferences.set({ key, value });
      throw new Error('preferenceStorage.set: Capacitor not available');
    }
  },

  async get(key: string): Promise<string | null> {
    if (DEV_MODE) {
      return localStorage.getItem(PREF_PREFIX + key);
    }
    // Replace with: const { value } = await Preferences.get({ key }); return value;
    throw new Error('preferenceStorage.get: Capacitor not available');
  },

  async delete(key: string): Promise<void> {
    if (DEV_MODE) {
      localStorage.removeItem(PREF_PREFIX + key);
    } else {
      // Replace with: await Preferences.remove({ key });
      throw new Error('preferenceStorage.delete: Capacitor not available');
    }
  },
};

// ---------------------------------------------------------------------------
// SecureStorage stub — sensitive data only (device credentials).
// Browser-dev: localStorage with a visible DevGate warning.
// Capacitor: Keychain (iOS) / Keystore (Android).
// ---------------------------------------------------------------------------

const STORAGE_PREFIX = 'tallykeep_dev_';

export const secureStorage = {
  async set(key: string, value: string): Promise<void> {
    if (DEV_MODE) {
      // TODO(browser-pwa-auth-model): localStorage stub — swap for Capacitor Keychain/Keystore at private-ship.
      localStorage.setItem(STORAGE_PREFIX + key, value);
    } else {
      throw new Error('secureStorage.set: Capacitor not available');
    }
  },

  async get(key: string): Promise<string | null> {
    if (DEV_MODE) {
      // TODO(browser-pwa-auth-model): localStorage stub — swap for Capacitor Keychain/Keystore at private-ship.
      return localStorage.getItem(STORAGE_PREFIX + key);
    }
    throw new Error('secureStorage.get: Capacitor not available');
  },

  async delete(key: string): Promise<void> {
    if (DEV_MODE) {
      // TODO(browser-pwa-auth-model): localStorage stub — swap for Capacitor Keychain/Keystore at private-ship.
      localStorage.removeItem(STORAGE_PREFIX + key);
    } else {
      throw new Error('secureStorage.delete: Capacitor not available');
    }
  },
};

// ---------------------------------------------------------------------------
// Biometric stub
// canUseBiometric: override with ?biometric=true query string in browser-dev.
// ---------------------------------------------------------------------------

function _biometricDevOverride(): boolean {
  if (typeof window === 'undefined') return false;
  return new URLSearchParams(window.location.search).get('biometric') === 'true';
}

export const biometric = {
  canUseBiometric(): boolean {
    if (DEV_MODE) return _biometricDevOverride();
    // Capacitor: check Capacitor.isNativePlatform() + bio availability.
    return false;
  },

  async unlock(): Promise<boolean> {
    if (DEV_MODE) {
      _notifyGate('biometric.unlock');
      if (_biometricDevOverride()) {
        // Simulate success in dev mode when override is active.
        return true;
      }
      return false;
    }
    throw new Error('biometric.unlock: Capacitor not available');
  },
};

// ---------------------------------------------------------------------------
// QR scanner stub
// ---------------------------------------------------------------------------

export const qrScanner = {
  /** Returns the decoded QR string, or null if cancelled. */
  async scan(): Promise<string | null> {
    _notifyGate('qrScanner.scan');
    if (DEV_MODE) {
      // In browser-dev we cannot scan; gate is shown and we return null
      // so callers fall back to manual URL entry.
      return null;
    }
    throw new Error('qrScanner.scan: Capacitor not available');
  },
};

// ---------------------------------------------------------------------------
// Clipboard
// Browser-dev: navigator.clipboard.readText() (works natively in secure contexts).
// Capacitor: swap for @capacitor/clipboard at private-ship.
// ---------------------------------------------------------------------------

export const clipboard = {
  /** Read the current clipboard text. Returns null on permission denial or empty. */
  async paste(): Promise<string | null> {
    if (DEV_MODE) {
      try {
        return await navigator.clipboard.readText();
      } catch {
        return null; // permission denied or unavailable in this context
      }
    }
    _notifyGate('clipboard.paste');
    throw new Error('clipboard.paste: Capacitor not available');
  },
};
