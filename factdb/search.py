"""
Full-text and filtered search for FactDB.

Implements a lightweight in-database search that works with SQLite's
built-in FTS5 virtual table (``facts_fts``) for free-text queries and
falls back to LIKE matching when FTS5 is unavailable (e.g. non-SQLite
engines).  Structured filters (domain, level, status, tags, confidence)
use the composite indexes defined on the ``facts`` table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    Fact,
    FactStatus,
    FactUsageLog,
    Tag,
)


def _fts5_available(session: Session) -> bool:
    """Return True if the facts_fts virtual table exists in the database."""
    try:
        result = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'")
        ).fetchone()
        return result is not None
    except Exception:
        return False


class FactSearch:
    """
    Search helper for :class:`~factdb.models.Fact` records.

    All queries are restricted to active (``is_active=True``) facts unless
    *include_inactive* is explicitly set to ``True``.

    Keyword search uses the FTS5 virtual table (``facts_fts``) when
    available, falling back to ``ILIKE``/``LIKE`` pattern matching.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self._use_fts5: bool | None = None  # lazily resolved

    def _fts5_enabled(self) -> bool:
        if self._use_fts5 is None:
            self._use_fts5 = _fts5_available(self.session)
        return self._use_fts5

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
        record_usage: bool = False,
        usage_context: str | None = "search",
        usage_by: str | None = None,
    ) -> Sequence[Fact]:
        """
        Search facts using a combination of keyword and structured filters.

        Keyword search (``query``) uses the FTS5 virtual table when available
        for fast ranked retrieval, falling back to ``LIKE`` matching otherwise.

        Args:
            query:            Free-text search against *title*, *content*, and
                              *extended_content*.  Supports FTS5 match syntax
                              (e.g. ``"motor AND speed"``) when FTS5 is active.
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
            record_usage:     When ``True``, increment :attr:`Fact.use_count` and
                              append a :class:`~factdb.models.FactUsageLog` row for
                              every fact returned.  Defaults to ``False``.
            usage_context:    Context label written to the usage log when
                              *record_usage* is ``True`` (default ``"search"``).
            usage_by:         Identity of the caller written to the usage log.

        Returns:
            Sequence of matching :class:`~factdb.models.Fact` objects ordered
            by descending confidence score then ascending title.
        """
        if query and self._fts5_enabled():
            results = self._search_fts5(
                query=query,
                domain=domain,
                category=category,
                subcategory=subcategory,
                detail_level=detail_level,
                status=status,
                tags=tags,
                min_confidence=min_confidence,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )
        else:
            results = self._search_like(
                query=query,
                domain=domain,
                category=category,
                subcategory=subcategory,
                detail_level=detail_level,
                status=status,
                tags=tags,
                min_confidence=min_confidence,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )

        if record_usage and results:
            now = datetime.now(timezone.utc)
            for fact in results:
                fact.use_count = (fact.use_count or 0) + 1
                fact.last_used_at = now
                self.session.add(
                    FactUsageLog(
                        fact_id=fact.id,
                        context=usage_context,
                        used_by=usage_by,
                        used_at=now,
                    )
                )
            self.session.flush()

        return results

    # ------------------------------------------------------------------
    # FTS5 path
    # ------------------------------------------------------------------

    def _search_fts5(
        self,
        query: str,
        domain: EngineeringDomain | None,
        category: str | None,
        subcategory: str | None,
        detail_level: DetailLevel | None,
        status: FactStatus | None,
        tags: list[str] | None,
        min_confidence: float,
        include_inactive: bool,
        limit: int,
        offset: int,
    ) -> Sequence[Fact]:
        """Use the FTS5 virtual table to resolve matching fact IDs, then
        apply structured filters on the ``facts`` table."""
        # Escape any quotes in the query to prevent FTS5 syntax errors.
        safe_query = query.replace('"', '""')
        fts_stmt = text(
            "SELECT fact_id FROM facts_fts WHERE facts_fts MATCH :q"
        ).bindparams(q=safe_query)
        try:
            matching_ids = [
                row[0]
                for row in self.session.execute(fts_stmt).fetchall()
            ]
        except Exception:
            # FTS5 MATCH syntax error — fall back to LIKE
            return self._search_like(
                query=query,
                domain=domain,
                category=category,
                subcategory=subcategory,
                detail_level=detail_level,
                status=status,
                tags=tags,
                min_confidence=min_confidence,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )

        if not matching_ids:
            return []

        stmt = select(Fact).where(Fact.id.in_(matching_ids))
        stmt = self._apply_filters(
            stmt,
            domain=domain,
            category=category,
            subcategory=subcategory,
            detail_level=detail_level,
            status=status,
            tags=tags,
            min_confidence=min_confidence,
            include_inactive=include_inactive,
        )
        stmt = stmt.order_by(Fact.confidence_score.desc(), Fact.title).offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # LIKE fallback path
    # ------------------------------------------------------------------

    def _search_like(
        self,
        query: str | None,
        domain: EngineeringDomain | None,
        category: str | None,
        subcategory: str | None,
        detail_level: DetailLevel | None,
        status: FactStatus | None,
        tags: list[str] | None,
        min_confidence: float,
        include_inactive: bool,
        limit: int,
        offset: int,
    ) -> Sequence[Fact]:
        stmt = select(Fact)

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Fact.title.ilike(pattern),
                    Fact.content.ilike(pattern),
                    Fact.extended_content.ilike(pattern),
                )
            )

        stmt = self._apply_filters(
            stmt,
            domain=domain,
            category=category,
            subcategory=subcategory,
            detail_level=detail_level,
            status=status,
            tags=tags,
            min_confidence=min_confidence,
            include_inactive=include_inactive,
        )
        stmt = stmt.order_by(Fact.confidence_score.desc(), Fact.title).offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Shared filter builder
    # ------------------------------------------------------------------

    def _apply_filters(
        self,
        stmt,
        domain: EngineeringDomain | None,
        category: str | None,
        subcategory: str | None,
        detail_level: DetailLevel | None,
        status: FactStatus | None,
        tags: list[str] | None,
        min_confidence: float,
        include_inactive: bool,
    ):
        if not include_inactive:
            stmt = stmt.where(Fact.is_active == True)  # noqa: E712

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
            for tag_name in tags:
                stmt = stmt.where(
                    Fact.id.in_(
                        select(Fact.id)
                        .join(Fact.tags)
                        .where(Tag.name == tag_name)
                    )
                )

        return stmt

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

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
