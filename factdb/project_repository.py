"""
Repository layer — CRUD for Project, DesignElement, and their associations.

All methods accept a SQLAlchemy Session; the caller controls transaction
boundaries (call ``session.commit()`` after operations).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import EngineeringDomain, Fact
from factdb.project_models import (
    ComponentCategory,
    DesignElement,
    Project,
    ProjectDesignElement,
    ProjectStatus,
)


class ProjectRepository:
    """
    CRUD + linking operations on Projects, DesignElements, and their
    many-to-many associations.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ==================================================================
    # DesignElement — Create / Read / List
    # ==================================================================

    def create_design_element(
        self,
        title: str,
        selected_approach: str,
        component_category: ComponentCategory = ComponentCategory.SENSING,
        design_question: str | None = None,
        rationale: str | None = None,
        alternatives: list[dict] | None = None,
        verification_notes: str | None = None,
        supporting_fact_titles: List[str] | None = None,
        implementation_code: str | None = None,
    ) -> DesignElement:
        """
        Create a new standalone, reusable DesignElement.

        Args:
            title:                  Unique short title (used as the lookup key).
            selected_approach:      The chosen design approach (required).
            component_category:     Category of the component being designed.
            design_question:        The engineering question being answered.
            rationale:              Why this approach was selected.
            alternatives:           List of ``{approach, reason_rejected}`` dicts.
            verification_notes:     Notes from fact / reasoning verification.
            supporting_fact_titles: Titles of Fact records that back this decision.
            implementation_code:    Python code showing how to call the supporting
                                    software artifacts within this element.

        Returns:
            The new :class:`~factdb.project_models.DesignElement`.
        """
        element = DesignElement(
            title=title,
            selected_approach=selected_approach,
            component_category=component_category,
            design_question=design_question,
            rationale=rationale,
            verification_notes=verification_notes,
            implementation_code=implementation_code,
        )
        if alternatives:
            element.set_alternatives(alternatives)

        self.session.add(element)
        self.session.flush()

        if supporting_fact_titles:
            self._attach_facts_to_element(element, supporting_fact_titles)

        return element

    def get_design_element(self, element_id: str) -> Optional[DesignElement]:
        """Return a DesignElement by primary key, or None."""
        return self.session.get(DesignElement, element_id)

    def get_design_element_by_title(self, title: str) -> Optional[DesignElement]:
        """Return a DesignElement by exact title, or None."""
        return self.session.execute(
            select(DesignElement).where(DesignElement.title == title)
        ).scalar_one_or_none()

    def get_or_create_design_element(
        self, title: str, **kwargs
    ) -> tuple[DesignElement, bool]:
        """
        Return an existing DesignElement by title, or create a new one.

        Returns:
            Tuple of (element, created) where ``created`` is True if the
            element was newly inserted.
        """
        element = self.get_design_element_by_title(title)
        if element is not None:
            return element, False
        element = self.create_design_element(title=title, **kwargs)
        return element, True

    def list_design_elements(
        self,
        component_category: ComponentCategory | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Sequence[DesignElement]:
        """Return DesignElements, optionally filtered by category and/or creation date range."""
        stmt = select(DesignElement)
        if component_category is not None:
            stmt = stmt.where(
                DesignElement.component_category == component_category
            )
        if created_after is not None:
            stmt = stmt.where(DesignElement.created_at >= created_after)
        if created_before is not None:
            stmt = stmt.where(DesignElement.created_at <= created_before)
        stmt = stmt.order_by(DesignElement.component_category, DesignElement.title)
        stmt = stmt.offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def get_projects_using_element(self, element_id: str) -> list[Project]:
        """Return all Projects that include the given DesignElement."""
        stmt = (
            select(Project)
            .join(Project.element_links)
            .where(ProjectDesignElement.element_id == element_id)
            .order_by(Project.title)
        )
        return list(self.session.execute(stmt).scalars().all())

    # ==================================================================
    # Project — Create / Read / List / Update
    # ==================================================================

    def create_project(
        self,
        title: str,
        description: str,
        objective: str | None = None,
        constraints: str | None = None,
        domain: str = "systems",
        status: ProjectStatus = ProjectStatus.CONCEPT,
        created_by: str | None = None,
        supporting_fact_titles: List[str] | None = None,
        integration_code: str | None = None,
        element_interactions: list[dict] | None = None,
    ) -> Project:
        """
        Create a new Project record (without design elements).

        Use :meth:`link_element_to_project` to attach elements after creation.

        Args:
            title:                   Unique short title.
            description:             Full description.
            objective:               Primary engineering objective.
            constraints:             Design constraints.
            domain:                  Engineering domain string or enum value.
            status:                  Initial lifecycle status.
            created_by:              Author identity.
            supporting_fact_titles:  Project-level fact references.
            integration_code:        Python source that orchestrates all design
                                     elements into a complete working program.
            element_interactions:    List of ``{from, to, data}`` dicts
                                     describing data flow between elements.

        Returns:
            The new :class:`~factdb.project_models.Project`.
        """
        project = Project(
            title=title,
            description=description,
            objective=objective,
            constraints=constraints,
            domain=EngineeringDomain(domain),
            status=status,
            created_by=created_by,
            integration_code=integration_code,
        )
        if element_interactions:
            project.set_element_interactions(element_interactions)
        self.session.add(project)
        self.session.flush()

        if supporting_fact_titles:
            self._attach_facts_to_project(project, supporting_fact_titles)

        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Return a Project by primary key, or None."""
        return self.session.get(Project, project_id)

    def get_project_by_title(self, title: str) -> Optional[Project]:
        """Return a Project by exact title, or None."""
        return self.session.execute(
            select(Project).where(Project.title == title)
        ).scalar_one_or_none()

    def list_projects(
        self,
        status: ProjectStatus | None = None,
        domain: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Project]:
        """Return projects filtered by status, domain, and/or creation date range."""
        stmt = select(Project)
        if status is not None:
            stmt = stmt.where(Project.status == status)
        if domain is not None:
            stmt = stmt.where(Project.domain == domain)
        if created_after is not None:
            stmt = stmt.where(Project.created_at >= created_after)
        if created_before is not None:
            stmt = stmt.where(Project.created_at <= created_before)
        stmt = stmt.order_by(Project.created_at).offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def update_project(self, project_id: str, **fields) -> Project:
        """
        Update mutable fields on a Project.

        Supported keyword fields: title, description, objective, constraints,
        domain, status, supporting_fact_titles.

        Raises:
            ValueError: if the project is not found.
        """
        project = self.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id!r}")

        for key in ("title", "description", "objective", "constraints", "integration_code"):
            if key in fields:
                setattr(project, key, fields[key])

        if "status" in fields:
            project.status = ProjectStatus(fields["status"])
        if "domain" in fields:
            project.domain = EngineeringDomain(fields["domain"])
        if "supporting_fact_titles" in fields:
            project.supporting_facts.clear()
            self._attach_facts_to_project(project, fields["supporting_fact_titles"])
        if "element_interactions" in fields:
            project.set_element_interactions(fields["element_interactions"])

        self.session.flush()
        return project

    # ==================================================================
    # Project ↔ DesignElement association
    # ==================================================================

    def link_element_to_project(
        self,
        project_id: str,
        element_id: str,
        usage_notes: str | None = None,
    ) -> ProjectDesignElement:
        """
        Link a DesignElement to a Project, optionally with project-specific
        ``usage_notes``.

        Idempotent: if the link already exists, it is returned unchanged
        (usage_notes is not overwritten).

        Args:
            project_id:   PK of the Project.
            element_id:   PK of the DesignElement.
            usage_notes:  Optional project-specific context.

        Returns:
            The :class:`~factdb.project_models.ProjectDesignElement` link.

        Raises:
            ValueError: if either record is not found.
        """
        if self.get_project(project_id) is None:
            raise ValueError(f"Project not found: {project_id!r}")
        if self.get_design_element(element_id) is None:
            raise ValueError(f"DesignElement not found: {element_id!r}")

        # Check for existing link
        existing = self.session.execute(
            select(ProjectDesignElement).where(
                ProjectDesignElement.project_id == project_id,
                ProjectDesignElement.element_id == element_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        link = ProjectDesignElement(
            project_id=project_id,
            element_id=element_id,
            usage_notes=usage_notes,
        )
        self.session.add(link)
        self.session.flush()
        return link

    def unlink_element_from_project(
        self, project_id: str, element_id: str
    ) -> None:
        """Remove the link between a project and a design element (if it exists)."""
        link = self.session.execute(
            select(ProjectDesignElement).where(
                ProjectDesignElement.project_id == project_id,
                ProjectDesignElement.element_id == element_id,
            )
        ).scalar_one_or_none()
        if link is not None:
            self.session.delete(link)
            self.session.flush()

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _resolve_facts(self, titles: List[str]) -> list[Fact]:
        facts = []
        for title in titles:
            fact = self.session.execute(
                select(Fact).where(Fact.title == title)
            ).scalar_one_or_none()
            if fact is not None:
                facts.append(fact)
        return facts

    def _attach_facts_to_project(
        self, project: Project, titles: List[str]
    ) -> None:
        for fact in self._resolve_facts(titles):
            if fact not in project.supporting_facts:
                project.supporting_facts.append(fact)
        self.session.flush()

    def _attach_facts_to_element(
        self, element: DesignElement, titles: List[str]
    ) -> None:
        for fact in self._resolve_facts(titles):
            if fact not in element.supporting_facts:
                element.supporting_facts.append(fact)
        self.session.flush()
