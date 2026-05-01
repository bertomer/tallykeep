"""Shared pytest fixtures.

Each milestone adds fixtures here. M0 only ships an in-process FastAPI test client.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
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
