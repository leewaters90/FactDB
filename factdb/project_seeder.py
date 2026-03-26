"""
Project seeder — loads shared DesignElements and mechatronics projects from
the JSON folder tree.

Data sources
------------
- Design elements: ``data/projects/design-elements/*.json``
- Projects:        ``data/projects/projects/*.json``

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

Requires :func:`factdb.seeder.seed` to have been called first so that the
Fact records referenced by ``supporting_fact_titles`` exist in the database.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from factdb.project_models import ComponentCategory, ProjectStatus
from factdb.project_repository import ProjectRepository

# Root directory for project JSON data.
_PROJECTS_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "data" / "projects"


def _load_json_dir(directory: Path) -> list[dict]:
    """Return all JSON objects found in *directory* (non-recursive)."""
    if not directory.exists():
        return []
    results = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return results


def seed_projects(session: Session, created_by: str = "system-seed") -> dict:
    """
    Populate the database with shared DesignElements and project designs.

    Reads design element data from ``data/projects/design-elements/*.json``
    and project data from ``data/projects/projects/*.json``.

    Args:
        session:     Active SQLAlchemy session (caller commits).
        created_by:  Identity used as ``created_by`` on project records.

    Returns:
        Dict with counts: elements_created, elements_skipped,
        projects_created, projects_skipped, links_created.
    """
    repo = ProjectRepository(session)

    design_elements = _load_json_dir(_PROJECTS_DIR / "design-elements")
    mechatronics_projects = _load_json_dir(_PROJECTS_DIR / "projects")

    elements_created = 0
    elements_skipped = 0

    # ----------------------------------------------------------------
    # 1. Seed all DesignElements
    # ----------------------------------------------------------------
    for edata in design_elements:
        title = edata.get("title", "")
        if not title:
            continue
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

    for pdata in mechatronics_projects:
        ptitle = pdata.get("title", "")
        if not ptitle:
            continue

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
        usage_notes_map: dict = pdata.get("element_usage_notes", {})
        for etitle in pdata.get("design_element_titles", []):
            element = repo.get_design_element_by_title(etitle)
            if element is None:
                continue
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
