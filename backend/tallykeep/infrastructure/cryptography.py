"""Cryptography helpers — Argon2id KDF and AES-256-GCM authenticated encryption.

Spec module 03 / 10:
- KDF: Argon2id with per-installation random salt and tunable cost parameters.
- Encryption: AES-256-GCM with a fresh 12-byte nonce per secret.

Authenticated encryption means tampering with the ciphertext or the associated data
causes decryption to raise — never returns garbage.

This module deals only with bytes. Callers pass passphrases as `str`, secrets as
`bytes`, and storage layers serialize the resulting structures separately.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# Per spec module 03:
KDF_ALGORITHM = "argon2id"
ENCRYPTION_ALGORITHM = "aes-256-gcm"

# Sizes (bytes). Locked by the algorithm choices above.
KDF_SALT_SIZE = 16
DERIVED_KEY_SIZE = 32  # 256 bits, AES-256-GCM key size
GCM_NONCE_SIZE = 12  # 96-bit nonce, the GCM-recommended size
GCM_TAG_SIZE = 16  # 128-bit auth tag

# Default Argon2id cost parameters per spec module 03. They are stored in
# crypto_parameters at first-run so they can be tuned upward across versions.
DEFAULT_KDF_MEMORY_COST_KIB = 65536  # 64 MiB
DEFAULT_KDF_TIME_COST = 3
DEFAULT_KDF_PARALLELISM = 4


@dataclass(frozen=True)
class KdfParameters:
    """Argon2id parameters, persisted in `crypto_parameters` at first init."""

    salt: bytes
    memory_cost_kib: int = DEFAULT_KDF_MEMORY_COST_KIB
    time_cost: int = DEFAULT_KDF_TIME_COST
    parallelism: int = DEFAULT_KDF_PARALLELISM

    def __post_init__(self) -> None:
        if len(self.salt) != KDF_SALT_SIZE:
            raise ValueError(f"KDF salt must be {KDF_SALT_SIZE} bytes")
        if self.memory_cost_kib < 8:
            raise ValueError("Argon2id memory_cost_kib must be >= 8")
        if self.time_cost < 1:
            raise ValueError("Argon2id time_cost must be >= 1")
        if self.parallelism < 1:
            raise ValueError("Argon2id parallelism must be >= 1")


@dataclass(frozen=True)
class EncryptedSecret:
    """The on-disk representation of an encrypted secret.

    Per spec module 03 the `secret` table stores ciphertext + nonce + tag.
    cryptography's AESGCM concatenates the tag onto the ciphertext, so we slice
    on the boundary when persisting and re-attach when decrypting.
    """

    ciphertext: bytes
    nonce: bytes
    authentication_tag: bytes

    def __post_init__(self) -> None:
        if len(self.nonce) != GCM_NONCE_SIZE:
            raise ValueError(f"GCM nonce must be {GCM_NONCE_SIZE} bytes")
        if len(self.authentication_tag) != GCM_TAG_SIZE:
            raise ValueError(f"GCM authentication tag must be {GCM_TAG_SIZE} bytes")


def generate_salt() -> bytes:
    """Per-installation random salt. Stored in `crypto_parameters`. Not secret."""
    return secrets.token_bytes(KDF_SALT_SIZE)


def derive_key(passphrase: str, params: KdfParameters) -> bytes:
    """Run Argon2id over the passphrase and return a 32-byte symmetric key.

    The result lives in process memory only and is discarded on restart.
    """
    if not isinstance(passphrase, str):
        raise TypeError("passphrase must be a string")
    if not passphrase:
        # Refuse empty passphrases. Argon2id would happily process them, but a UX
        # check at this layer is the last guard before key derivation.
        raise ValueError("passphrase cannot be empty")

    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=params.salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost_kib,
        parallelism=params.parallelism,
        hash_len=DERIVED_KEY_SIZE,
        type=Type.ID,  # Argon2id
    )


def encrypt(plaintext: bytes, key: bytes) -> EncryptedSecret:
    """Encrypt `plaintext` under `key` with a fresh random nonce.

    The 32-byte `key` is the output of `derive_key`. `plaintext` is the raw secret.
    """
    if len(key) != DERIVED_KEY_SIZE:
        raise ValueError(f"key must be {DERIVED_KEY_SIZE} bytes")

    nonce = secrets.token_bytes(GCM_NONCE_SIZE)
    aesgcm = AESGCM(key)
    # cryptography returns ciphertext || tag concatenated.
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    ciphertext = ciphertext_and_tag[:-GCM_TAG_SIZE]
    tag = ciphertext_and_tag[-GCM_TAG_SIZE:]
    return EncryptedSecret(ciphertext=ciphertext, nonce=nonce, authentication_tag=tag)


def decrypt(secret: EncryptedSecret, key: bytes) -> bytes:
    """Decrypt and verify. Raises `cryptography.exceptions.InvalidTag` on tamper."""
    if len(key) != DERIVED_KEY_SIZE:
        raise ValueError(f"key must be {DERIVED_KEY_SIZE} bytes")
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(
        secret.nonce,
        secret.ciphertext + secret.authentication_tag,
        associated_data=None,
    )


# Re-export for callers that want to catch the canonical tamper-detected exception.
__all__ = [
    "KDF_ALGORITHM",
    "ENCRYPTION_ALGORITHM",
    "KDF_SALT_SIZE",
    "DERIVED_KEY_SIZE",
    "GCM_NONCE_SIZE",
    "GCM_TAG_SIZE",
    "DEFAULT_KDF_MEMORY_COST_KIB",
    "DEFAULT_KDF_TIME_COST",
    "DEFAULT_KDF_PARALLELISM",
    "KdfParameters",
    "EncryptedSecret",
    "InvalidTag",
    "generate_salt",
    "derive_key",
    "encrypt",
    "decrypt",
]
