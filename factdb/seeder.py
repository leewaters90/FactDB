"""
Seeder — populates the database from the JSON fact folder tree.

Facts are loaded from ``data/facts/{domain}/{category}/*.json``.
Relationships are loaded from ``data/facts/_relationships.json``.

Both sources are now the single source of truth; the old Python
``seed_data.py`` / ``seed_data_devices.py`` modules are no longer used.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.json_store import DEFAULT_FACTS_DIR, JsonFactStore
from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    Fact,
    FactRelationship,
    FactStatus,
    RelationshipType,
)
from factdb.repository import FactRepository
from factdb.verification import VerificationWorkflow

# Path to the shared relationships file alongside the fact JSON files.
_RELATIONSHIPS_FILE = Path(DEFAULT_FACTS_DIR) / "_relationships.json"


def _load_relationships() -> list[dict]:
    """Return the list of relationship dicts from the JSON file, or [] if missing."""
    if _RELATIONSHIPS_FILE.exists():
        return json.loads(_RELATIONSHIPS_FILE.read_text(encoding="utf-8"))
    return []


def seed(session: Session, verified_by: str = "system-seed") -> dict:
    """
    Populate the database with engineering facts from the JSON folder tree.

    Reads every ``*.json`` file under ``data/facts/`` and upserts each fact
    into SQLite.  Facts whose titles already exist are skipped.  Relationships
    are loaded from ``data/facts/_relationships.json``.

    Idempotent: safe to call multiple times.

    Args:
        session:     Active SQLAlchemy session.
        verified_by: Identity used for the auto-verification step.

    Returns:
        Dictionary with ``created``, ``skipped``, and ``relationships`` counts.
    """
    repo = FactRepository(session)
    workflow = VerificationWorkflow(session)

    store = JsonFactStore(DEFAULT_FACTS_DIR)
    all_fact_dicts = store.load_all()

    # Build title → Fact mapping from what's already in the database.
    existing: dict[str, Fact] = {
        f.title: f
        for f in session.execute(select(Fact)).scalars().all()
    }

    created = 0
    skipped = 0

    for data in all_fact_dicts:
        title = data.get("title", "")
        if not title:
            continue
        if title in existing:
            skipped += 1
            continue

        fact = repo.create(
            title=title,
            content=data["content"],
            domain=EngineeringDomain(data.get("domain", "general")),
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            detail_level=DetailLevel(data.get("detail_level", "fundamental")),
            extended_content=data.get("extended_content"),
            formula=data.get("formula"),
            units=data.get("units"),
            source=data.get("source"),
            source_url=data.get("source_url"),
            confidence_score=float(data.get("confidence_score", 1.0)),
            status=FactStatus.DRAFT,
            tags=data.get("tags", []),
            created_by=verified_by,
        )
        existing[title] = fact

        # Auto-submit and approve so facts are immediately usable.
        workflow.submit_for_review(fact.id, submitted_by=verified_by)
        workflow.approve(fact.id, verified_by=verified_by, notes="Seed data — auto-approved")

        session.flush()
        created += 1

    # Seed relationships
    rels_created = 0
    for rel_data in _load_relationships():
        src_title = rel_data["source_title"]
        tgt_title = rel_data["target_title"]
        if src_title not in existing or tgt_title not in existing:
            continue

        src = existing[src_title]
        tgt = existing[tgt_title]

        already = session.execute(
            select(FactRelationship).where(
                FactRelationship.source_fact_id == src.id,
                FactRelationship.target_fact_id == tgt.id,
                FactRelationship.relationship_type == rel_data["relationship_type"],
            )
        ).scalar_one_or_none()
        if already:
            continue

        repo.add_relationship(
            source_id=src.id,
            target_id=tgt.id,
            relationship_type=RelationshipType(rel_data["relationship_type"]),
            weight=rel_data.get("weight", 1.0),
            description=rel_data.get("description"),
        )
        rels_created += 1

    session.commit()
    return {"created": created, "skipped": skipped, "relationships": rels_created}
