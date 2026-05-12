"""user_profile, runtime_configuration, crypto_parameters, secret tables.

Singletons + key-value runtime config + secret-store schema (spec module 03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Integer,
    LargeBinary,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class UserProfileRow(Base):
    """Singleton row — id is fixed and CHECKed in the database."""

    __tablename__ = "user_profile"
    __table_args__ = (
        CheckConstraint(
            "id = '00000000-0000-0000-0000-000000000001'",
            name="user_profile_singleton_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    feature_flags: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    base_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'EUR'")
    )
    locale: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'en'")
    )
    principles_acknowledged_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class RuntimeConfigurationRow(Base):
    """Key-value table for runtime configuration (no abbreviation per spec module 03)."""

    __tablename__ = "runtime_configuration"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class CryptoParametersRow(Base):
    """Singleton row — KDF + encryption parameters for the secret store.

    Per spec module 03, the parameters are stored so they can be tuned upward across
    versions without breaking existing deployments.
    """

    __tablename__ = "crypto_parameters"
    __table_args__ = (
        CheckConstraint(
            "id = '00000000-0000-0000-0000-000000000001'",
            name="crypto_parameters_singleton_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kdf_algorithm: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'argon2id'")
    )
    kdf_salt: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kdf_memory_cost: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("65536")
    )
    kdf_time_cost: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("3")
    )
    kdf_parallelism: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("4")
    )
    encryption_algorithm: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'aes-256-gcm'")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class SecretRow(Base):
    """One row per encrypted secret. Reference is the lookup key used by callers.

    Spec commitment: only third-party access credentials (custodial provider keys,
    bitcoind RPC password, future Lightning credentials). Never any Bitcoin signing
    material.
    """

    __tablename__ = "secret"

    reference: Mapped[str] = mapped_column(String(200), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    authentication_tag: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class EventEmissionLogRow(Base):
    """Persist-first-emit-second audit log for the event bus (spec modules 01 / 03).

    Critical events (`is_critical=true`) are watched by the audit reconciler subscriber
    until they are acknowledged.
    """

    __tablename__ = "event_emission_log"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    emitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    is_critical: Mapped[bool] = mapped_column(nullable=False, server_default=text("FALSE"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class JobRow(Base):
    __tablename__ = "job"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    parameters: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    result: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


__all__ = [
    "UserProfileRow",
    "RuntimeConfigurationRow",
    "CryptoParametersRow",
    "SecretRow",
    "EventEmissionLogRow",
    "JobRow",
]
