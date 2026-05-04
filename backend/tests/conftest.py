"""Shared pytest fixtures.

Each milestone adds fixtures here.
"""

from __future__ import annotations

import os
import secrets as _secrets
from collections.abc import Iterator
from urllib.parse import urlparse, urlunparse

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from tallykeep.configuration import get_settings
from tallykeep.infrastructure import database
from tallykeep.infrastructure.secrets import InMemorySecretStore
from tallykeep.main import create_app


@pytest.fixture(autouse=True)
def _isolate_unit_tests_from_infrastructure(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Tests marked `unit` run with no live database or redis.

    Without this, `/health`'s probes wait the full TCP connect timeout against
    the configured (but possibly unreachable) backing services on every health
    request, slowing the unit-test loop by orders of magnitude.

    Integration tests opt back in by depending on `base_database_url` /
    `redis_url`, which read the original env values from the host.
    """
    is_unit = any(m.name == "unit" for m in request.node.iter_markers())
    if is_unit:
        monkeypatch.setenv("TALLYKEEP_DATABASE_URL", "")
        monkeypatch.setenv("TALLYKEEP_REDIS_URL", "")
        monkeypatch.setenv("TALLYKEEP_BITCOIND_RPC_URL", "")
        monkeypatch.setenv("TALLYKEEP_BITCOIND_ZMQ_ENDPOINT", "")
        get_settings.cache_clear()
        database.reset_engine_for_tests()
    yield
    if is_unit:
        get_settings.cache_clear()
        database.reset_engine_for_tests()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Synchronous TestClient with an unlocked in-memory SecretStore.

    The store is pre-initialized so the lock middleware passes through; tests
    that exercise the lock semantics build their own app and bypass this
    fixture (see tests/unit/test_unlock_endpoints.py).

    Cheap-Argon2id parameters keep per-test setup at ~1ms.
    """
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1
    )

    store = InMemorySecretStore()
    store.initialize("test passphrase")

    app = create_app()
    app.state.secret_store = store
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def app_with_db(
    clean_test_database: str, monkeypatch: pytest.MonkeyPatch
):  # type: ignore[no-untyped-def]
    """TestClient backed by a freshly-migrated Postgres database.

    Yields a tuple `(client, session_factory)` so tests can poke at the
    database directly when assertions need it.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import sessionmaker

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", clean_test_database)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(clean_test_database, future=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    # Cheap Argon2id so per-test setup is ~1ms instead of ~100ms — the secret
    # store is the only KDF user in this fixture and we only need it to gate
    # the lock middleware.
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1
    )

    # Endpoints behind the lock middleware require an unlocked store; initialize
    # an InMemoryStore so tests reach their handlers. Lock semantics are
    # exercised separately by tests/unit/test_unlock_endpoints.py.
    store = InMemorySecretStore()
    store.initialize("test passphrase")

    app = create_app()
    app.state.secret_store = store
    app.state.session_factory = factory

    with TestClient(app) as test_client:
        yield test_client, factory

    engine.dispose()


@pytest.fixture()
def app_with_db_and_node(
    clean_test_database: str,
    bitcoind_rpc_url: str,
    bitcoind_clean_chain,  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
):  # type: ignore[no-untyped-def]
    """TestClient with both a fresh DB and a live NodeAdapter wired.

    Used by chain-scan integration tests. Yields
    `(client, session_factory, node_adapter)`. Depends on
    `bitcoind_clean_chain` so the regtest chain isn't past the halving
    cliff at session start.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import sessionmaker

    from tallykeep.adapters.node_adapter import NodeAdapter

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", clean_test_database)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(clean_test_database, future=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1
    )

    store = InMemorySecretStore()
    store.initialize("test passphrase")
    node = NodeAdapter(bitcoind_rpc_url, timeout_seconds=60.0)

    app = create_app()
    app.state.secret_store = store
    app.state.session_factory = factory
    app.state.node_adapter = node

    with TestClient(app) as test_client:
        yield test_client, factory, node

    node.close()
    engine.dispose()


# --- Integration test plumbing ----------------------------------------------------


def _admin_url(database_url: str, target_database: str) -> str:
    """Return the same DSN but pointing at `target_database`.

    Used to manage the actual test database via the maintenance database (`postgres`).
    """
    parts = urlparse(database_url)
    new_path = f"/{target_database}"
    return urlunparse(parts._replace(path=new_path))


