# Custom adapter for non-ccxt venues (Swissquote and similar)

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Proves the adapter abstraction works for non-ccxt
  venues. Swissquote in particular matters for Swiss / EU users
  with traditional broker accounts that hold Bitcoin positions.
- **Sketch:** Implement the same `CustodialProvider` interface
  ccxt adapters use, but against Swissquote's REST API directly.
- **Touches:** treasury layer adapter abstraction
- **Status:** idea
- **Milestone:** post-shipping.
