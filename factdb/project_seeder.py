"""
Project seeder — loads the 10 mechatronics project designs into the database.

Idempotent: projects whose titles already exist in the database are skipped.
Also seeds the device-domain facts (seed_data_devices) before seeding projects,
so that project-to-fact links can be resolved.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from factdb.project_models import ComponentCategory, ProjectStatus
from factdb.project_repository import ProjectRepository
from factdb.project_seed_data import MECHATRONICS_PROJECTS


def seed_projects(session: Session, created_by: str = "system-seed") -> dict:
    """
    Populate the database with the 10 mechatronics project designs.

    Must be called after :func:`factdb.seeder.seed` (or equivalent) so that
    the Fact records referenced by fact title already exist.

    Args:
        session:     Active SQLAlchemy session.
        created_by:  Identity used as the ``created_by`` field.

    Returns:
        Dictionary with ``created`` and ``skipped`` project counts, and
        ``decisions`` (total design decisions created).
    """
    repo = ProjectRepository(session)

    created = 0
    skipped = 0
    decisions_created = 0

    for pdata in MECHATRONICS_PROJECTS:
        title = pdata["title"]

        # Idempotency check
        if repo.get_project_by_title(title) is not None:
            skipped += 1
            continue

        project = repo.create_project(
            title=title,
            description=pdata.get("description", ""),
            objective=pdata.get("objective"),
            constraints=pdata.get("constraints"),
            domain=pdata.get("domain", "systems"),
            status=ProjectStatus(pdata.get("status", "completed")),
            created_by=created_by,
            supporting_fact_titles=pdata.get("supporting_fact_titles", []),
        )
        session.flush()
        created += 1

        for ddata in pdata.get("designs", []):
            cat_str = ddata.get("component_category", "sensing")
            category = ComponentCategory(cat_str)

            repo.add_design_decision(
                project_id=project.id,
                title=ddata["title"],
                selected_approach=ddata["selected_approach"],
                component_category=category,
                design_question=ddata.get("design_question"),
                rationale=ddata.get("rationale"),
                alternatives=ddata.get("alternatives"),
                verification_notes=ddata.get("verification_notes"),
                supporting_fact_titles=ddata.get("supporting_fact_titles", []),
            )
            decisions_created += 1

        session.flush()

    session.commit()
    return {
        "created": created,
        "skipped": skipped,
        "decisions": decisions_created,
    }
