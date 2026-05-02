"""Pydantic schemas for /api/v1/configuration.

Spec module 03 / 04: configuration is a key-value store backed by the
``runtime_configuration`` table. v1 organizes the keys into named sections
(``bitcoind``, ``fee_estimation``, ``custodial_polling``, ``analysis``,
``notifications``) so the API exposes a nested object instead of flat dotted
keys.

Each section is a Pydantic model — unknown keys are rejected at the API
boundary, so a typo in a PATCH body returns 422 instead of silently writing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


_StrictBase = ConfigDict(extra="forbid")


class BitcoindConfiguration(BaseModel):
    model_config = _StrictBase

    rpc_host: str | None = None
    rpc_port: int | None = Field(default=None, ge=1, le=65535)
    zmq_block_endpoint: str | None = None
    zmq_tx_endpoint: str | None = None


class FeeEstimationConfiguration(BaseModel):
    model_config = _StrictBase

    strategy: str | None = None  # tier name (economy / normal / priority) or "custom"


class CustodialPollingConfiguration(BaseModel):
    model_config = _StrictBase

    interval_seconds: int | None = Field(default=None, ge=60, le=3600)


class AnalysisConfiguration(BaseModel):
    model_config = _StrictBase

    recompute_interval_minutes: int | None = Field(default=None, ge=1)


class NotificationsConfiguration(BaseModel):
    model_config = _StrictBase

    enabled: bool | None = None


class ConfigurationResponse(BaseModel):
    """Full configuration response — every section is always present, fields default
    to None when no override exists."""

    model_config = _StrictBase

    bitcoind: BitcoindConfiguration = BitcoindConfiguration()
    fee_estimation: FeeEstimationConfiguration = FeeEstimationConfiguration()
    custodial_polling: CustodialPollingConfiguration = CustodialPollingConfiguration()
    analysis: AnalysisConfiguration = AnalysisConfiguration()
    notifications: NotificationsConfiguration = NotificationsConfiguration()


class ConfigurationUpdate(BaseModel):
    """Partial update — every section is optional, every field within optional."""

    model_config = _StrictBase

    bitcoind: BitcoindConfiguration | None = None
    fee_estimation: FeeEstimationConfiguration | None = None
    custodial_polling: CustodialPollingConfiguration | None = None
    analysis: AnalysisConfiguration | None = None
    notifications: NotificationsConfiguration | None = None
