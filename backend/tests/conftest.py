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

from tallykeep.main import create_app


@pytest.fixture(scope="session")
def app() -> Iterator:
    """Fresh FastAPI app for the test session."""
    yield create_app()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    """Synchronous TestClient bound to a fresh app instance.

    Per-test scope so route registrations or app state from one test cannot leak.
    """
    with TestClient(app) as test_client:
        yield test_client


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
