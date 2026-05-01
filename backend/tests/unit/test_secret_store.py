"""SecretStore unit tests using the in-memory backend.

Exercises the lifecycle (initialize / unlock / lock), CRUD, and the canary-based
passphrase verification. The same lifecycle is exercised against Postgres in the
integration suite.
"""

from __future__ import annotations

import pytest

from tallykeep.infrastructure.secrets import (
    AlreadyInitializedError,
    CANARY_REFERENCE,
    InMemorySecretStore,
    LockedError,
    NotInitializedError,
    WrongPassphraseError,
)


pytestmark = pytest.mark.unit


# Use cheap Argon2id parameters for tests by patching the defaults via wrapping the
# whole flow with a parameter-injected backend. To keep this simple and fast we
# override at module level.
@pytest.fixture(autouse=True)
def _cheap_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make Argon2id finish in ~1ms so the lifecycle tests stay fast."""
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr("tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1)
    monkeypatch.setattr("tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1)


# --- Lifecycle --------------------------------------------------------------------


class TestLifecycle:
    def test_fresh_store_is_not_initialized(self) -> None:
        store = InMemorySecretStore()
        assert not store.is_initialized()
        assert not store.is_unlocked()

    def test_initialize_marks_store_initialized_and_unlocked(self) -> None:
        store = InMemorySecretStore()
        store.initialize("strong passphrase")
        assert store.is_initialized()
        assert store.is_unlocked()

    def test_initialize_twice_rejected(self) -> None:
        store = InMemorySecretStore()
        store.initialize("p")
        with pytest.raises(AlreadyInitializedError):
            store.initialize("p")

    def test_unlock_before_initialize_rejected(self) -> None:
        store = InMemorySecretStore()
        with pytest.raises(NotInitializedError):
            store.unlock("p")

    def test_lock_clears_in_memory_key(self) -> None:
        store = InMemorySecretStore()
        store.initialize("p")
        store.lock()
        assert not store.is_unlocked()
        assert store.is_initialized()  # parameters persist

    def test_unlock_with_wrong_passphrase_rejected(self) -> None:
        store = InMemorySecretStore()
        store.initialize("right passphrase")
        store.lock()
        with pytest.raises(WrongPassphraseError):
            store.unlock("wrong passphrase")
        assert not store.is_unlocked()

    def test_unlock_with_right_passphrase_succeeds_after_lock(self) -> None:
        store = InMemorySecretStore()
        store.initialize("right passphrase")
        store.lock()
        store.unlock("right passphrase")
        assert store.is_unlocked()


# --- Secret CRUD ------------------------------------------------------------------


class TestSecretCrud:
    def _initialized(self) -> InMemorySecretStore:
        store = InMemorySecretStore()
        store.initialize("test passphrase")
        return store

    def test_set_and_get_roundtrip(self) -> None:
        store = self._initialized()
        store.set_secret("kraken_main:api_key", b"my_api_key_value")
        assert store.get_secret("kraken_main:api_key") == b"my_api_key_value"

    def test_get_missing_secret_raises_keyerror(self) -> None:
        store = self._initialized()
        with pytest.raises(KeyError):
            store.get_secret("never_set")

    def test_overwrite_existing_secret(self) -> None:
        store = self._initialized()
        store.set_secret("ref", b"first")
        store.set_secret("ref", b"second")
        assert store.get_secret("ref") == b"second"

    def test_delete_removes_secret(self) -> None:
        store = self._initialized()
        store.set_secret("ref", b"value")
        store.delete_secret("ref")
        with pytest.raises(KeyError):
            store.get_secret("ref")

    def test_delete_missing_secret_is_noop(self) -> None:
        # Spec doesn't mandate behavior; we treat delete as idempotent.
        store = self._initialized()
        store.delete_secret("never_existed")  # must not raise

    def test_set_when_locked_rejected(self) -> None:
        store = InMemorySecretStore()
        store.initialize("p")
        store.lock()
        with pytest.raises(LockedError):
            store.set_secret("ref", b"value")

    def test_get_when_locked_rejected(self) -> None:
        store = InMemorySecretStore()
        store.initialize("p")
        store.set_secret("ref", b"v")
        store.lock()
        with pytest.raises(LockedError):
            store.get_secret("ref")

    def test_canary_reference_reserved(self) -> None:
        store = self._initialized()
        with pytest.raises(ValueError, match="reserved"):
            store.set_secret(CANARY_REFERENCE, b"x")
        with pytest.raises(ValueError, match="reserved"):
            store.get_secret(CANARY_REFERENCE)
        with pytest.raises(ValueError, match="reserved"):
            store.delete_secret(CANARY_REFERENCE)


# --- Cross-instance: persistence implies a passphrase round-trip -----------------


class TestUnlockRoundtripAcrossLifecycles:
    """Secrets persisted before lock must be retrievable after re-unlock with the
    same passphrase. Critical for the Docker scenario: a container restart locks
    the store, the user re-enters the passphrase, all stored credentials must
    decrypt correctly.

    The in-memory backend simulates this by reusing the same store instance — only
    the in-memory key is cleared by `lock()`."""

    def test_secret_decryptable_after_lock_and_unlock(self) -> None:
        store = InMemorySecretStore()
        store.initialize("the passphrase")
        store.set_secret("ref", b"the secret value")
        store.lock()
        store.unlock("the passphrase")
        assert store.get_secret("ref") == b"the secret value"
