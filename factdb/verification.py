"""
Verification and change-management workflow for FactDB.

A fact must pass through a review cycle before it is considered *verified*
and safe for use in production AI reasoning.

Workflow states
---------------
DRAFT → PENDING_REVIEW → VERIFIED
                       ↘ NEEDS_REVISION → (edit) → PENDING_REVIEW
                       ↘ (REJECTED remains at PENDING_REVIEW or reverts to DRAFT)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import (
    Fact,
    FactStatus,
    FactVerification,
    VerificationStatus,
)


class VerificationWorkflow:
    """
    Manages the fact verification lifecycle.

    All methods require an active *session*.  The caller controls
    transaction boundaries (``session.commit()``).
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Submit for review
    # ------------------------------------------------------------------

    def submit_for_review(self, fact_id: str, submitted_by: str) -> Fact:
        """
        Transition a fact from DRAFT (or NEEDS_REVISION) to PENDING_REVIEW.

        Args:
            fact_id:       PK of the fact to submit.
            submitted_by:  Identity of the submitting author.

        Returns:
            The updated :class:`~factdb.models.Fact`.

        Raises:
            ValueError: If the fact is not found or already in PENDING_REVIEW
                        or VERIFIED state.
        """
        fact = self._get_or_raise(fact_id)

        allowed_vals = {FactStatus.DRAFT.value}
        if fact.status not in allowed_vals:
            # If it's already pending or verified, nothing to do
            if fact.status == FactStatus.PENDING_REVIEW.value:
                return fact
            raise ValueError(
                f"Fact {fact_id!r} cannot be submitted from status {fact.status!r}."
            )

        fact.status = FactStatus.PENDING_REVIEW
        fact.updated_at = datetime.now(timezone.utc)
        fact.updated_by = submitted_by
        self.session.flush()
        return fact

    # ------------------------------------------------------------------
    # Approve / Reject / Request revision
    # ------------------------------------------------------------------

    def approve(
        self,
        fact_id: str,
        verified_by: str,
        notes: str | None = None,
    ) -> FactVerification:
        """
        Approve a fact — transitions it to VERIFIED status.

        Args:
            fact_id:     PK of the fact to approve.
            verified_by: Identity of the reviewer.
            notes:       Optional reviewer notes.

        Returns:
            The new :class:`~factdb.models.FactVerification` record.

        Raises:
            ValueError: If the fact is not found or not in PENDING_REVIEW.
        """
        fact = self._get_or_raise(fact_id)
        self._assert_pending(fact)

        fact.status = FactStatus.VERIFIED
        fact.updated_at = datetime.now(timezone.utc)
        fact.updated_by = verified_by
        self.session.flush()

        return self._record_verification(
            fact,
            verified_by=verified_by,
            verification_status=VerificationStatus.APPROVED,
            notes=notes,
        )

    def reject(
        self,
        fact_id: str,
        verified_by: str,
        notes: str | None = None,
    ) -> FactVerification:
        """
        Reject a fact — transitions it back to DRAFT for correction.

        Args:
            fact_id:     PK of the fact to reject.
            verified_by: Identity of the reviewer.
            notes:       Mandatory reviewer notes explaining the rejection.

        Returns:
            The new :class:`~factdb.models.FactVerification` record.

        Raises:
            ValueError: If the fact is not found or not in PENDING_REVIEW.
        """
        fact = self._get_or_raise(fact_id)
        self._assert_pending(fact)

        fact.status = FactStatus.DRAFT
        fact.updated_at = datetime.now(timezone.utc)
        fact.updated_by = verified_by
        self.session.flush()

        return self._record_verification(
            fact,
            verified_by=verified_by,
            verification_status=VerificationStatus.REJECTED,
            notes=notes,
        )

    def request_revision(
        self,
        fact_id: str,
        verified_by: str,
        notes: str | None = None,
    ) -> FactVerification:
        """
        Request a revision — fact stays in a special *pending* sub-state.

        The fact status is set back to DRAFT so the author can address the
        review feedback before re-submitting.

        Args:
            fact_id:     PK of the fact.
            verified_by: Identity of the reviewer.
            notes:       Explanation of what needs to change.

        Returns:
            The new :class:`~factdb.models.FactVerification` record.

        Raises:
            ValueError: If the fact is not found or not in PENDING_REVIEW.
        """
        fact = self._get_or_raise(fact_id)
        self._assert_pending(fact)

        fact.status = FactStatus.DRAFT
        fact.updated_at = datetime.now(timezone.utc)
        fact.updated_by = verified_by
        self.session.flush()

        return self._record_verification(
            fact,
            verified_by=verified_by,
            verification_status=VerificationStatus.NEEDS_REVISION,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_verification_history(self, fact_id: str) -> Sequence[FactVerification]:
        """
        Return the full verification history for a fact.

        Args:
            fact_id: PK of the fact.

        Returns:
            Sequence of :class:`~factdb.models.FactVerification` records
            ordered by most-recent first.
        """
        stmt = (
            select(FactVerification)
            .where(FactVerification.fact_id == fact_id)
            .order_by(FactVerification.verified_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def pending_review_facts(self) -> Sequence[Fact]:
        """Return all facts currently awaiting review."""
        stmt = select(Fact).where(
            Fact.status == FactStatus.PENDING_REVIEW,
            Fact.is_active == True,  # noqa: E712
        )
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_or_raise(self, fact_id: str) -> Fact:
        fact = self.session.get(Fact, fact_id)
        if fact is None:
            raise ValueError(f"Fact not found: {fact_id!r}")
        return fact

    @staticmethod
    def _assert_pending(fact: Fact) -> None:
        if fact.status != FactStatus.PENDING_REVIEW.value:
            raise ValueError(
                f"Fact {fact.id!r} must be in PENDING_REVIEW to be reviewed; "
                f"current status is {fact.status!r}."
            )

    def _record_verification(
        self,
        fact: Fact,
        verified_by: str,
        verification_status: VerificationStatus,
        notes: str | None,
    ) -> FactVerification:
        record = FactVerification(
            fact_id=fact.id,
            verified_by=verified_by,
            verification_status=verification_status,
            notes=notes,
            fact_version_at_verification=fact.version,
        )
        self.session.add(record)
        self.session.flush()
        return record
