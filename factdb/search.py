"""
Full-text and filtered search for FactDB.

Implements a lightweight in-database search that works with SQLite's
built-in LIKE operator as well as structured filters.  The interface is
intentionally simple so that it can be wrapped by an AI planner.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    Fact,
    FactStatus,
    Tag,
)


class FactSearch:
    """
    Search helper for :class:`~factdb.models.Fact` records.

    All queries are restricted to active (``is_active=True``) facts unless
    *include_inactive* is explicitly set to ``True``.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        query: str | None = None,
        domain: EngineeringDomain | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        detail_level: DetailLevel | None = None,
        status: FactStatus | None = None,
        tags: list[str] | None = None,
        min_confidence: float = 0.0,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Fact]:
        """
        Search facts using a combination of keyword and structured filters.

        Args:
            query:            Free-text search against *title*, *content*, and
                              *extended_content*.  Case-insensitive LIKE match.
                              Supports ``%`` and ``_`` wildcards.
            domain:           Restrict to a specific engineering domain.
            category:         Restrict to a category (exact match, case-insensitive).
            subcategory:      Restrict to a subcategory (exact, case-insensitive).
            detail_level:     Restrict to a specific detail level.
            status:           Restrict to a lifecycle status (default: any).
            tags:             Return only facts that have **all** listed tags.
            min_confidence:   Minimum confidence score threshold (0.0–1.0).
            include_inactive: Include soft-deleted facts when ``True``.
            limit:            Maximum results to return (default 50).
            offset:           Pagination offset (default 0).

        Returns:
            Sequence of matching :class:`~factdb.models.Fact` objects ordered
            by descending confidence score then ascending title.
        """
        stmt = select(Fact)

        if not include_inactive:
            stmt = stmt.where(Fact.is_active == True)  # noqa: E712

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Fact.title.ilike(pattern),
                    Fact.content.ilike(pattern),
                    Fact.extended_content.ilike(pattern),
                )
            )

        if domain is not None:
            stmt = stmt.where(Fact.domain == domain)

        if category is not None:
            stmt = stmt.where(Fact.category.ilike(category))

        if subcategory is not None:
            stmt = stmt.where(Fact.subcategory.ilike(subcategory))

        if detail_level is not None:
            stmt = stmt.where(Fact.detail_level == detail_level)

        if status is not None:
            stmt = stmt.where(Fact.status == status)

        if min_confidence > 0.0:
            stmt = stmt.where(Fact.confidence_score >= min_confidence)

        if tags:
            # Must have ALL specified tags (chained joins)
            for tag_name in tags:
                tag_alias = select(Tag.id).where(Tag.name == tag_name).scalar_subquery()
                stmt = stmt.where(
                    Fact.id.in_(
                        select(Fact.id)
                        .join(Fact.tags)
                        .where(Tag.name == tag_name)
                    )
                )

        stmt = (
            stmt.order_by(Fact.confidence_score.desc(), Fact.title)
            .offset(offset)
            .limit(limit)
        )

        return self.session.execute(stmt).scalars().all()

    def get_by_domain_and_level(
        self,
        domain: EngineeringDomain,
        detail_level: DetailLevel,
        status: FactStatus = FactStatus.VERIFIED,
    ) -> Sequence[Fact]:
        """
        Convenience method: fetch verified facts for a domain at a given
        level of detail.  Commonly used by AI planners to retrieve the
        appropriate knowledge layer.

        Args:
            domain:       Engineering domain to query.
            detail_level: Desired granularity.
            status:       Minimum lifecycle status (default: VERIFIED).

        Returns:
            Sequence of matching facts ordered by title.
        """
        return self.search(domain=domain, detail_level=detail_level, status=status)

    def suggest_related_by_tags(
        self, fact_id: str, limit: int = 10
    ) -> Sequence[Fact]:
        """
        Suggest facts that share at least one tag with the given fact.

        This is a lightweight alternative to the graph-based
        :class:`~factdb.reasoning.ReasoningEngine` for quick tag-based
        similarity lookups.

        Args:
            fact_id: PK of the reference fact.
            limit:   Maximum number of suggestions to return (default 10).

        Returns:
            Sequence of suggested facts (excluding the reference fact itself).
        """
        fact = self.session.get(Fact, fact_id)
        if fact is None or not fact.tags:
            return []

        tag_names = [t.name for t in fact.tags]
        stmt = (
            select(Fact)
            .join(Fact.tags)
            .where(Tag.name.in_(tag_names), Fact.id != fact_id, Fact.is_active == True)  # noqa: E712
            .distinct()
            .order_by(Fact.confidence_score.desc())
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()
