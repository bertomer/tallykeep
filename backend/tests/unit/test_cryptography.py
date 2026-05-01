"""Cryptography helpers — unit tests for spec module 03.

Test Argon2id derivation determinism, AES-256-GCM authenticated-encryption properties,
and the dataclass invariants. Argon2id parameters are dialled down to the minimum so
the suite stays fast; the real defaults are validated separately by the secrets
module's roundtrip test.
"""

from __future__ import annotations

import os

import pytest

from tallykeep.infrastructure.cryptography import (
    DERIVED_KEY_SIZE,
    GCM_NONCE_SIZE,
    GCM_TAG_SIZE,
    KDF_SALT_SIZE,
    EncryptedSecret,
    InvalidTag,
    KdfParameters,
    decrypt,
    derive_key,
    encrypt,
    generate_salt,
)


pytestmark = pytest.mark.unit


# Cheap Argon2id parameters for the unit tests. The defaults (64 MiB / 3 iterations /
# parallelism 4) are too expensive to run dozens of times in unit tests. Production
# uses the defaults from the module.
CHEAP_PARAMS = KdfParameters(
    salt=b"\x00" * KDF_SALT_SIZE,
    memory_cost_kib=8,
    time_cost=1,
    parallelism=1,
)


def _fresh_params(memory_cost_kib: int = 8, time_cost: int = 1) -> KdfParameters:
    return KdfParameters(
        salt=generate_salt(),
        memory_cost_kib=memory_cost_kib,
        time_cost=time_cost,
        parallelism=1,
    )


# --- KDF parameter validation ----------------------------------------------------


class TestKdfParametersInvariants:
    def test_salt_must_be_correct_length(self) -> None:
        with pytest.raises(ValueError, match="salt must be"):
            KdfParameters(salt=b"\x00" * (KDF_SALT_SIZE - 1))

    def test_memory_cost_must_be_at_least_eight(self) -> None:
        with pytest.raises(ValueError, match="memory_cost"):
            KdfParameters(salt=generate_salt(), memory_cost_kib=4)

    def test_time_cost_must_be_at_least_one(self) -> None:
        with pytest.raises(ValueError, match="time_cost"):
            KdfParameters(salt=generate_salt(), time_cost=0)

    def test_parallelism_must_be_at_least_one(self) -> None:
        with pytest.raises(ValueError, match="parallelism"):
            KdfParameters(salt=generate_salt(), parallelism=0)


# --- KDF behavior -----------------------------------------------------------------


class TestDeriveKey:
    def test_output_size(self) -> None:
        key = derive_key("correct horse battery staple", CHEAP_PARAMS)
        assert len(key) == DERIVED_KEY_SIZE

    def test_same_input_same_output(self) -> None:
        """Argon2id is deterministic given identical inputs."""
        passphrase = "an example passphrase"
        params = _fresh_params()
        first = derive_key(passphrase, params)
        second = derive_key(passphrase, params)
        assert first == second

    def test_different_passphrase_different_key(self) -> None:
        params = _fresh_params()
        a = derive_key("passphrase one", params)
        b = derive_key("passphrase two", params)
        assert a != b

    def test_different_salt_different_key(self) -> None:
        a = derive_key("same passphrase", _fresh_params())
        b = derive_key("same passphrase", _fresh_params())
        assert a != b  # different randomly-generated salts

    def test_empty_passphrase_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            derive_key("", CHEAP_PARAMS)

    def test_non_string_passphrase_rejected(self) -> None:
        with pytest.raises(TypeError):
            derive_key(b"not a string", CHEAP_PARAMS)  # type: ignore[arg-type]


# --- AES-GCM behavior ------------------------------------------------------------


