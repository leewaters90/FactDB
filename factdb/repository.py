"""
Repository layer — CRUD operations for facts and related entities.

All public methods accept a SQLAlchemy Session so the caller controls
transaction boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    Fact,
    FactRelationship,
    FactStatus,
    FactUsageLog,
    FactVersion,
    RelationshipType,
    Tag,
)


# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------


def get_or_create_tag(session: Session, name: str, description: str = "") -> Tag:
    """Return an existing Tag or create a new one."""
    tag = session.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if tag is None:
        tag = Tag(name=name, description=description)
        session.add(tag)
        session.flush()
    return tag


# ---------------------------------------------------------------------------
# FactRepository
# ---------------------------------------------------------------------------


class FactRepository:
    """
    CRUD + versioning operations on :class:`~factdb.models.Fact` objects.

    All methods require an active *session* to be passed in.  The session is
    **not** committed inside this class — the caller is responsible for
    calling ``session.commit()`` (or letting the ``get_session`` context
    manager do so automatically).
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        title: str,
        content: str,
        domain: EngineeringDomain = EngineeringDomain.GENERAL,
        category: str | None = None,
        subcategory: str | None = None,
        detail_level: DetailLevel = DetailLevel.FUNDAMENTAL,
        extended_content: str | None = None,
        formula: str | None = None,
        units: str | None = None,
        source: str | None = None,
        source_url: str | None = None,
        confidence_score: float = 1.0,
        status: FactStatus = FactStatus.DRAFT,
        tags: List[str] | None = None,
        created_by: str | None = None,
    ) -> Fact:
        """
        Create and persist a new Fact, recording version 1 automatically.

        Args:
            title:             Short descriptive title of the fact.
            content:           The concise fact statement.
            domain:            Engineering discipline.
            category:          Sub-domain (e.g. ``"thermodynamics"``).
            subcategory:       Further subdivision (e.g. ``"heat transfer"``).
            detail_level:      Depth of the fact.
            extended_content:  Longer explanation / derivation (optional).
            formula:           Mathematical or code expression (optional).
            units:             Applicable units (optional).
            source:            Bibliographic reference (optional).
            source_url:        URL to the source (optional).
            confidence_score:  0.0–1.0; defaults to 1.0 (fully confident).
            status:            Initial lifecycle status; defaults to DRAFT.
            tags:              List of tag name strings to attach.
            created_by:        Identity of the author.

        Returns:
            The newly created :class:`~factdb.models.Fact` instance.
        """
        fact = Fact(
            title=title,
            content=content,
            domain=domain,
            category=category,
            subcategory=subcategory,
            detail_level=detail_level,
            extended_content=extended_content,
            formula=formula,
            units=units,
            source=source,
            source_url=source_url,
            confidence_score=confidence_score,
            status=status,
            version=1,
            created_by=created_by,
            updated_by=created_by,
        )

        self.session.add(fact)
        self.session.flush()  # get fact.id before adding tags or versions

        if tags:
            fact.tags.clear()
            for tag_name in tags:
                fact.tags.append(get_or_create_tag(self.session, tag_name.strip()))
            self.session.flush()

        # Record initial version
        self._snapshot_version(fact, changed_by=created_by, change_reason="Initial creation")

        return fact

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, fact_id: str) -> Optional[Fact]:
        """Return a Fact by primary key, or None if not found."""
        return self.session.get(Fact, fact_id)

    def list_all(
        self,
        domain: EngineeringDomain | None = None,
        status: FactStatus | None = None,
        detail_level: DetailLevel | None = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Fact]:
        """
        Return a filtered list of facts.

        Args:
            domain:       Filter by engineering domain.
            status:       Filter by lifecycle status.
            detail_level: Filter by detail level.
            is_active:    If True (default) return only active (non-deleted) facts.
            limit:        Maximum number of records to return (default 100).
            offset:       Number of records to skip for pagination (default 0).

        Returns:
            Sequence of matching :class:`~factdb.models.Fact` objects.
        """
        stmt = select(Fact)
        if is_active is not None:
            stmt = stmt.where(Fact.is_active == is_active)
        if domain is not None:
            stmt = stmt.where(Fact.domain == domain)
        if status is not None:
            stmt = stmt.where(Fact.status == status)
        if detail_level is not None:
            stmt = stmt.where(Fact.detail_level == detail_level)
        stmt = stmt.order_by(Fact.created_at).offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def list_by_tag(self, tag_name: str) -> Sequence[Fact]:
        """Return all active facts that have the given tag."""
        stmt = (
            select(Fact)
            .join(Fact.tags)
            .where(Tag.name == tag_name, Fact.is_active == True)  # noqa: E712
        )
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        fact_id: str,
        changed_by: str | None = None,
        change_reason: str | None = None,
        **fields,
    ) -> Fact:
        """
        Update mutable fields on an existing Fact and record a new version.

        Args:
            fact_id:        Primary key of the fact to update.
            changed_by:     Identity of the person making the change.
            change_reason:  Human-readable reason for the change.
            **fields:       Keyword arguments mapping column names to new values.
                            Supported: title, content, extended_content, formula,
                            units, source, source_url, confidence_score, status,
                            domain, category, subcategory, detail_level, tags.

        Returns:
            The updated :class:`~factdb.models.Fact` instance.

        Raises:
            ValueError: If the fact is not found.
        """
        fact = self.get(fact_id)
        if fact is None:
            raise ValueError(f"Fact not found: {fact_id!r}")

        updatable = {
            "title", "content", "extended_content", "formula", "units",
            "source", "source_url", "confidence_score", "status",
            "domain", "category", "subcategory", "detail_level",
        }
        for key, value in fields.items():
            if key == "tags":
                continue
            if key in updatable:
                setattr(fact, key, value)

        if "tags" in fields:
            fact.tags.clear()
            for tag_name in (fields["tags"] or []):
                fact.tags.append(get_or_create_tag(self.session, tag_name.strip()))

        fact.version += 1
        fact.updated_at = datetime.now(timezone.utc)
        fact.updated_by = changed_by

        self.session.flush()
        self._snapshot_version(fact, changed_by=changed_by, change_reason=change_reason)

        return fact

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------

    def delete(self, fact_id: str, deleted_by: str | None = None) -> None:
        """
        Soft-delete a fact by marking it as inactive.

        The fact record is retained for audit purposes but will be excluded
        from all normal queries.

        Args:
            fact_id:    Primary key of the fact to delete.
            deleted_by: Identity of the person requesting the deletion.

        Raises:
            ValueError: If the fact is not found.
        """
        fact = self.get(fact_id)
        if fact is None:
            raise ValueError(f"Fact not found: {fact_id!r}")
        fact.is_active = False
        fact.status = FactStatus.DEPRECATED
        fact.updated_by = deleted_by
        fact.updated_at = datetime.now(timezone.utc)
        self.session.flush()

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        weight: float = 1.0,
        description: str | None = None,
    ) -> FactRelationship:
        """
        Create a directed semantic relationship between two facts.

        Args:
            source_id:         PK of the originating fact.
            target_id:         PK of the referenced fact.
            relationship_type: Semantic type of the relationship.
            weight:            Importance weight (0.0–1.0); defaults to 1.0.
            description:       Optional human-readable description.

        Returns:
            The new :class:`~factdb.models.FactRelationship` instance.

        Raises:
            ValueError: If either fact is not found.
        """
        for fid in (source_id, target_id):
            if self.get(fid) is None:
                raise ValueError(f"Fact not found: {fid!r}")

        rel = FactRelationship(
            source_fact_id=source_id,
            target_fact_id=target_id,
            relationship_type=relationship_type,
            weight=weight,
            description=description,
        )
        self.session.add(rel)
        self.session.flush()
        return rel

    def get_related_facts(
        self,
        fact_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[tuple[FactRelationship, Fact]]:
        """
        Return facts directly reachable from *fact_id* via outgoing edges.

        Args:
            fact_id:           PK of the starting fact.
            relationship_type: Optional filter; if None all types are returned.

        Returns:
            List of ``(relationship, target_fact)`` tuples.
        """
        stmt = (
            select(FactRelationship)
            .where(FactRelationship.source_fact_id == fact_id)
        )
        if relationship_type is not None:
            stmt = stmt.where(FactRelationship.relationship_type == relationship_type)

        rels = self.session.execute(stmt).scalars().all()
        return [(rel, rel.target_fact) for rel in rels]

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------

    def get_history(self, fact_id: str) -> Sequence[FactVersion]:
        """Return all version snapshots for a fact, ordered by version number."""
        stmt = (
            select(FactVersion)
            .where(FactVersion.fact_id == fact_id)
            .order_by(FactVersion.version)
        )
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    def record_usage(
        self,
        fact_id: str,
        context: str | None = None,
        used_by: str | None = None,
    ) -> FactUsageLog:
        """
        Record that a fact was used and increment its usage counter.

        Increments :attr:`Fact.use_count`, updates :attr:`Fact.last_used_at`,
        and appends a :class:`~factdb.models.FactUsageLog` row so that
        per-use context is retained for audit and prioritisation purposes.

        Args:
            fact_id:  Primary key of the fact that was used.
            context:  Short label describing the call-site, e.g.
                      ``"search"``, ``"inference"``, or ``"reasoning"``.
            used_by:  Identity of the caller (user or agent name).

        Returns:
            The new :class:`~factdb.models.FactUsageLog` instance.

        Raises:
            ValueError: If the fact is not found.
        """
        fact = self.get(fact_id)
        if fact is None:
            raise ValueError(f"Fact not found: {fact_id!r}")

        fact.use_count = (fact.use_count or 0) + 1
        fact.last_used_at = datetime.now(timezone.utc)

        log = FactUsageLog(fact_id=fact_id, context=context, used_by=used_by)
        self.session.add(log)
        self.session.flush()
        return log

    def list_most_used(
        self,
        limit: int = 20,
        min_use_count: int = 1,
        domain: EngineeringDomain | None = None,
    ) -> Sequence[Fact]:
        """
        Return active facts ranked by descending use count.

        Useful for identifying high-value facts that should be prioritised
        for verification and maintenance.

        Args:
            limit:         Maximum number of results (default 20).
            min_use_count: Only include facts used at least this many times
                           (default 1, i.e. at least once).
            domain:        Optional domain filter.

        Returns:
            Sequence of :class:`~factdb.models.Fact` objects ordered by
            ``use_count`` descending, then ``last_used_at`` descending.
        """
        stmt = (
            select(Fact)
            .where(Fact.is_active == True, Fact.use_count >= min_use_count)  # noqa: E712
        )
        if domain is not None:
            stmt = stmt.where(Fact.domain == domain)
        stmt = stmt.order_by(Fact.use_count.desc(), Fact.last_used_at.desc()).limit(limit)
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _snapshot_version(
        self,
        fact: Fact,
        changed_by: str | None = None,
        change_reason: str | None = None,
    ) -> FactVersion:
        snapshot = FactVersion(
            fact_id=fact.id,
            version=fact.version,
            title=fact.title,
            content=fact.content,
            extended_content=fact.extended_content,
            formula=fact.formula,
            detail_level=fact.detail_level,
            status=fact.status,
            confidence_score=fact.confidence_score,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot
