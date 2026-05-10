# UI — Mobile platform spec

This is the mobile platform spec. Cross-platform decisions (Holding
type vocabulary, unit + currency controls, flow inventory, honest
abstraction enforcement) live in `UI/README.md`. This file describes
how those decisions render on mobile, screen by screen, with the
reconcilability gauntlet answers attached.

## Status

The mobile spec is **iteration-driven**. Per ADR-0002 and the
working agreement in `PROCESS.md`, screen-by-screen detail is
authored alongside each iteration's mockups, not pre-specified
upfront. The active iteration's scope lives in `next_iteration.md`.

The original module 11 (`11_ux_flows.md`) carried screen-by-screen
ASCII layouts that predated the current mobile-first thinking and
the UI/README cross-platform decisions. That module retires in
the consolidation merge; its content is not ported here. Mockups
are authored fresh per iteration.

## What lives here

When an iteration produces mobile screen designs, this file gains a
section per flow, in the form:

```
## <Flow name>

### Screens
- `mobile_<flow>_<state>.html` — short description
- ...

### Reconcilability gauntlet answers
1. Trust boundary: ...
2. Keys and secrets: ...
3. Self-hosted vs hosted: ...
4. Confirmation honesty: ...
5. Browser-only fallback: ...
6. Open-source and reproducibility: ...

### Notes
<anything else worth keeping at the platform-spec level>
```

Mockups themselves live in `UI/mockups/` (one HTML file per
screen-state) per the convention in `UI/mockups/README.md`.

## What does NOT live here

- Cross-platform UX decisions — see `UI/README.md`.
- The flow inventory — see `UI/README.md` §"Flow inventory".
- Visual styling specifics — see `UI/mockups/_shared/tokens.css`
  and `UI/mockups/_shared/shell.css`.
- Implementation specifics (SvelteKit components, routing, state
  stores) — those are code, not spec.
- Brand identity, copy voice — placeholder per ADR-0003.

## Migration note for the first Send / Receive iteration

The per-Holding Send and Receive flow detail (Account "Withdraw
to whitelist", Purse external-watch-only redirect to source
wallet, TallyKeep-managed Purse native-sign vs gate, Strongbox
PSBT roundtrip, Vault) currently lives in `UI/README.md` §Send
and §Receive because it predates the iteration-driven
mobile-spec convention. **The first Send/Receive iteration's
scope must include moving that detail into the corresponding
flow sections of this file**, alongside the gauntlet answers,
and stripping it from `UI/README.md` (which then keeps only the
cross-platform flow inventory). This avoids the per-Holding
detail living in two places once mobile.md gains a real
`## Send` and `## Receive` section.

## Iteration roadmap (rough)

The pre-shipping mobile UI iterations target the private-ship event
(per ADR-0003). The roadmap is sketched in `next_iteration.md` and
typically begins with Onboarding + Home (empty + populated states),
followed by Add Holding, Holding detail per type, Send + Receive,
Activity + Categorization, Sweep policy + Trading view, Settings.

When an iteration ships, its corresponding section appears below.
