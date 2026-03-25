"""
Data models for FactDB.

Hierarchy:
    EngineeringDomain → Category → Subcategory → Fact
    Fact has: DetailLevel, FactStatus, Tags, Relationships, Versions, Verifications
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EngineeringDomain(str, PyEnum):
    """Top-level engineering disciplines."""

    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    CIVIL = "civil"
    SOFTWARE = "software"
    CHEMICAL = "chemical"
    AEROSPACE = "aerospace"
    MATERIALS = "materials"
    SYSTEMS = "systems"
    GENERAL = "general"


class DetailLevel(str, PyEnum):
    """Granularity / depth of a fact — supports layered retrieval."""

    FUNDAMENTAL = "fundamental"   # Basic principles, suitable for any audience
    INTERMEDIATE = "intermediate"  # Requires domain background
    ADVANCED = "advanced"          # Specialist knowledge
    EXPERT = "expert"              # Cutting-edge / research-level


class FactStatus(str, PyEnum):
    """Lifecycle status of a fact record."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"


class VerificationStatus(str, PyEnum):
    """Outcome of a single verification attempt."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class RelationshipType(str, PyEnum):
    """Semantic relationships between facts (used by the reasoning engine)."""

    DEPENDS_ON = "depends_on"        # B requires A to be true / applicable
    SUPPORTS = "supports"            # A provides evidence for B
    CONTRADICTS = "contradicts"      # A and B cannot both be true
    DERIVED_FROM = "derived_from"    # B is derived / calculated from A
    PREREQUISITE = "prerequisite"    # Must know A before B makes sense
    EXAMPLE_OF = "example_of"        # B is a concrete example of A
    GENERALISES = "generalises"      # A is a generalisation of B


# ---------------------------------------------------------------------------
# ORM Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Association table: Fact ↔ Tag  (many-to-many)
# ---------------------------------------------------------------------------

fact_tag_association = Table(
    "fact_tag",
    Base.metadata,
    Column("fact_id", String(36), ForeignKey("facts.id", ondelete="CASCADE")),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE")),
)


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------


class Tag(Base):
    """Keyword label that can be attached to any number of facts."""

    __tablename__ = "tags"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    name: str = Column(String(100), nullable=False, unique=True, index=True)
    description: str = Column(Text, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    facts = relationship(
        "Fact",
        secondary=fact_tag_association,
        back_populates="tags",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Tag name={self.name!r}>"


# ---------------------------------------------------------------------------
# Fact
# ---------------------------------------------------------------------------


class Fact(Base):
    """
    Core entity: a single, discrete engineering fact.

    Layers of detail are expressed through *detail_level* and the optional
    *extended_content* field that supplements the concise *content*.
    """

    __tablename__ = "facts"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)

    # --- Identity / Classification ---
    title: str = Column(String(300), nullable=False, index=True)
    domain: str = Column(
        Enum(EngineeringDomain),
        nullable=False,
        default=EngineeringDomain.GENERAL,
        index=True,
    )
    category: str = Column(String(150), nullable=True, index=True)
    subcategory: str = Column(String(150), nullable=True, index=True)
    detail_level: str = Column(
        Enum(DetailLevel),
        nullable=False,
        default=DetailLevel.FUNDAMENTAL,
        index=True,
    )

    # --- Content ---
    content: str = Column(Text, nullable=False)           # Concise statement of the fact
    extended_content: str = Column(Text, nullable=True)   # Deeper explanation / derivation
    formula: str = Column(Text, nullable=True)            # Mathematical / code expression
    units: str = Column(String(100), nullable=True)       # SI / other units where applicable

    # --- Provenance ---
    source: str = Column(String(500), nullable=True)      # Reference / citation
    source_url: str = Column(String(1000), nullable=True)
    confidence_score: float = Column(Float, nullable=False, default=1.0)

    # --- Lifecycle ---
    status: str = Column(
        Enum(FactStatus),
        nullable=False,
        default=FactStatus.DRAFT,
        index=True,
    )
    version: int = Column(Integer, nullable=False, default=1)
    is_active: bool = Column(Boolean, nullable=False, default=True)

    # --- Timestamps / Authorship ---
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    created_by: str = Column(String(200), nullable=True)
    updated_by: str = Column(String(200), nullable=True)

    # --- Relationships ---
    tags = relationship(
        "Tag",
        secondary=fact_tag_association,
        back_populates="facts",
        passive_deletes=True,
    )
    versions = relationship(
        "FactVersion",
        back_populates="fact",
        cascade="all, delete-orphan",
        order_by="FactVersion.version",
    )
    verifications = relationship(
        "FactVerification",
        back_populates="fact",
        cascade="all, delete-orphan",
        order_by="FactVerification.verified_at.desc()",
    )
    outgoing_relationships = relationship(
        "FactRelationship",
        foreign_keys="FactRelationship.source_fact_id",
        back_populates="source_fact",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "FactRelationship",
        foreign_keys="FactRelationship.target_fact_id",
        back_populates="target_fact",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Fact id={self.id!r} title={self.title!r} status={self.status!r}>"

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary (useful for JSON export / AI ingestion)."""
        return {
            "id": self.id,
            "title": self.title,
            "domain": self.domain,
            "category": self.category,
            "subcategory": self.subcategory,
            "detail_level": self.detail_level,
            "content": self.content,
            "extended_content": self.extended_content,
            "formula": self.formula,
            "units": self.units,
            "source": self.source,
            "source_url": self.source_url,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "version": self.version,
            "tags": [t.name for t in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


# ---------------------------------------------------------------------------
# FactVersion  (change management / audit trail)
# ---------------------------------------------------------------------------


class FactVersion(Base):
    """
    Immutable snapshot of a Fact at a specific version number.
    Every edit to a Fact produces a new FactVersion row.
    """

    __tablename__ = "fact_versions"
    __table_args__ = (
        UniqueConstraint("fact_id", "version", name="uq_fact_version"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    fact_id: str = Column(
        String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: int = Column(Integer, nullable=False)

    # Snapshot fields (mirror of Fact)
    title: str = Column(String(300), nullable=False)
    content: str = Column(Text, nullable=False)
    extended_content: str = Column(Text, nullable=True)
    formula: str = Column(Text, nullable=True)
    detail_level: str = Column(Enum(DetailLevel), nullable=False)
    status: str = Column(Enum(FactStatus), nullable=False)
    confidence_score: float = Column(Float, nullable=False)

    # Change metadata
    changed_by: str = Column(String(200), nullable=True)
    change_reason: str = Column(Text, nullable=True)
    changed_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    fact = relationship("Fact", back_populates="versions")

    def __repr__(self) -> str:
        return f"<FactVersion fact_id={self.fact_id!r} v={self.version}>"


# ---------------------------------------------------------------------------
# FactVerification
# ---------------------------------------------------------------------------


class FactVerification(Base):
    """
    Records a single verification event for a fact.
    A fact is considered *verified* once at least one approved verification
    exists and no subsequent rejection is pending.
    """

    __tablename__ = "fact_verifications"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    fact_id: str = Column(
        String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    verified_by: str = Column(String(200), nullable=False)
    verification_status: str = Column(
        Enum(VerificationStatus), nullable=False, default=VerificationStatus.APPROVED
    )
    notes: str = Column(Text, nullable=True)
    fact_version_at_verification: int = Column(Integer, nullable=True)
    verified_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    fact = relationship("Fact", back_populates="verifications")

    def __repr__(self) -> str:
        return (
            f"<FactVerification fact_id={self.fact_id!r} "
            f"status={self.verification_status!r} by={self.verified_by!r}>"
        )


# ---------------------------------------------------------------------------
# FactRelationship
# ---------------------------------------------------------------------------


class FactRelationship(Base):
    """
    Directed edge between two facts.
    Forms the graph used by the reasoning engine (decision trees / expert
    system rules).
    """

    __tablename__ = "fact_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_fact_id", "target_fact_id", "relationship_type",
            name="uq_fact_relationship",
        ),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    source_fact_id: str = Column(
        String(36),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_fact_id: str = Column(
        String(36),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: str = Column(
        Enum(RelationshipType), nullable=False, index=True
    )
    weight: float = Column(Float, nullable=False, default=1.0)
    description: str = Column(Text, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    source_fact = relationship(
        "Fact",
        foreign_keys=[source_fact_id],
        back_populates="outgoing_relationships",
    )
    target_fact = relationship(
        "Fact",
        foreign_keys=[target_fact_id],
        back_populates="incoming_relationships",
    )

    def __repr__(self) -> str:
        return (
            f"<FactRelationship {self.source_fact_id!r} "
            f"--[{self.relationship_type}]--> {self.target_fact_id!r}>"
        )
