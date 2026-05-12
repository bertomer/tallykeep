"""paired_device table — device credential registry (auth layer, spec 01 §"Network security posture")."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class PairedDeviceRow(Base):
    """One row per paired client device.

    The raw device credential is never stored. `credential_hash` holds the
    Argon2id hash of the credential issued to the device at pairing time.
    """

    __tablename__ = "paired_device"
    __table_args__ = (
        Index("ix_paired_device_revoked_at", "revoked_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # Argon2id hash string (argon2-cffi PasswordHasher format — includes salt and params).
    credential_hash: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
