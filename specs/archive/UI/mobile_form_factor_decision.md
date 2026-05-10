# TallyKeep — Mobile form factor decision

**Date**: 2026-05
**Status**: Decided. Amends `design_decisions.md` §10 and §12, and spec modules 01 and 12.
**Supersedes**: the prior reading of §10 that framed mobile as a read-mostly companion.

---

## TL;DR

- **Mobile is a real product**, not a companion. Same priority as desktop.
- **One SvelteKit codebase**, two distribution paths: PWA for desktop/web, **Capacitor wrapper for mobile app stores** (and sideload).
- **PWA never holds Bitcoin signing material.** Ever. Not on desktop, not on mobile-in-browser.
- **The Capacitor mobile app is the only surface that holds spending keys.** Stored in iOS Keychain / Android Keystore via native plugins, biometric-gated.
- Capacitor moves from v3 to **v1** in the roadmap. The PWA-only mobile path is downgraded to "watch-and-PSBT-out", same posture as desktop.

---

## What forced this

The spec previously assumed mobile would either be a thin companion to desktop (§10 as written) or a Capacitor wrapper in v3 (roadmap module 12). Neither survived contact with the hosted-tier target market.

For an Argentine or West African user with no home machine, the desktop *does not exist* in their life. Their phone is the entire surface. If TallyKeep is genuinely "banking ergonomics on Bitcoin" for that user, mobile has to support:

- Adding Holdings (at minimum Account and Purse from the phone)
- Receiving and spending from a Purse with keys held on the phone
- Lightning send/receive with keys held on the phone (v1.5)
- Categorising activity, viewing balances, configuring sweeps
- Doing all of this without trusting a server with their seed

