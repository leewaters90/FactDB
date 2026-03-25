"""
Database engine and session management for FactDB.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, Engine, event, text
from sqlalchemy.orm import sessionmaker, Session

from factdb.models import Base
import factdb.project_models  # noqa: F401 — registers Project/DesignElement tables with Base.metadata

# Default database path — can be overridden via the FACTDB_DATABASE_URL env var.
_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "factdb.sqlite"
)
_DEFAULT_DB_URL = f"sqlite:///{_DEFAULT_DB_PATH}"

_engine: Engine | None = None

# ---------------------------------------------------------------------------
# FTS5 schema — SQLite full-text search virtual table
# ---------------------------------------------------------------------------

_FTS5_CREATE = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    fact_id UNINDEXED,
    title,
    content,
    extended_content,
    tokenize = 'porter unicode61'
);
"""

# Triggers keep the FTS index in sync with the facts table.
_FTS5_TRIGGERS = [
    # INSERT
    """
    CREATE TRIGGER IF NOT EXISTS facts_fts_insert
    AFTER INSERT ON facts BEGIN
        INSERT INTO facts_fts(fact_id, title, content, extended_content)
        VALUES (new.id, new.title, new.content, new.extended_content);
    END;
    """,
    # DELETE
    """
    CREATE TRIGGER IF NOT EXISTS facts_fts_delete
    AFTER DELETE ON facts BEGIN
        DELETE FROM facts_fts WHERE fact_id = old.id;
    END;
    """,
    # UPDATE
    """
    CREATE TRIGGER IF NOT EXISTS facts_fts_update
    AFTER UPDATE ON facts BEGIN
        DELETE FROM facts_fts WHERE fact_id = old.id;
        INSERT INTO facts_fts(fact_id, title, content, extended_content)
        VALUES (new.id, new.title, new.content, new.extended_content);
    END;
    """,
]

_FTS5_BACKFILL = """
INSERT INTO facts_fts(fact_id, title, content, extended_content)
SELECT f.id, f.title, f.content, f.extended_content
FROM facts f
WHERE NOT EXISTS (
    SELECT 1 FROM facts_fts ff WHERE ff.fact_id = f.id
);
"""


def _setup_fts5(connection) -> None:
    """Create the FTS5 virtual table, triggers, and back-fill existing rows."""
    connection.execute(text(_FTS5_CREATE))
    for trigger_sql in _FTS5_TRIGGERS:
        connection.execute(text(trigger_sql))
    connection.execute(text(_FTS5_BACKFILL))


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
                # Increase cache to 32 MB for better read performance.
                cursor.execute("PRAGMA cache_size=-32768")
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
    Create all tables if they don't exist, apply composite indexes, set up
    the FTS5 virtual table and triggers, and return the engine.

    Args:
        database_url: Optional connection string (see ``get_engine``).
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    # Apply composite / covering indexes that cannot be added by create_all()
    # when the table already exists.  CREATE INDEX IF NOT EXISTS is idempotent.
    _COMPOSITE_INDEXES = [
        # Covering index for active-facts list filtered by domain + status.
        "CREATE INDEX IF NOT EXISTS ix_facts_active_domain_status "
        "ON facts (is_active, domain, status)",
        # Supports layered retrieval by domain + level + status.
        "CREATE INDEX IF NOT EXISTS ix_facts_domain_level_status "
        "ON facts (domain, detail_level, status)",
        # Supports confidence-ordered queries within active fact set.
        "CREATE INDEX IF NOT EXISTS ix_facts_active_confidence "
        "ON facts (is_active, confidence_score)",
        # Graph traversal: outgoing edges filtered by relationship type.
        "CREATE INDEX IF NOT EXISTS ix_fact_relationships_src_type "
        "ON fact_relationships (source_fact_id, relationship_type)",
        # Graph traversal: incoming edges filtered by relationship type.
        "CREATE INDEX IF NOT EXISTS ix_fact_relationships_tgt_type "
        "ON fact_relationships (target_fact_id, relationship_type)",
    ]
    with engine.begin() as conn:
        for idx_sql in _COMPOSITE_INDEXES:
            conn.execute(text(idx_sql))

    # Apply FTS5 only for SQLite (the virtual table syntax is SQLite-specific).
    if "sqlite" in str(engine.url):
        with engine.begin() as conn:
            _setup_fts5(conn)

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
