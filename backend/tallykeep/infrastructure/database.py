"""Database engine and session factory.

Single sync engine for v1 (per spec module 01: SQLAlchemy 2.x). Async support is a
v2 concern; FastAPI runs the sync engine in a threadpool which is more than fast
enough for a single-user app.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from tallykeep.configuration import get_settings


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("TALLYKEEP_DATABASE_URL is not configured")
        # connect_timeout caps how long a single connection attempt blocks. Important
        # so that /health probes do not hang the API when Postgres is briefly down.
        _engine = create_engine(
            settings.database_url,
            future=True,
            pool_pre_ping=True,  # Survives Postgres restarts without bouncing the app.
            echo=False,
            connect_args={"connect_timeout": 2},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context-managed session with commit-on-success / rollback-on-error semantics."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_for_tests() -> None:
    """Test helper — drop cached engine and session factory.

    Useful when a test changes the database URL or wants a clean connection pool.
    Never call this in production code paths.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
