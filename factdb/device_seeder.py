"""
Device seeder — thin alias for the JSON-driven seeder.

All engineering facts (core + device design) now live in the shared JSON
folder tree under ``data/facts/``.  This module exists for backward
compatibility with the ``factdb seed-devices`` CLI command and any code
that imports ``seed_devices`` directly; both are now equivalent to calling
:func:`factdb.seeder.seed`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from factdb.seeder import seed


def seed_devices(session: Session, verified_by: str = "system-seed") -> dict:
    """
    Populate the database from the JSON fact folder tree.

    Equivalent to :func:`factdb.seeder.seed`; retained for backward
    compatibility.  Facts are idempotent — already-seeded facts are skipped.

    Args:
        session:     Active SQLAlchemy session.
        verified_by: Identity used for the auto-verification step.

    Returns:
        Dictionary with ``created``, ``skipped``, and ``relationships`` counts.
    """
    return seed(session, verified_by=verified_by)
