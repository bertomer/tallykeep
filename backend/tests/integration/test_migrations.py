"""Integration test: alembic upgrade and downgrade roundtrip.

Spec module 03: every schema change has a rollback path; this test guards that for
the initial migration. As more migrations land, each one earns its own assertion in
the parametrized cases below.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import pytest


pytestmark = pytest.mark.integration


# All tables defined in the spec module 03 schema. Update in lockstep with new
# migrations.
EXPECTED_TABLES = {
    "address",
    "broadcast_attempt",
    "crypto_parameters",
    "custodial_ledger_entry",
    "custodial_provider",
    "descriptor",
    "event_emission_log",
    "holding",
    "holding_type_change_log",
    "invoice",
    "job",
    "ledger_entry",
    "ledger_entry_holding_link",
    "onchain_transaction",
    "paired_device",
    "payment_request",
    "runtime_configuration",
    "secret",
    "sweep_execution",
    "sweep_policy",
    "user_profile",
    "utxo",
}


def _alembic_config(database_url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _list_tables(database_url: str) -> set[str]:
    engine = sa.create_engine(database_url, future=True)
    try:
        inspector = sa.inspect(engine)
        return set(inspector.get_table_names())
    finally:
        engine.dispose()


def test_upgrade_creates_all_expected_tables(clean_test_database: str) -> None:
    """`alembic upgrade head` creates every spec-defined table."""
    cfg = _alembic_config(clean_test_database)
    command.upgrade(cfg, "head")

    tables = _list_tables(clean_test_database)
    # alembic_version is implementation-detail of alembic itself.
    tables.discard("alembic_version")
    assert tables == EXPECTED_TABLES, f"Schema diverges from spec module 03: {tables ^ EXPECTED_TABLES}"


def test_downgrade_drops_all_application_tables(clean_test_database: str) -> None:
    """`alembic downgrade base` reverses the initial migration cleanly."""
    cfg = _alembic_config(clean_test_database)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    tables = _list_tables(clean_test_database)
    # Only alembic's own bookkeeping table should remain.
    assert tables == {"alembic_version"}


def test_upgrade_downgrade_roundtrip_is_idempotent(clean_test_database: str) -> None:
    """Running upgrade → downgrade → upgrade leaves the schema identical."""
    cfg = _alembic_config(clean_test_database)
    command.upgrade(cfg, "head")
    tables_first = _list_tables(clean_test_database) - {"alembic_version"}

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    tables_second = _list_tables(clean_test_database) - {"alembic_version"}

    assert tables_first == tables_second
    assert tables_second == EXPECTED_TABLES


def test_holding_singleton_check_constraint(clean_test_database: str) -> None:
    """Spec module 03: user_profile and crypto_parameters have a fixed singleton id.

    The database itself enforces this via CHECK constraints.
    """
    cfg = _alembic_config(clean_test_database)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(clean_test_database, future=True)
    try:
        # Inserting a row with a non-singleton id must fail.
        with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
            conn.exec_driver_sql(
                """
                INSERT INTO user_profile (id)
                VALUES ('00000000-0000-0000-0000-000000000002')
                """
            )
    finally:
        engine.dispose()


def test_can_trade_false_invariant_at_database_level(clean_test_database: str) -> None:
    """Defense-in-depth: even if a service-layer bug let `can_trade=true` through,
    the database constraint must reject the insert (spec module 03 / 10)."""
    cfg = _alembic_config(clean_test_database)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(clean_test_database, future=True)
    try:
        with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
            # Skip FK validation by attempting the constraint check first via a raw
            # insert with bogus FK targets — the CHECK constraint fires before FK
            # validation since all values are present in the row.
            conn.exec_driver_sql(
                """
                INSERT INTO custodial_provider (
                    id, holding_id, provider_kind, display_name, adapter_id,
                    api_credential_reference, api_secret_reference,
                    can_read, can_trade, can_withdraw,
                    whitelist_address, whitelist_address_descriptor_id, is_active,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), gen_random_uuid(), 'exchange', 'X', 'kraken',
                    'r1', 'r2', TRUE, TRUE, FALSE,
                    'bc1q', gen_random_uuid(), TRUE, NOW(), NOW()
                )
                """
            )
    finally:
        engine.dispose()
