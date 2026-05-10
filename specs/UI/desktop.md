# UI — Desktop platform spec

This is the desktop platform spec. Cross-platform decisions live in
`UI/README.md`.

## Status

**Desktop work is deferred.** Per `UI/README.md` §"Mobile and
desktop":

> Mobile is being built first. The Capacitor build is the only
> surface that holds spending keys; browser PWA on either platform
> never holds signing material. Codebase architecture for desktop is
> TBD — the call between one project with route-group divergence vs.
> two projects sharing an npm-package'd library is deferred until
> desktop work begins and we have actual mobile UX to compare
> against.

The desktop surface is an operations console — setup, configuration,
deep transaction history, accounting export, hardware-wallet PSBT
roundtrips. Real-world banking-app comparisons (CIC's mobile vs.
web) suggest mobile and desktop information architecture often
differ substantially even with shared brand and data.

## When this file gets filled in

This file fills in when:

1. The mobile UI is stable enough that we have something to compare
   against.
2. Rémy decides to start desktop work (likely post-private-ship,
   possibly post-public-ship — TBD per ADR-0003).
3. The codebase architecture call is made (single project with
   route-group divergence vs. shared library).

Until then, this file exists as a placeholder so canonical references
to `UI/desktop.md` resolve, and so anyone reading the spec tree
knows desktop is deliberate-not-forgotten.
