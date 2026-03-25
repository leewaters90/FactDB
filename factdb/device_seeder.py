"""
Device seeder — populates the database with device-design engineering facts.

Seeds facts from ``seed_data_devices.py`` (weather station, robot vacuum,
and shared mechatronics project facts).  Idempotent.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    Fact,
    FactRelationship,
    FactStatus,
    RelationshipType,
)
from factdb.repository import FactRepository
from factdb.seed_data_devices import DEVICE_FACTS, DEVICE_FACT_RELATIONSHIPS
from factdb.verification import VerificationWorkflow


def seed_devices(session: Session, verified_by: str = "system-seed") -> dict:
    """
    Populate the database with device-design engineering facts.

    Idempotent: facts whose titles already exist in the database are skipped.

    Args:
        session:     Active SQLAlchemy session.
        verified_by: Identity used for the auto-verification step.

    Returns:
        Dict with ``created``, ``skipped``, and ``relationships`` counts.
    """
    repo = FactRepository(session)
    workflow = VerificationWorkflow(session)

    existing: dict[str, Fact] = {
        f.title: f
        for f in session.execute(select(Fact)).scalars().all()
    }

    created = 0
    skipped = 0

    for data in DEVICE_FACTS:
        title = data["title"]
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
            confidence_score=data.get("confidence_score", 1.0),
            status=FactStatus.DRAFT,
            tags=data.get("tags", []),
            created_by=verified_by,
        )
        existing[title] = fact

        workflow.submit_for_review(fact.id, submitted_by=verified_by)
        workflow.approve(
            fact.id,
            verified_by=verified_by,
            notes="Device seed data — auto-approved",
        )
        session.flush()
        created += 1

    # Seed relationships
    rels_created = 0
    for rel_data in DEVICE_FACT_RELATIONSHIPS:
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