class TestEncryptDecryptRoundtrip:
    def test_roundtrip_recovers_plaintext(self) -> None:
        key = derive_key("test passphrase", CHEAP_PARAMS)
        plaintext = b"my Kraken API key value"
        encrypted = encrypt(plaintext, key)
        recovered = decrypt(encrypted, key)
        assert recovered == plaintext

    def test_nonce_is_12_bytes(self) -> None:
        key = os.urandom(DERIVED_KEY_SIZE)
        encrypted = encrypt(b"x", key)
        assert len(encrypted.nonce) == GCM_NONCE_SIZE

    def test_authentication_tag_is_16_bytes(self) -> None:
        key = os.urandom(DERIVED_KEY_SIZE)
        encrypted = encrypt(b"x", key)
        assert len(encrypted.authentication_tag) == GCM_TAG_SIZE

    def test_each_encryption_uses_a_fresh_nonce(self) -> None:
        """Reusing a (key, nonce) pair under GCM is catastrophic. The encrypt helper
        must generate a fresh nonce on every call."""
        key = os.urandom(DERIVED_KEY_SIZE)
        nonces = {encrypt(b"same plaintext", key).nonce for _ in range(50)}
        assert len(nonces) == 50

    def test_each_encryption_produces_different_ciphertext(self) -> None:
        """Different nonce ⇒ different ciphertext for identical plaintext."""
        key = os.urandom(DERIVED_KEY_SIZE)
        ciphertexts = {encrypt(b"same plaintext", key).ciphertext for _ in range(20)}
        assert len(ciphertexts) == 20


class TestAuthenticatedEncryption:
    def test_ciphertext_tamper_rejected(self) -> None:
        key = os.urandom(DERIVED_KEY_SIZE)
        encrypted = encrypt(b"important secret", key)

        # Flip a bit in the ciphertext.
        tampered_bytes = bytes([encrypted.ciphertext[0] ^ 0x01]) + encrypted.ciphertext[1:]
        tampered = EncryptedSecret(
            ciphertext=tampered_bytes,
            nonce=encrypted.nonce,
            authentication_tag=encrypted.authentication_tag,
        )
        with pytest.raises(InvalidTag):
            decrypt(tampered, key)

    def test_tag_tamper_rejected(self) -> None:
        key = os.urandom(DERIVED_KEY_SIZE)
        encrypted = encrypt(b"important secret", key)

        tampered_tag = bytes([encrypted.authentication_tag[0] ^ 0x01]) + encrypted.authentication_tag[1:]
        tampered = EncryptedSecret(
            ciphertext=encrypted.ciphertext,
            nonce=encrypted.nonce,
            authentication_tag=tampered_tag,
        )
        with pytest.raises(InvalidTag):
            decrypt(tampered, key)

    def test_wrong_key_rejected(self) -> None:
        right = os.urandom(DERIVED_KEY_SIZE)
        wrong = os.urandom(DERIVED_KEY_SIZE)
        encrypted = encrypt(b"important secret", right)
        with pytest.raises(InvalidTag):
            decrypt(encrypted, wrong)


class TestKeySizeEnforcement:
    def test_encrypt_rejects_wrong_key_size(self) -> None:
        with pytest.raises(ValueError, match="key must be"):
            encrypt(b"x", os.urandom(DERIVED_KEY_SIZE - 1))

    def test_decrypt_rejects_wrong_key_size(self) -> None:
        encrypted = encrypt(b"x", os.urandom(DERIVED_KEY_SIZE))
        with pytest.raises(ValueError, match="key must be"):
            decrypt(encrypted, os.urandom(DERIVED_KEY_SIZE - 1))


class TestEncryptedSecretInvariants:
    def test_nonce_size_enforced(self) -> None:
        with pytest.raises(ValueError, match="nonce must be"):
            EncryptedSecret(
                ciphertext=b"c",
                nonce=b"\x00" * (GCM_NONCE_SIZE - 1),
                authentication_tag=b"\x00" * GCM_TAG_SIZE,
            )

    def test_tag_size_enforced(self) -> None:
        with pytest.raises(ValueError, match="authentication tag"):
            EncryptedSecret(
                ciphertext=b"c",
                nonce=b"\x00" * GCM_NONCE_SIZE,
                authentication_tag=b"\x00" * (GCM_TAG_SIZE - 1),
            )
