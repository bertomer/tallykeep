"""Integration test for EncryptedDatabaseSecretStore.

Exercises the same lifecycle as the in-memory unit test but persists through real
Postgres tables, including a simulated container restart (drop the in-memory key,
reload via a new store instance, decrypt).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

import pytest

from tallykeep.infrastructure.secrets import (
    AlreadyInitializedError,
    EncryptedDatabaseSecretStore,
    NotInitializedError,
    WrongPassphraseError,
)


pytestmark = pytest.mark.integration


# Apply cheap KDF parameters at module load so initialize() is fast in CI.
@pytest.fixture(autouse=True)
def _cheap_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr("tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1)
    monkeypatch.setattr("tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1)


@pytest.fixture()
def migrated_session_factory(clean_test_database: str):  # type: ignore[no-untyped-def]
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", clean_test_database)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(clean_test_database, future=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_initialize_persists_crypto_parameters(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    store = EncryptedDatabaseSecretStore(migrated_session_factory)
    assert not store.is_initialized()

    store.initialize("the passphrase")

    # Re-checking via a fresh store instance proves the parameters live in the DB.
    fresh = EncryptedDatabaseSecretStore(migrated_session_factory)
    assert fresh.is_initialized()
    assert not fresh.is_unlocked()  # fresh instance has no in-memory key


def test_secret_decryptable_across_store_instances(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    """Simulates: container starts → user unlocks → stores a secret → container
    restarts → user unlocks again → reads the same secret."""
    first = EncryptedDatabaseSecretStore(migrated_session_factory)
    first.initialize("strong passphrase")
    first.set_secret("kraken:api_key", b"my-real-api-key")

    # Simulate restart.
    first.lock()

    second = EncryptedDatabaseSecretStore(migrated_session_factory)
    second.unlock("strong passphrase")
    assert second.get_secret("kraken:api_key") == b"my-real-api-key"


def test_wrong_passphrase_after_restart_rejected(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    first = EncryptedDatabaseSecretStore(migrated_session_factory)
    first.initialize("right one")

    second = EncryptedDatabaseSecretStore(migrated_session_factory)
    with pytest.raises(WrongPassphraseError):
        second.unlock("wrong one")


def test_initialize_twice_rejected_across_instances(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    first = EncryptedDatabaseSecretStore(migrated_session_factory)
    first.initialize("p")

    second = EncryptedDatabaseSecretStore(migrated_session_factory)
    with pytest.raises(AlreadyInitializedError):
        second.initialize("p")


def test_unlock_before_initialize_rejected(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    store = EncryptedDatabaseSecretStore(migrated_session_factory)
    with pytest.raises(NotInitializedError):
        store.unlock("anything")


def test_overwrite_secret_persists(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    store = EncryptedDatabaseSecretStore(migrated_session_factory)
    store.initialize("p")
    store.set_secret("ref", b"first")
    store.set_secret("ref", b"second")
    assert store.get_secret("ref") == b"second"


def test_delete_persists(migrated_session_factory) -> None:  # type: ignore[no-untyped-def]
    store = EncryptedDatabaseSecretStore(migrated_session_factory)
    store.initialize("p")
    store.set_secret("ref", b"value")
    store.delete_secret("ref")

    fresh = EncryptedDatabaseSecretStore(migrated_session_factory)
    fresh.unlock("p")
    with pytest.raises(KeyError):
        fresh.get_secret("ref")
