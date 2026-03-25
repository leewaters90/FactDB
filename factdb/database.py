"""
Database engine and session management for FactDB.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session

from factdb.models import Base

# Default database path — can be overridden via the FACTDB_DATABASE_URL env var.
_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "factdb.sqlite"
)
_DEFAULT_DB_URL = f"sqlite:///{_DEFAULT_DB_PATH}"

_engine: Engine | None = None


def get_engine(database_url: str | None = None) -> Engine:
    """
    Return the singleton SQLAlchemy Engine, creating it on first call.

    Args:
        database_url: SQLAlchemy connection string.  Defaults to the value of
                      the ``FACTDB_DATABASE_URL`` environment variable, or a
                      local SQLite file at ``data/factdb.sqlite``.
    """
    global _engine
    if _engine is None:
        url = database_url or os.environ.get("FACTDB_DATABASE_URL", _DEFAULT_DB_URL)
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
            echo=False,
        )
        if url.startswith("sqlite"):
            # Enable WAL mode and foreign-key enforcement for SQLite
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragmas(dbapi_conn, _connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

    return _engine


def reset_engine() -> None:
    """Dispose the current engine (useful for testing with in-memory DBs)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def init_db(database_url: str | None = None) -> Engine:
    """
    Create all tables if they don't exist and return the engine.

    Args:
        database_url: Optional connection string (see ``get_engine``).
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session_factory(database_url: str | None = None) -> sessionmaker:
    """Return a configured session factory bound to the engine."""
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session(database_url: str | None = None) -> Generator[Session, None, None]:
    """
    Context-manager / generator that yields a database session.

    Usage::

        with next(get_session()) as session:
            ...

    Or as a dependency in a framework::

        session = next(get_session())
    """
    factory = get_session_factory(database_url)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
