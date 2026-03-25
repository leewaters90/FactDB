"""
Tests for FactSearch.
"""

import pytest

from factdb.models import DetailLevel, EngineeringDomain, FactStatus
from factdb.repository import FactRepository
from factdb.search import FactSearch
from factdb.verification import VerificationWorkflow


def _seed_facts(session):
    """Create a small set of test facts for search tests."""
    repo = FactRepository(session)

    facts = [
        repo.create(
            title="Ohm's Law",
            content="V = I * R; voltage equals current times resistance.",
            domain=EngineeringDomain.ELECTRICAL,
            category="circuit theory",
            detail_level=DetailLevel.FUNDAMENTAL,
            confidence_score=1.0,
            tags=["circuit", "voltage"],
        ),
        repo.create(
            title="Newton's Second Law",
            content="F = m * a; force equals mass times acceleration.",
            domain=EngineeringDomain.MECHANICAL,
            category="dynamics",
            detail_level=DetailLevel.FUNDAMENTAL,
            confidence_score=0.95,
            tags=["force", "dynamics"],
        ),
        repo.create(
            title="Carnot Efficiency",
            content="Maximum efficiency of a heat engine: 1 - T_L/T_H.",
            domain=EngineeringDomain.MECHANICAL,
            category="thermodynamics",
            detail_level=DetailLevel.INTERMEDIATE,
            confidence_score=0.9,
            tags=["thermodynamics", "efficiency"],
        ),
        repo.create(
            title="Beam Bending Formula",
            content="Bending stress σ = M*y/I.",
            domain=EngineeringDomain.CIVIL,
            category="structural",
            detail_level=DetailLevel.INTERMEDIATE,
            confidence_score=0.85,
            tags=["bending", "structural"],
        ),
    ]

    # Verify the first two facts so status filtering can be tested
    wf = VerificationWorkflow(session)
    for f in facts[:2]:
        wf.submit_for_review(f.id, submitted_by="tester")
        wf.approve(f.id, verified_by="tester")

    session.commit()
    return facts


class TestFactSearch:
    def test_search_by_keyword_in_title(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(query="Ohm")
        assert any("Ohm" in f.title for f in results)

    def test_search_by_keyword_in_content(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(query="mass times acceleration")
        assert any("Newton" in f.title for f in results)

    def test_search_domain_filter(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(domain=EngineeringDomain.ELECTRICAL)
        assert all(f.domain == EngineeringDomain.ELECTRICAL.value for f in results)

    def test_search_detail_level_filter(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(detail_level=DetailLevel.INTERMEDIATE)
        assert all(f.detail_level == DetailLevel.INTERMEDIATE.value for f in results)
        assert len(results) == 2

    def test_search_status_filter(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(status=FactStatus.VERIFIED)
        assert all(f.status == FactStatus.VERIFIED.value for f in results)
        assert len(results) == 2

    def test_search_by_tag(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(tags=["thermodynamics"])
        titles = [f.title for f in results]
        assert "Carnot Efficiency" in titles
        assert "Ohm's Law" not in titles

    def test_search_min_confidence(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(min_confidence=0.95)
        assert all(f.confidence_score >= 0.95 for f in results)

    def test_search_returns_empty_for_no_match(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(query="xyzzy_no_match_12345")
        assert len(results) == 0

    def test_search_limit(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.search(limit=2)
        assert len(results) <= 2

    def test_get_by_domain_and_level(self, db_session):
        _seed_facts(db_session)
        searcher = FactSearch(db_session)
        results = searcher.get_by_domain_and_level(
            EngineeringDomain.ELECTRICAL, DetailLevel.FUNDAMENTAL
        )
        assert all(f.domain == EngineeringDomain.ELECTRICAL.value for f in results)

    def test_suggest_related_by_tags(self, db_session):
        facts = _seed_facts(db_session)
        searcher = FactSearch(db_session)
        # Ohm's Law has tag "circuit", which no other seed fact shares
        suggestions = searcher.suggest_related_by_tags(facts[0].id)
        # Should return 0 suggestions (no shared tags with other facts in this seed set)
        # But at minimum it should not include the fact itself
        assert all(f.id != facts[0].id for f in suggestions)

    def test_search_inactive_excluded_by_default(self, db_session):
        repo = FactRepository(db_session)
        f = repo.create(title="To Be Deleted", content="content")
        repo.delete(f.id)
        db_session.commit()

        searcher = FactSearch(db_session)
        results = searcher.search(query="To Be Deleted")
        assert all(f.is_active for f in results)
