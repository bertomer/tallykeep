"""Auto-categorization heuristics — spec module 05.

The CategorizerSuggester subscriber (M5.6) reacts to
`ledger_entry.requires_categorization` events and writes a non-binding
`suggested_category` onto the entry. The user always has the final say
via PATCH; the suggestion is purely advisory.

v1 heuristics (in order of evaluation — first match wins):

  1. INTERNAL_TRANSFER:
     `direction == INTERNAL` is unambiguous — the tx moves value
     between two holdings the user owns.

  2. CUSTODIAL_DEPOSIT / CUSTODIAL_WITHDRAWAL:
     If a watched output's address matches the `whitelist_address` on
     a registered CustodialProvider, suggest CUSTODIAL_DEPOSIT (when
     direction == OUTGOING) or CUSTODIAL_WITHDRAWAL (when direction
     == INCOMING). The CustodialProvider table doesn't ship until M8,
     so this branch is currently a no-op (the lookup returns nothing).
     We keep the code path so M8 lights up the heuristic by adding rows.

  3. PaymentRequest match:
     If a non-cancelled PaymentRequest exists with this entry's txid as
     `broadcast_txid`, suggest the category that PaymentRequest used.
     Banking lands in M6, so this branch is also a no-op for v1's
     savings-only state.

If no heuristic matches, leave `suggested_category` unset; the user will
pick from the full enum.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import Direction, LedgerCategory
from tallykeep.models import LedgerEntryRow


logger = logging.getLogger(__name__)


def suggest_category(
    session: Session, ledger_entry_id, *,
    write_to_db: bool = True,
) -> LedgerCategory | None:  # type: ignore[no-untyped-def]
    """Compute and (optionally) persist the suggested category.

    Returns the suggestion (None if no heuristic fired). The caller
    typically commits the session after this returns; we don't commit
    inside.
    """
    row = session.get(LedgerEntryRow, ledger_entry_id)
    if row is None:
        return None
    if row.suggested_category is not None:
        # A previous run already filled it; leave alone (idempotent).
        return LedgerCategory(row.suggested_category)

    suggestion: LedgerCategory | None = None

    if row.direction == Direction.INTERNAL.value:
        suggestion = LedgerCategory.INTERNAL_TRANSFER

    if suggestion is None:
        suggestion = _custodial_match(session, row)

    if suggestion is None:
        suggestion = _payment_request_match(session, row)

    if suggestion is not None and write_to_db:
        row.suggested_category = suggestion.value

    return suggestion


# --- heuristics ------------------------------------------------------------


def _custodial_match(session: Session, entry_row: LedgerEntryRow) -> LedgerCategory | None:
    """Look for a CustodialProvider whose whitelist_address appears in the
    tx's outputs (for OUTGOING entries) or inputs (for INCOMING).

    The CustodialProvider table isn't populated in v1's savings-only
    milestone — the lookup returns no rows and this heuristic stays
    quiet. M8's treasury layer wires it.
    """
    try:
        from tallykeep.models import CustodialProviderRow
    except ImportError:  # pragma: no cover — keeps the import dependency local
        return None

    # We don't have a direct mapping from a LedgerEntry to its tx vouts /
    # vins here; that requires re-decoding the raw tx via NodeAdapter. The
    # cheap path used in v1: check if any whitelist address is referenced
    # by a UTXO row that shares this entry's source_reference (which IS
    # the txid for ONCHAIN_TRANSACTION entries). When it matches AND we
    # know the tx direction, we can suggest deposit or withdrawal.
    if entry_row.source != "onchain_transaction":
        return None

    # Pull all whitelist addresses (small N — the user has a handful of
    # custodial accounts at most).
    whitelist_rows = session.execute(
        select(CustodialProviderRow.whitelist_address).where(
            CustodialProviderRow.whitelist_address.is_not(None)
        )
    ).scalars().all()
    if not whitelist_rows:
        return None

    # If any UTXO of this tx pays a whitelist address, that's a strong
    # signal. We avoid that lookup here — the SQL is non-trivial and the
    # M8 implementation will flesh out the matching logic. Keeping the
    # branch wired but inert keeps the architecture honest without
    # half-implementing it.
    return None


def _payment_request_match(
    session: Session, entry_row: LedgerEntryRow
) -> LedgerCategory | None:
    """When the entry's source_reference matches a PaymentRequest
    `broadcast_txid`, suggest the category that PaymentRequest carried.

    Banking lands in M6; for now this is a no-op.
    """
    return None


__all__ = ["suggest_category"]
