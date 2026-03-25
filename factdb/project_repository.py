"""
Repository layer — CRUD operations for Project and DesignDecision.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import Fact
from factdb.project_models import (
    ComponentCategory,
    DesignDecision,
    Project,
    ProjectStatus,
)


class ProjectRepository:
    """
    CRUD operations on :class:`~factdb.project_models.Project` and
    :class:`~factdb.project_models.DesignDecision`.

    The caller controls transaction boundaries (call ``session.commit()``
    after operations).
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Project — Create
    # ------------------------------------------------------------------

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
    ) -> Project:
        """
        Create a new Project record.

        Args:
            title:                   Unique short title.
            description:             Full description of the project.
            objective:               Primary engineering objective.
            constraints:             Design constraints (budget, size, power…).
            domain:                  Engineering domain string or enum value.
            status:                  Initial lifecycle status.
            created_by:              Author identity.
            supporting_fact_titles:  Titles of facts that underpin the project.

        Returns:
            The newly created :class:`~factdb.project_models.Project` instance.
        """
        from factdb.models import EngineeringDomain

        project = Project(
            title=title,
            description=description,
            objective=objective,
            constraints=constraints,
            domain=EngineeringDomain(domain),
            status=status,
            created_by=created_by,
        )
        self.session.add(project)
        self.session.flush()

        if supporting_fact_titles:
            self._attach_facts_to_project(project, supporting_fact_titles)

        return project

    # ------------------------------------------------------------------
    # Project — Read
    # ------------------------------------------------------------------

    def get_project(self, project_id: str) -> Optional[Project]:
        """Return a Project by primary key, or None."""
        return self.session.get(Project, project_id)

    def get_project_by_title(self, title: str) -> Optional[Project]:
        """Return a Project by title, or None."""
        return self.session.execute(
            select(Project).where(Project.title == title)
        ).scalar_one_or_none()

    def list_projects(
        self,
        status: ProjectStatus | None = None,
        domain: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Project]:
        """Return filtered projects ordered by creation time."""
        stmt = select(Project)
        if status is not None:
            stmt = stmt.where(Project.status == status)
        if domain is not None:
            stmt = stmt.where(Project.domain == domain)
        stmt = stmt.order_by(Project.created_at).offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Project — Update
    # ------------------------------------------------------------------

    def update_project(
        self, project_id: str, **fields
    ) -> Project:
        """
        Update mutable fields on an existing Project.

        Supported keyword arguments: title, description, objective,
        constraints, domain, status, supporting_fact_titles.

        Raises:
            ValueError: If the project is not found.
        """
        project = self.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id!r}")

        for key in ("title", "description", "objective", "constraints"):
            if key in fields:
                setattr(project, key, fields[key])

        if "status" in fields:
            project.status = ProjectStatus(fields["status"])

        if "domain" in fields:
            from factdb.models import EngineeringDomain
            project.domain = EngineeringDomain(fields["domain"])

        if "supporting_fact_titles" in fields:
            project.supporting_facts.clear()
            self._attach_facts_to_project(project, fields["supporting_fact_titles"])

        self.session.flush()
        return project

    # ------------------------------------------------------------------
    # DesignDecision — Create
    # ------------------------------------------------------------------

    def add_design_decision(
        self,
        project_id: str,
        title: str,
        selected_approach: str,
        component_category: ComponentCategory = ComponentCategory.SENSING,
        design_question: str | None = None,
        rationale: str | None = None,
        alternatives: list[dict] | None = None,
        verification_notes: str | None = None,
        supporting_fact_titles: List[str] | None = None,
    ) -> DesignDecision:
        """
        Add a design decision to a project.

        Args:
            project_id:            PK of the owning project.
            title:                 Short title of the decision.
            selected_approach:     The chosen design approach.
            component_category:    Category of the component being designed.
            design_question:       The question being answered.
            rationale:             Why this approach was chosen.
            alternatives:          List of ``{approach, reason_rejected}`` dicts.
            verification_notes:    Notes from fact / reasoning verification.
            supporting_fact_titles: Titles of facts supporting this decision.

        Returns:
            The new :class:`~factdb.project_models.DesignDecision` instance.

        Raises:
            ValueError: If the project is not found.
        """
        if self.get_project(project_id) is None:
            raise ValueError(f"Project not found: {project_id!r}")

        decision = DesignDecision(
            project_id=project_id,
            title=title,
            selected_approach=selected_approach,
            component_category=component_category,
            design_question=design_question,
            rationale=rationale,
            verification_notes=verification_notes,
        )
        if alternatives:
            decision.set_alternatives(alternatives)

        self.session.add(decision)
        self.session.flush()

        if supporting_fact_titles:
            self._attach_facts_to_decision(decision, supporting_fact_titles)

        return decision

    # ------------------------------------------------------------------
    # DesignDecision — Read
    # ------------------------------------------------------------------

    def get_decision(self, decision_id: str) -> Optional[DesignDecision]:
        """Return a DesignDecision by primary key, or None."""
        return self.session.get(DesignDecision, decision_id)

    def list_decisions(
        self,
        project_id: str,
        component_category: ComponentCategory | None = None,
    ) -> Sequence[DesignDecision]:
        """Return design decisions for a project, optionally filtered by category."""
        stmt = select(DesignDecision).where(
            DesignDecision.project_id == project_id
        )
        if component_category is not None:
            stmt = stmt.where(
                DesignDecision.component_category == component_category
            )
        stmt = stmt.order_by(DesignDecision.created_at)
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_facts(self, titles: List[str]) -> list[Fact]:
        """Resolve fact titles to Fact instances (silently skips missing)."""
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

    def _attach_facts_to_decision(
        self, decision: DesignDecision, titles: List[str]
    ) -> None:
        for fact in self._resolve_facts(titles):
            if fact not in decision.supporting_facts:
                decision.supporting_facts.append(fact)
        self.session.flush()
