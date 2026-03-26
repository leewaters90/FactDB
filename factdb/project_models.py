"""
Project and DesignElement ORM models for FactDB.

Architecture
------------
DesignElement
    A reusable, standalone component or subsystem design decision.
    One DesignElement can appear in many Projects (many-to-many).

ProjectDesignElement  (association object)
    Joins Project ↔ DesignElement and carries optional ``usage_notes``
    describing how this particular project uses the element.

Project
    A mechatronics design project composed of DesignElements.

Both Project and DesignElement carry many-to-many links to Fact records
so every design choice is anchored to the verified fact knowledge base.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from factdb.models import Base, EngineeringDomain, _new_uuid, _utcnow


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProjectStatus(str, PyEnum):
    """Lifecycle status of a mechatronics project."""

    CONCEPT = "concept"
    IN_DESIGN = "in_design"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    DEPRECATED = "deprecated"


class ComponentCategory(str, PyEnum):
    """High-level category of a design element."""

    POWER = "power"
    SENSING = "sensing"
    ACTUATION = "actuation"
    CONTROL = "control"
    COMMUNICATION = "communication"
    SOFTWARE = "software"
    MECHANICAL = "mechanical"
    PROCESSING = "processing"


# ---------------------------------------------------------------------------
# Association: Project ↔ Fact  (many-to-many)
# ---------------------------------------------------------------------------

project_fact_association = Table(
    "project_facts",
    Base.metadata,
    Column(
        "project_id",
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "fact_id",
        String(36),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("project_id", "fact_id", name="uq_project_fact"),
)

# ---------------------------------------------------------------------------
# Association: DesignElement ↔ Fact  (many-to-many)
# ---------------------------------------------------------------------------

design_element_fact_association = Table(
    "design_element_facts",
    Base.metadata,
    Column(
        "element_id",
        String(36),
        ForeignKey("design_elements.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "fact_id",
        String(36),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("element_id", "fact_id", name="uq_element_fact"),
)


# ---------------------------------------------------------------------------
# DesignElement — reusable, shared across projects
# ---------------------------------------------------------------------------


class DesignElement(Base):
    """
    A reusable design element (component/subsystem design decision).

    DesignElements are *shared* — the same element (e.g.
    "ESP32 WiFi + MQTT Telemetry") can be linked to many Projects.
    Project-specific context is stored in the :class:`ProjectDesignElement`
    association object rather than here.
    """

    __tablename__ = "design_elements"
    __table_args__ = (
        Index("ix_design_elements_category", "component_category"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)

    # --- Identity ---
    title: str = Column(String(300), nullable=False, unique=True, index=True)
    component_category: str = Column(
        Enum(ComponentCategory),
        nullable=False,
        default=ComponentCategory.SENSING,
        index=True,
    )

    # --- Design content ---
    design_question: str = Column(Text, nullable=True)
    selected_approach: str = Column(Text, nullable=False)
    rationale: str = Column(Text, nullable=True)
    alternatives_json: str = Column(Text, nullable=True)   # JSON array of {approach, reason_rejected}
    verification_notes: str = Column(Text, nullable=True)
    implementation_code: str = Column(Text, nullable=True)  # Python/pseudocode using the supporting artifacts

    # --- Timestamps ---
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # --- Relationships ---
    project_links = relationship(
        "ProjectDesignElement",
        back_populates="element",
        cascade="all, delete-orphan",
    )
    supporting_facts = relationship(
        "Fact",
        secondary=design_element_fact_association,
        passive_deletes=True,
    )

    # ------------------------------------------------------------------
    # Helpers for the JSON alternatives field
    # ------------------------------------------------------------------

    def set_alternatives(self, alternatives: list[dict[str, str]]) -> None:
        """Store a list of alternative dicts as JSON."""
        self.alternatives_json = json.dumps(alternatives, ensure_ascii=False)

    def get_alternatives(self) -> list[dict[str, Any]]:
        """Return the list of alternative approaches (empty list if none)."""
        if not self.alternatives_json:
            return []
        return json.loads(self.alternatives_json)

    @property
    def projects(self) -> list["Project"]:
        """Return all Projects that use this element."""
        return [link.project for link in self.project_links]

    def __repr__(self) -> str:
        return (
            f"<DesignElement title={self.title!r} "
            f"category={self.component_category!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "component_category": self.component_category,
            "design_question": self.design_question,
            "selected_approach": self.selected_approach,
            "rationale": self.rationale,
            "alternatives": self.get_alternatives(),
            "verification_notes": self.verification_notes,
            "implementation_code": self.implementation_code,
            "supporting_fact_titles": [f.title for f in self.supporting_facts],
            "used_in_projects": [link.project.title for link in self.project_links],
        }


# ---------------------------------------------------------------------------
# ProjectDesignElement — association object (carries usage_notes)
# ---------------------------------------------------------------------------


class ProjectDesignElement(Base):
    """
    Association between a Project and a DesignElement.

    ``usage_notes`` records how *this project* uses the shared element —
    e.g. a variant component value, a project-specific trade-off note, or
    an integration detail not captured in the element's generic description.
    """

    __tablename__ = "project_design_elements"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "element_id", name="uq_project_design_element"
        ),
        Index("ix_pde_project_id", "project_id"),
        Index("ix_pde_element_id", "element_id"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    project_id: str = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    element_id: str = Column(
        String(36),
        ForeignKey("design_elements.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage_notes: str = Column(Text, nullable=True)

    project = relationship("Project", back_populates="element_links")
    element = relationship("DesignElement", back_populates="project_links")

    def __repr__(self) -> str:
        return (
            f"<ProjectDesignElement project={self.project_id!r} "
            f"element={self.element_id!r}>"
        )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(Base):
    """
    A mechatronics design project.

    Composed of zero or more :class:`DesignElement` records (many-to-many),
    accessed through :class:`ProjectDesignElement` association objects.
    Each element in the composition may carry project-specific
    ``usage_notes``.
    """

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_status_domain", "status", "domain"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)

    # --- Identity ---
    title: str = Column(String(300), nullable=False, index=True, unique=True)
    description: str = Column(Text, nullable=False)
    objective: str = Column(Text, nullable=True)
    constraints: str = Column(Text, nullable=True)

    # --- Classification ---
    domain: str = Column(
        Enum(EngineeringDomain),
        nullable=False,
        default=EngineeringDomain.SYSTEMS,
        index=True,
    )
    status: str = Column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.CONCEPT,
        index=True,
    )

    # --- Timestamps / Authorship ---
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    created_by: str = Column(String(200), nullable=True)

    # --- Integration code ---
    # Python source that orchestrates the design elements into a working whole.
    integration_code: str = Column(Text, nullable=True)
    # JSON array of {from, to, data} describing inter-element data flow.
    element_interactions_json: str = Column(Text, nullable=True)

    # --- Relationships ---
    element_links = relationship(
        "ProjectDesignElement",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectDesignElement.id",
    )
    supporting_facts = relationship(
        "Fact",
        secondary=project_fact_association,
        passive_deletes=True,
    )

    @property
    def elements(self) -> list[DesignElement]:
        """Return all DesignElements used by this project (ordered by link id)."""
        return [link.element for link in self.element_links]

    def set_element_interactions(self, interactions: list[dict]) -> None:
        """Store inter-element data-flow descriptions as JSON."""
        self.element_interactions_json = json.dumps(interactions, ensure_ascii=False)

    def get_element_interactions(self) -> list[dict]:
        """Return inter-element data-flow descriptions (empty list if none)."""
        if not self.element_interactions_json:
            return []
        return json.loads(self.element_interactions_json)

    def __repr__(self) -> str:
        return f"<Project title={self.title!r} status={self.status!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "objective": self.objective,
            "constraints": self.constraints,
            "domain": self.domain,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "integration_code": self.integration_code,
            "element_interactions": self.get_element_interactions(),
            "supporting_fact_titles": [f.title for f in self.supporting_facts],
            "design_elements": [
                {
                    "title": link.element.title,
                    "category": link.element.component_category,
                    "usage_notes": link.usage_notes,
                }
                for link in self.element_links
            ],
        }
