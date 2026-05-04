"""Runtime configuration loading.

Spec module 01: configuration is a single TOML file mounted into the backend container.
For M0 we read environment variables only — the TOML loader lands in M1 alongside the
secrets unlock flow. Values here are limited to what the M0 health endpoint and stack
wiring need.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALLYKEEP_",
        env_file=None,
        extra="ignore",
    )

    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # Network bindings reserved for later milestones; declared here so config tests
    # can assert their presence without forcing implementation now.
    database_url: str = Field(default="")
    redis_url: str = Field(default="")
    bitcoind_rpc_url: str = Field(default="")
    # Single ZMQ endpoint — bitcoind multiplexes hashblock/hashtx/rawblock/rawtx
    # over the same PUB socket via topic frames. Spec module 05 documents the
    # bitcoin.conf lines users add to enable it.
    bitcoind_zmq_endpoint: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
