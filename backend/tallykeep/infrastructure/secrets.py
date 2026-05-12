"""Secret store — interface plus encrypted-database backend.

Spec module 03: only third-party access credentials live here (custodial provider
keys, bitcoind RPC password, future Lightning credentials). **No Bitcoin signing
material.** This is the central security commitment of the app.

Two backends are defined in spec module 03:
  - keyring (dev) — uses the OS keyring; placeholder, not used by the Docker stack.
  - encrypted_database (Docker) — implemented here, active in CONTEXT.md's all-Docker
    development stack.

A small `InMemorySecretStore` is included for unit tests that need the full unlock
semantics without a database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tallykeep.infrastructure.cryptography import (
    DEFAULT_KDF_MEMORY_COST_KIB,
    DEFAULT_KDF_PARALLELISM,
    DEFAULT_KDF_TIME_COST,
    ENCRYPTION_ALGORITHM,
    KDF_ALGORITHM,
    EncryptedSecret,
    InvalidTag,
    KdfParameters,
    decrypt,
    derive_key,
    encrypt,
    generate_salt,
)
from tallykeep.models import CryptoParametersRow, SecretRow


# Canary secret: a fixed plaintext stored encrypted at initialization. On every
# unlock attempt we try to decrypt this; success ⇒ the passphrase is correct.
# The reference is reserved and cannot be used for application secrets.
CANARY_REFERENCE = "__canary__"
CANARY_PLAINTEXT = b"tallykeep canary v1"

# Singleton id for crypto_parameters (matches the database CHECK constraint).
CRYPTO_PARAMETERS_ID = UUID("00000000-0000-0000-0000-000000000001")


class AlreadyInitializedError(RuntimeError):
    """Raised when initialize is called on a store that already has parameters."""


class NotInitializedError(RuntimeError):
    """Raised when a method that requires initialization runs first."""


class LockedError(RuntimeError):
    """Raised when a secret operation runs without an active unlock."""


class WrongPassphraseError(RuntimeError):
    """Raised by unlock when the passphrase does not decrypt the canary."""


class SecretStore(ABC):
    """Common surface for both backends.

    Lifecycle:
      1. is_initialized() — checks whether first-run setup happened.
      2. initialize(passphrase) — generates salt + canary, persists, derives key.
      3. unlock(passphrase) — derives key, validates against canary, holds key
         in process memory.
      4. lock() — discards the in-memory key.
      5. set/get/delete operate only while unlocked.
      6. validate_passphrase(passphrase) — check passphrase WITHOUT changing
         lock state. Used by the phone-side passphrase-validate endpoint.
    """

    @abstractmethod
    def is_initialized(self) -> bool: ...

    @abstractmethod
    def initialize(self, passphrase: str) -> None: ...

    @abstractmethod
    def unlock(self, passphrase: str) -> None: ...

    @abstractmethod
    def lock(self) -> None: ...

    @abstractmethod
    def is_unlocked(self) -> bool: ...

    @abstractmethod
    def validate_passphrase(self, passphrase: str) -> bool:
        """Check passphrase WITHOUT changing lock state.

        Returns True if correct, False if wrong. Raises NotInitializedError
        if the store has never been initialized.
        """
        ...

    @abstractmethod
    def set_secret(self, reference: str, value: bytes) -> None: ...

    @abstractmethod
    def get_secret(self, reference: str) -> bytes: ...

    @abstractmethod
    def delete_secret(self, reference: str) -> None: ...


class _SecretStoreBase(SecretStore):
    """Shared lifecycle/key-state management. Backend stores override only the
    storage operations and the parameter persistence."""

    def __init__(self) -> None:
        self._key: bytes | None = None
        self._lock = RLock()  # protects _key against concurrent unlock/lock calls

    # --- key state ----------------------------------------------------------------

    def is_unlocked(self) -> bool:
        with self._lock:
            return self._key is not None

    def lock(self) -> None:
        with self._lock:
            self._key = None

    def _require_unlocked(self) -> bytes:
        with self._lock:
            if self._key is None:
                raise LockedError("Secret store is locked")
            return self._key

    # --- subclass hooks -----------------------------------------------------------

    @abstractmethod
    def _load_kdf_parameters(self) -> KdfParameters | None: ...

    @abstractmethod
    def _store_kdf_parameters(self, params: KdfParameters) -> None: ...

    @abstractmethod
    def _store_encrypted(self, reference: str, secret: EncryptedSecret) -> None: ...

    @abstractmethod
    def _load_encrypted(self, reference: str) -> EncryptedSecret | None: ...

    @abstractmethod
    def _delete_encrypted(self, reference: str) -> None: ...

    # --- lifecycle ----------------------------------------------------------------

    def is_initialized(self) -> bool:
        return self._load_kdf_parameters() is not None

    def initialize(self, passphrase: str) -> None:
        if self.is_initialized():
            raise AlreadyInitializedError("Secret store already initialized")

        params = KdfParameters(
            salt=generate_salt(),
            memory_cost_kib=DEFAULT_KDF_MEMORY_COST_KIB,
            time_cost=DEFAULT_KDF_TIME_COST,
            parallelism=DEFAULT_KDF_PARALLELISM,
        )
        key = derive_key(passphrase, params)

        # Persist params first, then write the canary, then "unlock" with the
        # in-memory key. If any step fails the database state is recoverable.
        self._store_kdf_parameters(params)
        self._store_encrypted(CANARY_REFERENCE, encrypt(CANARY_PLAINTEXT, key))

        with self._lock:
            self._key = key

    def unlock(self, passphrase: str) -> None:
        params = self._load_kdf_parameters()
        if params is None:
            raise NotInitializedError("Secret store has not been initialized")

        key = derive_key(passphrase, params)

        canary = self._load_encrypted(CANARY_REFERENCE)
        if canary is None:
            # Initialized rows exist but the canary is gone — treat as not initialized
            # to force re-initialization rather than silently accept any passphrase.
            raise NotInitializedError(
                "Crypto parameters are present but the canary is missing"
            )

        try:
            decrypted = decrypt(canary, key)
        except InvalidTag as exc:
            raise WrongPassphraseError("Passphrase failed canary verification") from exc
        if decrypted != CANARY_PLAINTEXT:
            # Defense-in-depth: reject if somehow the canary decrypts but to garbage.
            raise WrongPassphraseError("Canary plaintext mismatch")

        with self._lock:
            self._key = key

    def validate_passphrase(self, passphrase: str) -> bool:
        """Check passphrase correctness WITHOUT storing the derived key."""
        params = self._load_kdf_parameters()
        if params is None:
            raise NotInitializedError("Secret store has not been initialized")

        key = derive_key(passphrase, params)

        canary = self._load_encrypted(CANARY_REFERENCE)
        if canary is None:
            raise NotInitializedError(
                "Crypto parameters are present but the canary is missing"
            )

        try:
            decrypted = decrypt(canary, key)
        except InvalidTag:
            return False
        return decrypted == CANARY_PLAINTEXT

    # --- secret CRUD --------------------------------------------------------------

    def set_secret(self, reference: str, value: bytes) -> None:
        if reference == CANARY_REFERENCE:
            raise ValueError(f"Reference {CANARY_REFERENCE!r} is reserved")
        key = self._require_unlocked()
        self._store_encrypted(reference, encrypt(value, key))

    def get_secret(self, reference: str) -> bytes:
        if reference == CANARY_REFERENCE:
            raise ValueError(f"Reference {CANARY_REFERENCE!r} is reserved")
        key = self._require_unlocked()
        encrypted = self._load_encrypted(reference)
        if encrypted is None:
            raise KeyError(reference)
        return decrypt(encrypted, key)

    def delete_secret(self, reference: str) -> None:
        if reference == CANARY_REFERENCE:
            raise ValueError(f"Reference {CANARY_REFERENCE!r} is reserved")
        # Locking is not strictly required to delete (no key needed), but the spec
        # says credential ops happen post-unlock, so we enforce it.
        self._require_unlocked()
        self._delete_encrypted(reference)


class InMemorySecretStore(_SecretStoreBase):
    """Test double: same lifecycle, dictionaries instead of a database."""

    def __init__(self) -> None:
        super().__init__()
        self._params: KdfParameters | None = None
        self._secrets: dict[str, EncryptedSecret] = {}

    def _load_kdf_parameters(self) -> KdfParameters | None:
        return self._params

    def _store_kdf_parameters(self, params: KdfParameters) -> None:
        self._params = params

    def _store_encrypted(self, reference: str, secret: EncryptedSecret) -> None:
        self._secrets[reference] = secret

    def _load_encrypted(self, reference: str) -> EncryptedSecret | None:
        return self._secrets.get(reference)

    def _delete_encrypted(self, reference: str) -> None:
        self._secrets.pop(reference, None)


class EncryptedDatabaseSecretStore(_SecretStoreBase):
    """Spec module 03 production backend.

    Each store call uses a fresh session via the configured factory so the store
    can be safely shared across requests.
    """

    def __init__(self, session_factory: object) -> None:
        super().__init__()
        # session_factory is sqlalchemy.orm.sessionmaker; we type it loosely to
        # avoid coupling tests to a concrete sessionmaker generic.
        self._session_factory = session_factory

    def _open(self) -> Session:
        return self._session_factory()  # type: ignore[no-any-return, operator]

    def _load_kdf_parameters(self) -> KdfParameters | None:
        with self._open() as session:
            row = session.get(CryptoParametersRow, CRYPTO_PARAMETERS_ID)
            if row is None:
                return None
            if row.kdf_algorithm != KDF_ALGORITHM:
                raise RuntimeError(
                    f"Unsupported KDF algorithm in database: {row.kdf_algorithm!r}"
                )
            return KdfParameters(
                salt=bytes(row.kdf_salt),
                memory_cost_kib=row.kdf_memory_cost,
                time_cost=row.kdf_time_cost,
                parallelism=row.kdf_parallelism,
            )

    def _store_kdf_parameters(self, params: KdfParameters) -> None:
        with self._open() as session:
            row = CryptoParametersRow(
                id=CRYPTO_PARAMETERS_ID,
                kdf_algorithm=KDF_ALGORITHM,
                kdf_salt=params.salt,
                kdf_memory_cost=params.memory_cost_kib,
                kdf_time_cost=params.time_cost,
                kdf_parallelism=params.parallelism,
                encryption_algorithm=ENCRYPTION_ALGORITHM,
            )
            session.add(row)
            session.commit()

    def _store_encrypted(self, reference: str, secret: EncryptedSecret) -> None:
        with self._open() as session:
            existing = session.get(SecretRow, reference)
            if existing is None:
                session.add(
                    SecretRow(
                        reference=reference,
                        ciphertext=secret.ciphertext,
                        nonce=secret.nonce,
                        authentication_tag=secret.authentication_tag,
                    )
                )
            else:
                existing.ciphertext = secret.ciphertext
                existing.nonce = secret.nonce
                existing.authentication_tag = secret.authentication_tag
                existing.updated_at = datetime.now(UTC)
            session.commit()

    def _load_encrypted(self, reference: str) -> EncryptedSecret | None:
        with self._open() as session:
            row = session.execute(
                select(SecretRow).where(SecretRow.reference == reference)
            ).scalar_one_or_none()
            if row is None:
                return None
            return EncryptedSecret(
                ciphertext=bytes(row.ciphertext),
                nonce=bytes(row.nonce),
                authentication_tag=bytes(row.authentication_tag),
            )

    def _delete_encrypted(self, reference: str) -> None:
        with self._open() as session:
            session.execute(delete(SecretRow).where(SecretRow.reference == reference))
            session.commit()


__all__ = [
    "SecretStore",
    "InMemorySecretStore",
    "EncryptedDatabaseSecretStore",
    "AlreadyInitializedError",
    "NotInitializedError",
    "LockedError",
    "WrongPassphraseError",
    "CANARY_REFERENCE",
]
