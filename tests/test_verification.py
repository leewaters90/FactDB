"""
Tests for VerificationWorkflow.
"""

import pytest

from factdb.models import FactStatus, VerificationStatus
from factdb.repository import FactRepository
from factdb.verification import VerificationWorkflow


def _draft_fact(session, title="Test Fact"):
    repo = FactRepository(session)
    fact = repo.create(title=title, content="Some content.")
    session.flush()
    return fact


class TestVerificationWorkflow:

    # ---------------------------------------------------------------
    # submit_for_review
    # ---------------------------------------------------------------

    def test_submit_draft_transitions_to_pending(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        updated = wf.submit_for_review(fact.id, submitted_by="alice")
        db_session.commit()
        assert updated.status == FactStatus.PENDING_REVIEW.value

    def test_submit_already_pending_is_idempotent(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact.id, submitted_by="alice")
        db_session.commit()
        # Second submit should succeed without error
        result = wf.submit_for_review(fact.id, submitted_by="alice")
        assert result.status == FactStatus.PENDING_REVIEW.value

    def test_submit_verified_fact_raises(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact.id, submitted_by="alice")
        wf.approve(fact.id, verified_by="bob")
        db_session.commit()
        with pytest.raises(ValueError):
            wf.submit_for_review(fact.id, submitted_by="alice")

    def test_submit_nonexistent_raises(self, db_session):
        wf = VerificationWorkflow(db_session)
        with pytest.raises(ValueError, match="Fact not found"):
            wf.submit_for_review("ghost", submitted_by="alice")

    # ---------------------------------------------------------------
    # approve
    # ---------------------------------------------------------------

    def test_approve_pending_transitions_to_verified(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact.id, submitted_by="alice")
        rec = wf.approve(fact.id, verified_by="bob", notes="Looks good")
        db_session.commit()

        repo = FactRepository(db_session)
        refreshed = repo.get(fact.id)
        assert refreshed.status == FactStatus.VERIFIED.value
        assert rec.verification_status == VerificationStatus.APPROVED.value
        assert rec.notes == "Looks good"

    def test_approve_non_pending_raises(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        with pytest.raises(ValueError, match="PENDING_REVIEW"):
            wf.approve(fact.id, verified_by="bob")

    # ---------------------------------------------------------------
    # reject
    # ---------------------------------------------------------------

    def test_reject_pending_transitions_to_draft(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact.id, submitted_by="alice")
        rec = wf.reject(fact.id, verified_by="bob", notes="Incorrect formula")
        db_session.commit()

        repo = FactRepository(db_session)
        refreshed = repo.get(fact.id)
        assert refreshed.status == FactStatus.DRAFT.value
        assert rec.verification_status == VerificationStatus.REJECTED.value

    # ---------------------------------------------------------------
    # request_revision
    # ---------------------------------------------------------------

    def test_request_revision(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact.id, submitted_by="alice")
        rec = wf.request_revision(fact.id, verified_by="bob", notes="Needs units")
        db_session.commit()

        repo = FactRepository(db_session)
        refreshed = repo.get(fact.id)
        assert refreshed.status == FactStatus.DRAFT.value
        assert rec.verification_status == VerificationStatus.NEEDS_REVISION.value

    # ---------------------------------------------------------------
    # Full round-trip workflow
    # ---------------------------------------------------------------

    def test_full_workflow_draft_to_verified(self, db_session):
        repo = FactRepository(db_session)
        wf = VerificationWorkflow(db_session)

        fact = repo.create(title="Workflow Test", content="E=mc²")
        db_session.flush()
        assert fact.status == FactStatus.DRAFT.value

        wf.submit_for_review(fact.id, submitted_by="engineer")
        assert fact.status == FactStatus.PENDING_REVIEW.value

        wf.approve(fact.id, verified_by="lead-engineer")
        db_session.commit()
        assert fact.status == FactStatus.VERIFIED.value

    def test_full_workflow_with_revision_cycle(self, db_session):
        repo = FactRepository(db_session)
        wf = VerificationWorkflow(db_session)

        fact = repo.create(title="Revision Test", content="Initial content")
        db_session.flush()

        # Submit → revision requested → resubmit → approve
        wf.submit_for_review(fact.id, submitted_by="eng")
        wf.request_revision(fact.id, verified_by="lead", notes="Add units")
        repo.update(fact.id, content="Improved content with units (m/s)", changed_by="eng")
        wf.submit_for_review(fact.id, submitted_by="eng")
        wf.approve(fact.id, verified_by="lead")
        db_session.commit()

        assert fact.status == FactStatus.VERIFIED.value

    # ---------------------------------------------------------------
    # get_verification_history / pending_review_facts
    # ---------------------------------------------------------------

    def test_get_verification_history(self, db_session):
        fact = _draft_fact(db_session)
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact.id, submitted_by="alice")
        wf.reject(fact.id, verified_by="bob", notes="Bad")
        wf.submit_for_review(fact.id, submitted_by="alice")
        wf.approve(fact.id, verified_by="carol")
        db_session.commit()

        history = wf.get_verification_history(fact.id)
        assert len(history) == 2
        statuses = [h.verification_status for h in history]
        assert VerificationStatus.APPROVED.value in statuses
        assert VerificationStatus.REJECTED.value in statuses

    def test_pending_review_facts(self, db_session):
        fact1 = _draft_fact(db_session, title="F1")
        fact2 = _draft_fact(db_session, title="F2")
        _draft_fact(db_session, title="F3")  # stays DRAFT
        wf = VerificationWorkflow(db_session)
        wf.submit_for_review(fact1.id, submitted_by="alice")
        wf.submit_for_review(fact2.id, submitted_by="alice")
        db_session.commit()

        pending = wf.pending_review_facts()
        ids = {f.id for f in pending}
        assert fact1.id in ids
        assert fact2.id in ids
