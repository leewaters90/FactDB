"""
Shared pytest fixtures for FactDB tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from factdb.models import Base
from factdb.database import reset_engine


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a fresh in-memory SQLite session for each test.

    Uses ``scope="function"`` so every test starts with an empty schema.
    """
    reset_engine()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Enable foreign keys
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()
        reset_engine()
