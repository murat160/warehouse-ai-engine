"""SQLAlchemy engine + session factory.

A single global engine/session-factory is created lazily on first use and
keyed by the database URL. SQLite is the default for local dev; production
deployments only need to set ``DATABASE_URL=postgresql+psycopg://…`` for the
exact same code to talk to PostgreSQL.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Single declarative base for all ORM models."""


_DEFAULT_SQLITE_PATH = Path("data/warehouse_ai.db")
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None
_init_lock = Lock()


def _resolve_url(url: Optional[str]) -> str:
    if url:
        return url
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    return f"sqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"


def init_db(url: Optional[str] = None) -> Engine:
    """Create the engine, run ``CREATE TABLE IF NOT EXISTS`` and cache the factory."""
    global _engine, _session_factory
    with _init_lock:
        resolved = _resolve_url(url)
        if resolved.startswith("sqlite"):
            # Make sure the parent directory exists for relative paths.
            db_path = resolved.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            resolved,
            future=True,
            echo=False,
            connect_args={"check_same_thread": False} if resolved.startswith("sqlite") else {},
        )
        # Import models so their tables are registered on Base.metadata.
        from . import models  # noqa: F401  -- side-effect import

        Base.metadata.create_all(_engine)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker:
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope. Commits on success, rolls back on error."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_for_tests() -> None:
    """Test-only helper: drops the cached engine so a new ``init_db`` runs."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
