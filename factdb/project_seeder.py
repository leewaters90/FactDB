"""
Project seeder — loads shared DesignElements and the 10 mechatronics projects.

Idempotency
-----------
- DesignElements are keyed by title: existing ones are skipped.
- Projects are keyed by title: existing ones are skipped.
- Links between projects and elements are keyed by (project_id, element_id):
  existing links are skipped.

Load order
----------
1. Seed DesignElements (require Facts to already exist for fact links).
2. Seed Projects (metadata only).
3. Link Projects → DesignElements.

Requires :func:`factdb.seeder.seed` (or :func:`factdb.device_seeder.seed_devices`)
to have been called first so that the Fact records exist.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from factdb.project_models import ComponentCategory, ProjectStatus
from factdb.project_repository import ProjectRepository
from factdb.project_seed_data import DESIGN_ELEMENTS, MECHATRONICS_PROJECTS


def seed_projects(session: Session, created_by: str = "system-seed") -> dict:
    """
    Populate the database with shared DesignElements and project designs.

    Args:
        session:     Active SQLAlchemy session (caller commits).
        created_by:  Identity used as ``created_by`` on project records.

    Returns:
        Dict with counts: elements_created, elements_skipped,
        projects_created, projects_skipped, links_created.
    """
    repo = ProjectRepository(session)

    elements_created = 0
    elements_skipped = 0

    # ----------------------------------------------------------------
    # 1. Seed all DesignElements
    # ----------------------------------------------------------------
    for edata in DESIGN_ELEMENTS:
        title = edata["title"]
        _, created = repo.get_or_create_design_element(
            title=title,
            selected_approach=edata["selected_approach"],
            component_category=ComponentCategory(edata.get("component_category", "sensing")),
            design_question=edata.get("design_question"),
            rationale=edata.get("rationale"),
            alternatives=edata.get("alternatives"),
            verification_notes=edata.get("verification_notes"),
            supporting_fact_titles=edata.get("supporting_fact_titles", []),
        )
        if created:
            elements_created += 1
        else:
            elements_skipped += 1

    session.flush()

    # ----------------------------------------------------------------
    # 2. Seed Projects + link elements
    # ----------------------------------------------------------------
    projects_created = 0
    projects_skipped = 0
    links_created = 0

    for pdata in MECHATRONICS_PROJECTS:
        ptitle = pdata["title"]

        project = repo.get_project_by_title(ptitle)
        is_new_project = project is None
        if not is_new_project:
            projects_skipped += 1
        else:
            project = repo.create_project(
                title=ptitle,
                description=pdata.get("description", ""),
                objective=pdata.get("objective"),
                constraints=pdata.get("constraints"),
                domain=pdata.get("domain", "systems"),
                status=ProjectStatus(pdata.get("status", "completed")),
                created_by=created_by,
                supporting_fact_titles=pdata.get("supporting_fact_titles", []),
            )
            session.flush()
            projects_created += 1

        # Link design elements (idempotent per element title).
        # Only count links that are truly new (i.e. for newly created projects).
        usage_notes_map: dict = pdata.get("element_usage_notes", {})
        for etitle in pdata.get("design_element_titles", []):
            element = repo.get_design_element_by_title(etitle)
            if element is None:
                continue  # element not seeded — skip silently
            repo.link_element_to_project(
                project_id=project.id,
                element_id=element.id,
                usage_notes=usage_notes_map.get(etitle),
            )
            if is_new_project:
                links_created += 1

        session.flush()

    session.commit()
    return {
        "elements_created": elements_created,
        "elements_skipped": elements_skipped,
        "projects_created": projects_created,
        "projects_skipped": projects_skipped,
        "links_created": links_created,
    }