@pytest.fixture(scope="session")
def base_database_url() -> str:
    """Configured Postgres DSN, or skip when unavailable.

    Integration tests share a single base DSN; per-test isolation is achieved by
    creating a fresh database for each test via the `clean_test_database` fixture.
    """
    url = os.environ.get("TALLYKEEP_DATABASE_URL", "")
    if not url:
        pytest.skip("TALLYKEEP_DATABASE_URL not set — postgres integration tests skipped")

    # Quick reachability check via a connection attempt to the maintenance database.
    admin_url = _admin_url(url, "postgres")
    try:
        engine = sa.create_engine(admin_url, future=True)
        with engine.connect():
            pass
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"postgres unreachable at {admin_url!r}: {exc}")

    return url


@pytest.fixture(scope="session")
def bitcoind_rpc_url() -> str:
    """Configured bitcoind RPC URL, or skip when unavailable.

    Integration tests share one bitcoind regtest instance. Per-test isolation
    is achieved by using throwaway addresses / wallet names — bitcoind's
    in-memory state is small and the regtest chain is cheap to extend.
    """
    url = os.environ.get("TALLYKEEP_BITCOIND_RPC_URL", "")
    if not url:
        pytest.skip(
            "TALLYKEEP_BITCOIND_RPC_URL not set — bitcoind integration tests skipped"
        )

    try:
        from tallykeep.adapters.node_adapter import NodeAdapter

        with NodeAdapter(url, timeout_seconds=2.0) as node:
            if not node.is_healthy():
                pytest.skip(f"bitcoind unreachable at {url!r}")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"bitcoind unreachable at {url!r}: {exc}")

    return url


@pytest.fixture(scope="session")
def bitcoind_clean_chain(bitcoind_rpc_url: str) -> None:
    """Roll the regtest chain back near genesis if it has accumulated past
    a depth where halvings make spending tests unreliable.

    Regtest's block subsidy halves every 150 blocks. Past ~10 halvings
    (height ~1500) the per-block reward is so small that newly-created
    wallets struggle to send 1000-3000 sats from a 150-block faucet
    fixture. This fixture invalidates the chain back to height 1 once
    per test session when needed; subsequent sessions on a fresh chain
    skip the rollback.

    Tests that need a faucet should depend on this fixture by listing it
    in their signature (it's session-scoped so the cost is paid once
    per test session).
    """
    from tallykeep.adapters.node_adapter import NodeAdapter

    DEPTH_LIMIT = 1500

    with NodeAdapter(bitcoind_rpc_url, timeout_seconds=60.0) as node:
        info = node.get_blockchain_info()
        if info.blocks <= DEPTH_LIMIT:
            return
        # Invalidate the block at height 2 to roll the tip back to height 1
        # (regtest only — `invalidateblock` is allowed there).
        block_at_2 = node._call("getblockhash", [2])
        node._call("invalidateblock", [block_at_2])
        new_info = node.get_blockchain_info()
        assert new_info.blocks <= 1, (
            f"chain reset failed; still at height {new_info.blocks}"
        )


@pytest.fixture(scope="session")
def redis_url() -> str:
    """Configured Redis URL, or skip when unavailable.

    Integration tests share one Redis instance. Per-test isolation is achieved by
    using a unique key prefix or channel name, since Redis pub/sub is broadcast
    and stateless across tests.
    """
    url = os.environ.get("TALLYKEEP_REDIS_URL", "")
    if not url:
        pytest.skip(
            "TALLYKEEP_REDIS_URL not set — redis integration tests skipped"
        )

    try:
        import redis as _redis

        client = _redis.Redis.from_url(url)
        client.ping()
        client.close()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"redis unreachable at {url!r}: {exc}")

    return url


@pytest.fixture()
def clean_test_database(base_database_url: str) -> Iterator[str]:
    """Provide a fresh, empty Postgres database for one test, drop it after.

    Yields the connection URL pointing at the per-test database.
    """
    suffix = _secrets.token_hex(4)
    test_db = f"tallykeep_test_{suffix}"
    admin_url = _admin_url(base_database_url, "postgres")
    test_url = _admin_url(base_database_url, test_db)

    admin_engine = sa.create_engine(
        admin_url,
        future=True,
        isolation_level="AUTOCOMMIT",  # CREATE/DROP DATABASE cannot run in a tx
    )
    try:
        with admin_engine.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{test_db}"')
        try:
            yield test_url
        finally:
            with admin_engine.connect() as conn:
                # Terminate any lingering connections so DROP can complete.
                conn.exec_driver_sql(
                    f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{test_db}' AND pid <> pg_backend_pid()
                    """
                )
                conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{test_db}"')
    finally:
        admin_engine.dispose()