Pure-PWA cannot meet the last bullet. Storage in Web platform APIs has no equivalent of iOS Keychain or Android Keystore — there is no hardware-backed, biometric-gated, OS-mediated secret store accessible from a browser. The closest substitute is encrypting a seed with a Web Crypto AES key marked `extractable: false` and storing the ciphertext in IndexedDB. iOS Safari evicts script-writable storage after periods of inactivity ([WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/)); installed PWAs since iOS 17 can request `navigator.storage.persist()` but the OS still reserves the right to evict under storage pressure. Mutiny Wallet, the most prominent Bitcoin PWA precedent, explicitly warned its users that browser storage clearing meant "you will not be able to access your funds without [your seed phrase]" ([Mutiny FAQ](https://blog.mutinywallet.com/mutiny-wallet-faq/)) and shipped native iOS/Android before shutting down.

WebAuthn / passkeys are real on PWA (iOS 17+, Android), and they're hardware-backed via Secure Enclave / TEE. But WebAuthn signs assertions on the **secp256r1 (P-256)** curve. Bitcoin uses **secp256k1**. They are different curves; a passkey cannot directly sign a Bitcoin transaction ([passkeys.dev iOS reference](https://passkeys.dev/docs/reference/ios/)). The only PWA pattern available is "WebAuthn-gated AES key wraps secp256k1 seed in IndexedDB" — which means the seed transits the JavaScript heap to sign, exposing it to any browser-RCE or malicious-dependency attack during the signing window.

Capacitor with `@aparajita/capacitor-secure-storage` (or equivalent) holds the seed in Android Keystore (TEE-backed, StrongBox on Pixel) or iOS Keychain (Secure Enclave), AES-256-GCM at rest, biometric-unlocked. A native module can perform the secp256k1 signing without the seed leaving native code if needed. That's a different threat model — and the right one for spending keys.

## What this changes

### 1. Form factor

| | Old (§10 / module 12) | New |
|---|---|---|
| Desktop | PWA from self-hosted backend | PWA from self-hosted backend or hosted instance — unchanged |
| Mobile | Companion, read-mostly, spend Purse + LN only | Real product. Capacitor app for spending. PWA-in-browser as a watch-only fallback. |
| Capacitor | v3 | v1 (mobile launches with Capacitor) |
| Mobile feature scope | Restrictive | Near-parity with desktop. Defers only flows that are physically desktop-shaped. |

### 2. Key storage policy (locked)

- **PWA: no Bitcoin signing material, ever, on any platform.** Desktop PWA signs via PSBT to hardware wallet. Mobile PWA-in-browser signs via PSBT to a separately-installed wallet app or to the desktop.
- **Capacitor app on mobile: spending keys (Purse seed, Lightning) live in Keychain/Keystore.** AES-256-GCM at rest, biometric-gated unlock, never written to disk in plaintext.
- **Strongbox / Vault keys: hardware wallet only, no change.** Mobile defers Strongbox sends to desktop in v1; v1.x will add PSBT-QR roundtrip for hardware wallets that support it (Coldcard, Jade).
- **Connection tokens (paired-device bearer tokens, hosted-tier session): in Keychain/Keystore on Capacitor; in IndexedDB encrypted with a non-extractable Web Crypto key on PWA.** Recovery is "revoke and re-pair", so eviction is annoying but not catastrophic for connection material.

### 3. Codebase

One SvelteKit project. Two build outputs:

| Build | Adapter | Distribution |
|---|---|---|
| Desktop / web PWA | `adapter-static` served by FastAPI, or `adapter-node` | localhost (self-host), tallykeep.app (hosted tier) |
| Mobile native | `adapter-static` wrapped in Capacitor | App Store, Play Store, APK sideload, F-Droid |

Conditional behaviour at runtime:

```ts
import { Capacitor } from '@capacitor/core';
import { SecureStorage } from '@aparajita/capacitor-secure-storage';

async function storeSpendingKey(seed: string) {
  if (!Capacitor.isNativePlatform()) {
    throw new SpendingNotSupportedError(
      'This build cannot hold spending keys. Install the TallyKeep app or sign on desktop.'
    );
  }
  await SecureStorage.set('purse:default:seed', seed, { biometric: true });
}
```

Layout adaptation uses a viewport-width store (mobile <= 768px → bottom nav, desktop > 768px → sidebar). The same `+page.svelte` files render correctly at both widths; layout components branch on viewport.

### 4. Distribution

Three tiers, in decreasing centralisation:

1. **App Store / Play Store** — primary distribution for the LatAm/Africa target market. Apple developer fee ~$99/yr, Google Play one-time $25.
2. **Sideload paths** — APK direct download from tallykeep.app, F-Droid for Android, AltStore / TestFlight for iOS sovereignty users.
3. **PWA fallback** — tallykeep.app served as PWA, installable to home screen. Watch-only; no spending keys held. The "I want to inspect the source before I trust it" tier.

**Reproducible builds** target from v1.x onward. Phoenix, Aqua, BlueWallet all do this; it's the recognised sovereignty-credible distribution standard for non-custodial wallets.

### 5. Mobile feature scope (revised §10)

| Feature | Mobile (Capacitor v1) | Mobile PWA (browser) | Desktop |
|---|---|---|---|
| View all Holdings | ✅ | ✅ | ✅ |
| Add Account (custodial) | ✅ | ✅ | ✅ |
| Add Purse (xpub paste / QR scan) | ✅ | ✅ | ✅ |
| Add Strongbox (HW wallet descriptor) | 🟡 v1.x | ❌ | ✅ |
| Add Vault (multisig) | ❌ defer | ❌ | ✅ |
| Send from Purse with on-device keys | ✅ | ❌ | ✅ (via paired phone) |
| Send from Purse via PSBT to other wallet | ✅ | ✅ | ✅ |
| Send from Strongbox | 🟡 v1.x QR-PSBT | ❌ | ✅ HW wallet |
| Send from Vault | ❌ defer | ❌ | ✅ |
| Receive (any holding) | ✅ | ✅ | ✅ |
| Lightning send/receive | ✅ v1.5 | ❌ | ✅ via own LN node |
| Categorisation | ✅ | ✅ | ✅ |
| Sweep policy creation | ✅ | ✅ | ✅ |
| Blueprint analysis (basic flags) | ✅ | ✅ | ✅ |
| Blueprint UTXO graph | ❌ v2 desktop | ❌ v2 desktop | 🟡 v2 |
| Multisig coordination ceremony | ❌ defer | ❌ defer | 🟡 v2 |
| Descriptor surgery (advanced edits) | ❌ defer | ❌ defer | ✅ advanced toggle |

### 6. v1 reality status table — amendment to design_decisions.md §13

The following rows in the existing table change:

| Screen / feature | Old status | New status |
|---|---|---|
| Mobile companion app | ⏳ v1.5+ | ✅ v1 (Capacitor) |
| Capacitor native wrapper | ⏳ v3 | ✅ v1 |
| Lightning send/receive | ⏳ v1.5 | ⏳ v1.5 — **on Capacitor only** |
| Lightning on PWA | (implicit) | ❌ never. Architectural. |

---

## Implementation notes

### Capacitor plugins required for v1

- **`@aparajita/capacitor-secure-storage`** or **`@capacitor-community/secure-storage`** — Keychain/Keystore wrapper. Pick after evaluating maintenance status.
- **`@capacitor/biometric`** or **`capacitor-native-biometric`** — Face ID / Touch ID / fingerprint prompts.
- **`@capacitor/camera`** — QR scanning for receive/pair flows.
- **`@capacitor/push-notifications`** — incoming payment, sweep executed, security discrepancy alerts (v1.5+).
- **`@capacitor/share`** — share QR / address.
- **`@capacitor/clipboard`** — paste address.
- **Native secp256k1 signing module** — write a small Swift + Kotlin plugin that takes a PSBT and signs with the seed retrieved from secure storage, never exposing the seed to JS. Defer to v1.5 if needed; v1 can sign in JS using `@noble/secp256k1` after retrieving from secure storage, accepting the slightly weaker model.

### Build pipeline

```bash
# Desktop PWA dev
npm run dev                          # SvelteKit dev server

# Desktop PWA build
npm run build                        # adapter-static or adapter-node

# Mobile dev (browser, viewport emulated)
npm run dev                          # then DevTools → device mode

# Mobile dev (real plugins, simulator/device)
npx cap sync                         # copy build to native projects
npx cap run ios --livereload         # or --external for physical device
npx cap run android --livereload

# Mobile release build
npm run build && npx cap sync
# Open ios/App/App.xcworkspace in Xcode, archive, submit
# Open android/ in Android Studio, generate signed APK/AAB
```

### Layout breakpoint

Single source of truth, `lib/stores/viewport.ts`:

```ts
import { readable } from 'svelte/store';
export const isMobile = readable(false, set => {
  if (typeof window === 'undefined') return;
  const mq = window.matchMedia('(max-width: 768px)');
  set(mq.matches);
  const listener = (e: MediaQueryListEvent) => set(e.matches);
  mq.addEventListener('change', listener);
  return () => mq.removeEventListener('change', listener);
});
```

Layout components (`+layout.svelte` at root, plus per-section overrides) branch on this:

```svelte
{#if $isMobile}
  <MobileShell>
    <slot />
    <BottomNav />
  </MobileShell>
{:else}
  <DesktopShell>
    <Sidebar />
    <slot />
  </DesktopShell>
{/if}
```

Page-level Svelte components (`+page.svelte`) are largely viewport-agnostic. The shell handles navigation.

---

## Open questions still pending

1. **Native secp256k1 plugin in v1 vs v1.5.** Strict reading of the security goal says "never expose seed to JS"; pragmatic v1 says "decrypt from secure storage, sign in JS, zero out". Decide before code.

2. **Reproducible build target date.** v1.x or v1.5? Phoenix and Aqua publish reproducible builds — for credibility in sovereignty markets, this matters. Cost: nontrivial CI pipeline work.

3. **F-Droid inclusion criteria.** F-Droid requires Free Software licensing for both the app and all dependencies. Check Capacitor's licence chain (MIT, mostly fine), and any Lightning SDK we adopt (Breez SDK has its own licence terms, may need verifying).

4. **iOS PWA fallback usability.** If a user comes to tallykeep.app on iOS Safari, they get a watch-only experience. Is the friction "now install the app for spending" acceptable, or do we need a PSBT-QR signing flow in PWA-in-browser too?

5. **Hosted-tier login UX in Capacitor.** If user is on Capacitor app and signs into hosted tier, do they sign in with email + passphrase, or an OAuth-style flow, or LNURL-auth? Defer to hosted-tier design pass.

---

## Files affected by this amendment

- `design_decisions.md` §10 — rewrite to reflect mobile-as-real-product
- `design_decisions.md` §12 — clarify Lightning is Capacitor-only on mobile, never PWA
- `design_decisions.md` §13 — update reality status table per §6 above
- `01_architecture.md` — add Capacitor build target alongside the existing PWA build
- `12_roadmap.md` — move Capacitor wrapper from v3 to v1; restructure mobile track
- `10_threat_model.md` — add the "spending key in mobile Keychain/Keystore" asset row, and the threat model for browser RCE + PWA-only seed storage being explicitly out of scope (PWA holds no spending keys)
