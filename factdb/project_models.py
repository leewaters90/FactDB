"""
Project and Design Decision ORM models for FactDB.

Hierarchy:
    Project
    └── DesignDecision  (one project has many decisions)

Both Project and DesignDecision carry many-to-many links to Fact records
so that designs are anchored to the verified fact knowledge base.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
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
    """High-level category of a design decision within a project."""

    POWER = "power"
    SENSING = "sensing"
    ACTUATION = "actuation"
    CONTROL = "control"
    COMMUNICATION = "communication"
    SOFTWARE = "software"
    MECHANICAL = "mechanical"
    PROCESSING = "processing"


# ---------------------------------------------------------------------------
# Association tables
# ---------------------------------------------------------------------------

# Project ↔ Fact  (many-to-many: which facts underpin this project overall)
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

# DesignDecision ↔ Fact  (many-to-many: which facts support this decision)
design_decision_fact_association = Table(
    "design_decision_facts",
    Base.metadata,
    Column(
        "decision_id",
        String(36),
        ForeignKey("design_decisions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "fact_id",
        String(36),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("decision_id", "fact_id", name="uq_decision_fact"),
)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(Base):
    """
    A mechatronics design project.

    Captures the overall goal, constraints, and selected domain, and links
    to the DesignDecision records that describe each component / subsystem
    choice.
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

    # --- Relationships ---
    designs = relationship(
        "DesignDecision",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="DesignDecision.created_at",
    )
    supporting_facts = relationship(
        "Fact",
        secondary=project_fact_association,
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Project title={self.title!r} status={self.status!r}>"

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary."""
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
            "supporting_fact_titles": [f.title for f in self.supporting_facts],
            "designs": [d.to_dict() for d in self.designs],
        }


# ---------------------------------------------------------------------------
# DesignDecision
# ---------------------------------------------------------------------------


class DesignDecision(Base):
    """
    A single component or subsystem design decision within a Project.

    Records the design question, the selected approach with rationale,
    alternative approaches considered (and why they were rejected), and
    links to the Fact records used to verify the decision.
    """

    __tablename__ = "design_decisions"
    __table_args__ = (
        Index("ix_design_decisions_project_category", "project_id", "component_category"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    project_id: str = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Content ---
    title: str = Column(String(300), nullable=False)
    component_category: str = Column(
        Enum(ComponentCategory),
        nullable=False,
        default=ComponentCategory.SENSING,
        index=True,
    )
    design_question: str = Column(Text, nullable=True)
    selected_approach: str = Column(Text, nullable=False)
    rationale: str = Column(Text, nullable=True)

    # Stored as a JSON array of {approach, reason_rejected} objects
    alternatives_json: str = Column(Text, nullable=True)

    verification_notes: str = Column(Text, nullable=True)

    # --- Timestamps ---
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # --- Relationships ---
    project = relationship("Project", back_populates="designs")
    supporting_facts = relationship(
        "Fact",
        secondary=design_decision_fact_association,
        passive_deletes=True,
    )

    # ------------------------------------------------------------------
    # Helpers for the JSON alternatives field
    # ------------------------------------------------------------------

    def set_alternatives(self, alternatives: list[dict[str, str]]) -> None:
        """Store a list of alternative dicts as JSON."""
        self.alternatives_json = json.dumps(alternatives)

    def get_alternatives(self) -> list[dict[str, Any]]:
        """Return the list of alternative approaches (empty list if none)."""
        if not self.alternatives_json:
            return []
        return json.loads(self.alternatives_json)

    def __repr__(self) -> str:
        return (
            f"<DesignDecision project_id={self.project_id!r} "
            f"title={self.title!r} category={self.component_category!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "component_category": self.component_category,
            "design_question": self.design_question,
            "selected_approach": self.selected_approach,
            "rationale": self.rationale,
            "alternatives": self.get_alternatives(),
            "verification_notes": self.verification_notes,
            "supporting_fact_titles": [f.title for f in self.supporting_facts],
        }
