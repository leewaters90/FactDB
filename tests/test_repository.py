"""
Tests for FactRepository — CRUD and change management.
"""

import pytest

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    FactStatus,
    RelationshipType,
)
from factdb.repository import FactRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fact(repo, **overrides):
    defaults = dict(
        title="Test Fact",
        content="This is a test fact.",
        domain=EngineeringDomain.MECHANICAL,
        category="test-category",
        detail_level=DetailLevel.FUNDAMENTAL,
        created_by="tester",
    )
    defaults.update(overrides)
    return repo.create(**defaults)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_minimal(self, db_session):
        repo = FactRepository(db_session)
        fact = repo.create(title="Simple Fact", content="A simple fact.")
        db_session.commit()

        assert fact.id is not None
        assert fact.title == "Simple Fact"
        assert fact.content == "A simple fact."
        assert fact.status == FactStatus.DRAFT.value
        assert fact.version == 1
        assert fact.is_active is True

    def test_create_with_tags(self, db_session):
        repo = FactRepository(db_session)
        fact = repo.create(
            title="Tagged Fact",
            content="A fact with tags.",
            tags=["physics", "mechanics"],
        )
        db_session.commit()

        tag_names = {t.name for t in fact.tags}
        assert tag_names == {"physics", "mechanics"}

    def test_create_records_version_1(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo)
        db_session.commit()

        versions = repo.get_history(fact.id)
        assert len(versions) == 1
        assert versions[0].version == 1
        assert versions[0].title == fact.title

    def test_create_sets_domain(self, db_session):
        repo = FactRepository(db_session)
        fact = repo.create(
            title="EE Fact",
            content="Ohm's law",
            domain=EngineeringDomain.ELECTRICAL,
        )
        db_session.commit()
        assert fact.domain == EngineeringDomain.ELECTRICAL.value

    def test_duplicate_tags_deduplicated(self, db_session):
        repo = FactRepository(db_session)
        # Create first fact with a tag
        repo.create(title="F1", content="c1", tags=["shared-tag"])
        # Create second fact with the same tag — should reuse the existing Tag row
        fact2 = repo.create(title="F2", content="c2", tags=["shared-tag"])
        db_session.commit()

        tag_names = {t.name for t in fact2.tags}
        assert "shared-tag" in tag_names


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class TestRead:
    def test_get_existing(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo)
        db_session.commit()

        retrieved = repo.get(fact.id)
        assert retrieved is not None
        assert retrieved.id == fact.id

    def test_get_nonexistent_returns_none(self, db_session):
        repo = FactRepository(db_session)
        assert repo.get("nonexistent-id") is None

    def test_list_all_filters_inactive(self, db_session):
        repo = FactRepository(db_session)
        f1 = _make_fact(repo, title="Active Fact")
        f2 = _make_fact(repo, title="Inactive Fact")
        repo.delete(f2.id)
        db_session.commit()

        active = repo.list_all(is_active=True)
        titles = [f.title for f in active]
        assert "Active Fact" in titles
        assert "Inactive Fact" not in titles

    def test_list_all_domain_filter(self, db_session):
        repo = FactRepository(db_session)
        _make_fact(repo, title="Mech Fact", domain=EngineeringDomain.MECHANICAL)
        _make_fact(repo, title="EE Fact", domain=EngineeringDomain.ELECTRICAL)
        db_session.commit()

        mech = repo.list_all(domain=EngineeringDomain.MECHANICAL)
        assert all(f.domain == EngineeringDomain.MECHANICAL.value for f in mech)

    def test_list_by_tag(self, db_session):
        repo = FactRepository(db_session)
        f1 = _make_fact(repo, title="T1", tags=["alpha", "beta"])
        f2 = _make_fact(repo, title="T2", tags=["beta"])
        f3 = _make_fact(repo, title="T3", tags=["gamma"])
        db_session.commit()

        beta_facts = repo.list_by_tag("beta")
        ids = {f.id for f in beta_facts}
        assert f1.id in ids
        assert f2.id in ids
        assert f3.id not in ids

    def test_list_all_pagination(self, db_session):
        repo = FactRepository(db_session)
        for i in range(5):
            _make_fact(repo, title=f"Fact {i}")
        db_session.commit()

        page1 = repo.list_all(limit=2, offset=0)
        page2 = repo.list_all(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert {f.id for f in page1}.isdisjoint({f.id for f in page2})


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_update_content(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo)
        db_session.commit()

        repo.update(fact.id, content="Updated content.", changed_by="editor")
        db_session.commit()

        updated = repo.get(fact.id)
        assert updated.content == "Updated content."
        assert updated.version == 2

    def test_update_increments_version(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo)
        db_session.commit()

        for i in range(3):
            repo.update(fact.id, content=f"Content v{i+2}", changed_by="ed")
        db_session.commit()

        assert repo.get(fact.id).version == 4

    def test_update_records_new_version(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo)
        db_session.commit()

        repo.update(fact.id, content="New content", change_reason="Corrected typo")
        db_session.commit()

        history = repo.get_history(fact.id)
        assert len(history) == 2
        assert history[1].content == "New content"
        assert history[1].change_reason == "Corrected typo"

    def test_update_tags(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo, tags=["old-tag"])
        db_session.commit()

        repo.update(fact.id, tags=["new-tag-a", "new-tag-b"], changed_by="ed")
        db_session.commit()

        refreshed = repo.get(fact.id)
        tag_names = {t.name for t in refreshed.tags}
        assert tag_names == {"new-tag-a", "new-tag-b"}

    def test_update_nonexistent_raises(self, db_session):
        repo = FactRepository(db_session)
        with pytest.raises(ValueError, match="Fact not found"):
            repo.update("does-not-exist", content="x")


# ---------------------------------------------------------------------------
# Delete (soft)
# ---------------------------------------------------------------------------


class TestDelete:
    def test_soft_delete(self, db_session):
        repo = FactRepository(db_session)
        fact = _make_fact(repo)
        db_session.commit()

        repo.delete(fact.id, deleted_by="admin")
        db_session.commit()

        deleted = repo.get(fact.id)
        assert deleted.is_active is False
        assert deleted.status == FactStatus.DEPRECATED.value

    def test_delete_nonexistent_raises(self, db_session):
        repo = FactRepository(db_session)
        with pytest.raises(ValueError, match="Fact not found"):
            repo.delete("ghost-id")


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


class TestRelationships:
    def test_add_relationship(self, db_session):
        repo = FactRepository(db_session)
        f1 = _make_fact(repo, title="Source")
        f2 = _make_fact(repo, title="Target")
        db_session.commit()

        rel = repo.add_relationship(
            f1.id, f2.id, RelationshipType.SUPPORTS, weight=0.8
        )
        db_session.commit()

        assert rel.id is not None
        assert rel.source_fact_id == f1.id
        assert rel.target_fact_id == f2.id
        assert rel.relationship_type == RelationshipType.SUPPORTS.value

    def test_get_related_facts(self, db_session):
        repo = FactRepository(db_session)
        f1 = _make_fact(repo, title="F1")
        f2 = _make_fact(repo, title="F2")
        f3 = _make_fact(repo, title="F3")
        db_session.commit()

        repo.add_relationship(f1.id, f2.id, RelationshipType.SUPPORTS)
        repo.add_relationship(f1.id, f3.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        all_related = repo.get_related_facts(f1.id)
        assert len(all_related) == 2

        supports_only = repo.get_related_facts(
            f1.id, relationship_type=RelationshipType.SUPPORTS
        )
        assert len(supports_only) == 1
        assert supports_only[0][1].title == "F2"

    def test_add_relationship_missing_fact_raises(self, db_session):
        repo = FactRepository(db_session)
        f1 = _make_fact(repo, title="Only One")
        db_session.commit()

        with pytest.raises(ValueError, match="Fact not found"):
            repo.add_relationship(f1.id, "ghost", RelationshipType.SUPPORTS)
