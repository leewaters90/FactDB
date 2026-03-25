"""
Tests for the ReasoningEngine.
"""

import pytest

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    FactStatus,
    RelationshipType,
)
from factdb.repository import FactRepository
from factdb.reasoning import ReasoningEngine
from factdb.verification import VerificationWorkflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verified_fact(session, title, content="Content."):
    repo = FactRepository(session)
    wf = VerificationWorkflow(session)
    fact = repo.create(title=title, content=content)
    session.flush()
    wf.submit_for_review(fact.id, submitted_by="sys")
    wf.approve(fact.id, verified_by="sys")
    session.flush()
    return fact


def _draft_fact(session, title, content="Draft content."):
    repo = FactRepository(session)
    fact = repo.create(title=title, content=content)
    session.flush()
    return fact


# ---------------------------------------------------------------------------
# collect_prerequisites (backward chaining)
# ---------------------------------------------------------------------------


class TestCollectPrerequisites:
    def test_single_fact_no_prereqs(self, db_session):
        fact = _verified_fact(db_session, "Goal")
        engine = ReasoningEngine(db_session)
        result = engine.collect_prerequisites(fact.id)
        assert result.goal_fact.id == fact.id
        assert len(result.chain) == 1

    def test_collects_prereq_chain(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "A — Base knowledge")
        b = _verified_fact(db_session, "B — Builds on A")
        c = _verified_fact(db_session, "C — Goal")

        # c depends on b, b depends on a  (source --DEPENDS_ON--> target = source requires target)
        repo.add_relationship(c.id, b.id, RelationshipType.DEPENDS_ON)
        repo.add_relationship(b.id, a.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.collect_prerequisites(c.id)

        chain_ids = {f.id for f in result.chain}
        assert a.id in chain_ids
        assert b.id in chain_ids
        assert c.id in chain_ids

    def test_detects_missing_unverified_prereq(self, db_session):
        repo = FactRepository(db_session)
        prereq = _draft_fact(db_session, "Unverified Prereq")
        goal = _verified_fact(db_session, "Goal that needs prereq")
        # goal --DEPENDS_ON--> prereq  (goal requires prereq)
        repo.add_relationship(goal.id, prereq.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.collect_prerequisites(goal.id)
        missing_ids = {f.id for f in result.missing_prereqs}
        assert prereq.id in missing_ids
        assert not result.is_achievable()

    def test_no_missing_prereqs_when_all_verified(self, db_session):
        repo = FactRepository(db_session)
        prereq = _verified_fact(db_session, "Verified Prereq")
        goal = _verified_fact(db_session, "Verified Goal")
        # goal --DEPENDS_ON--> prereq  (goal requires prereq)
        repo.add_relationship(goal.id, prereq.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.collect_prerequisites(goal.id)
        assert result.is_achievable()

    def test_raises_for_unknown_fact(self, db_session):
        engine = ReasoningEngine(db_session)
        with pytest.raises(ValueError, match="Fact not found"):
            engine.collect_prerequisites("ghost-id")

    def test_cycle_does_not_loop_forever(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "Cyclic A")
        b = _verified_fact(db_session, "Cyclic B")
        repo.add_relationship(a.id, b.id, RelationshipType.DEPENDS_ON)
        repo.add_relationship(b.id, a.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        # Should not loop indefinitely
        result = engine.collect_prerequisites(a.id, max_depth=5)
        assert result is not None


# ---------------------------------------------------------------------------
# derive_consequences (forward chaining)
# ---------------------------------------------------------------------------


class TestDeriveConsequences:
    def test_derives_supported_fact(self, db_session):
        repo = FactRepository(db_session)
        known = _verified_fact(db_session, "Known Fact")
        derived = _verified_fact(db_session, "Derived Fact")
        repo.add_relationship(known.id, derived.id, RelationshipType.SUPPORTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.derive_consequences([known.id])
        ids = {f.id for f in result}
        assert derived.id in ids

    def test_does_not_include_known_facts(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "A")
        b = _verified_fact(db_session, "B")
        repo.add_relationship(a.id, b.id, RelationshipType.DERIVED_FROM)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.derive_consequences([a.id])
        ids = {f.id for f in result}
        assert a.id not in ids
        assert b.id in ids

    def test_chains_forward(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "Chain A")
        b = _verified_fact(db_session, "Chain B")
        c = _verified_fact(db_session, "Chain C")
        repo.add_relationship(a.id, b.id, RelationshipType.SUPPORTS)
        repo.add_relationship(b.id, c.id, RelationshipType.SUPPORTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.derive_consequences([a.id], max_depth=5)
        ids = {f.id for f in result}
        assert b.id in ids
        assert c.id in ids


# ---------------------------------------------------------------------------
# detect_conflicts
# ---------------------------------------------------------------------------


class TestDetectConflicts:
    def test_detects_contradicting_facts(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "Claim A")
        b = _verified_fact(db_session, "Claim B — contradicts A")
        repo.add_relationship(a.id, b.id, RelationshipType.CONTRADICTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        conflicts = engine.detect_conflicts([a.id, b.id])
        assert len(conflicts) == 1
        pair_ids = {conflicts[0][0].id, conflicts[0][1].id}
        assert a.id in pair_ids
        assert b.id in pair_ids

    def test_no_conflicts_when_clean(self, db_session):
        a = _verified_fact(db_session, "Fact X")
        b = _verified_fact(db_session, "Fact Y")
        db_session.commit()

        engine = ReasoningEngine(db_session)
        conflicts = engine.detect_conflicts([a.id, b.id])
        assert len(conflicts) == 0

    def test_no_duplicate_conflict_pairs(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "P")
        b = _verified_fact(db_session, "Q — contradicts P")
        repo.add_relationship(a.id, b.id, RelationshipType.CONTRADICTS)
        repo.add_relationship(b.id, a.id, RelationshipType.CONTRADICTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        conflicts = engine.detect_conflicts([a.id, b.id])
        assert len(conflicts) == 1  # Only one unique pair


# ---------------------------------------------------------------------------
# build_decision_tree
# ---------------------------------------------------------------------------


class TestBuildDecisionTree:
    def test_builds_single_node_tree(self, db_session):
        fact = _verified_fact(db_session, "Root Only")
        engine = ReasoningEngine(db_session)
        tree = engine.build_decision_tree(fact.id)
        assert tree.fact.id == fact.id
        assert tree.children == []

    def test_builds_tree_with_children(self, db_session):
        repo = FactRepository(db_session)
        root = _verified_fact(db_session, "Root")
        child1 = _verified_fact(db_session, "Child 1")
        child2 = _verified_fact(db_session, "Child 2")
        repo.add_relationship(root.id, child1.id, RelationshipType.SUPPORTS, weight=0.9)
        repo.add_relationship(root.id, child2.id, RelationshipType.SUPPORTS, weight=0.7)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        tree = engine.build_decision_tree(root.id)
        assert len(tree.children) == 2
        # Children should be ordered by weight descending
        weights = [rel.weight for rel, _ in tree.children]
        assert weights == sorted(weights, reverse=True)

    def test_cycle_safe_tree(self, db_session):
        repo = FactRepository(db_session)
        a = _verified_fact(db_session, "Tree A")
        b = _verified_fact(db_session, "Tree B")
        repo.add_relationship(a.id, b.id, RelationshipType.SUPPORTS)
        repo.add_relationship(b.id, a.id, RelationshipType.SUPPORTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        tree = engine.build_decision_tree(a.id, max_depth=3)
        assert tree is not None

    def test_raises_for_unknown_root(self, db_session):
        engine = ReasoningEngine(db_session)
        with pytest.raises(ValueError, match="Fact not found"):
            engine.build_decision_tree("no-such-fact")

    def test_as_dict(self, db_session):
        repo = FactRepository(db_session)
        root = _verified_fact(db_session, "Dict Root")
        child = _verified_fact(db_session, "Dict Child")
        repo.add_relationship(root.id, child.id, RelationshipType.SUPPORTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        tree = engine.build_decision_tree(root.id)
        d = tree.as_dict()
        assert d["fact_id"] == root.id
        assert len(d["children"]) == 1
        assert d["children"][0]["node"]["fact_id"] == child.id


# ---------------------------------------------------------------------------
# evaluate_applicability (expert system)
# ---------------------------------------------------------------------------


class TestEvaluateApplicability:
    def test_applicable_when_verified_no_deps(self, db_session):
        fact = _verified_fact(db_session, "Standalone")
        engine = ReasoningEngine(db_session)
        result = engine.evaluate_applicability(fact.id, context_fact_ids=[])
        assert result["applicable"] is True

    def test_not_applicable_when_draft(self, db_session):
        fact = _draft_fact(db_session, "Draft Fact")
        engine = ReasoningEngine(db_session)
        result = engine.evaluate_applicability(fact.id, context_fact_ids=[])
        assert result["applicable"] is False

    def test_not_applicable_missing_prereq(self, db_session):
        repo = FactRepository(db_session)
        prereq = _verified_fact(db_session, "Required Prereq")
        goal = _verified_fact(db_session, "Goal needing prereq")
        # goal --DEPENDS_ON--> prereq  (goal requires prereq)
        repo.add_relationship(goal.id, prereq.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        # Context does NOT include prereq
        result = engine.evaluate_applicability(goal.id, context_fact_ids=[])
        assert result["applicable"] is False
        assert prereq.title in result["missing_prereqs"]

    def test_applicable_with_prereq_in_context(self, db_session):
        repo = FactRepository(db_session)
        prereq = _verified_fact(db_session, "Provided Prereq")
        goal = _verified_fact(db_session, "Goal with prereq provided")
        # goal --DEPENDS_ON--> prereq  (goal requires prereq)
        repo.add_relationship(goal.id, prereq.id, RelationshipType.DEPENDS_ON)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.evaluate_applicability(goal.id, context_fact_ids=[prereq.id])
        assert result["applicable"] is True

    def test_not_applicable_with_conflicting_context(self, db_session):
        repo = FactRepository(db_session)
        conflict = _verified_fact(db_session, "Conflicting Fact")
        goal = _verified_fact(db_session, "Goal that conflicts")
        repo.add_relationship(goal.id, conflict.id, RelationshipType.CONTRADICTS)
        db_session.commit()

        engine = ReasoningEngine(db_session)
        result = engine.evaluate_applicability(goal.id, context_fact_ids=[conflict.id])
        assert result["applicable"] is False
        assert conflict.title in result["conflicts"]
