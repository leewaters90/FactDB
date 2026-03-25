"""
Tests for the seeder — ensures seed data loads correctly.
"""

import pytest
from sqlalchemy import select

from factdb.models import Fact, FactStatus
from factdb.seeder import seed


class TestSeeder:
    def test_seed_creates_facts(self, db_session):
        result = seed(db_session)
        assert result["created"] > 0

    def test_seed_is_idempotent(self, db_session):
        r1 = seed(db_session)
        r2 = seed(db_session)
        assert r2["created"] == 0
        assert r2["skipped"] == r1["created"]

    def test_seed_facts_are_verified(self, db_session):
        seed(db_session)
        facts = db_session.execute(select(Fact)).scalars().all()
        assert all(f.status == FactStatus.VERIFIED.value for f in facts)

    def test_seed_creates_relationships(self, db_session):
        result = seed(db_session)
        assert result["relationships"] > 0

    def test_seed_facts_have_tags(self, db_session):
        seed(db_session)
        facts = db_session.execute(select(Fact)).scalars().all()
        facts_with_tags = [f for f in facts if f.tags]
        assert len(facts_with_tags) > 0
