"""
Reasoning engine for FactDB.

Provides graph traversal, rule-based inference, and decision-tree primitives
that allow small AI models to plan and execute complex engineering tasks by
walking the fact relationship graph.

Key concepts
------------
* **Forward chaining** — start from a set of known facts and derive new
  conclusions by following SUPPORTS / DERIVED_FROM edges.
* **Backward chaining** — start from a goal fact and collect all
  DEPENDS_ON / PREREQUISITE facts needed to achieve it.
* **Conflict detection** — surface CONTRADICTS edges between an active
  fact-set so the planner knows to seek clarification.
* **Decision tree nodes** — each fact can serve as a decision node;
  outgoing edges weighted by *weight* drive branching priorities.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import (
    Fact,
    FactRelationship,
    FactStatus,
    RelationshipType,
)


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class InferenceResult:
    """
    The outcome of a reasoning operation.

    Attributes:
        goal_fact:    The target fact that was queried.
        chain:        Ordered list of facts visited to reach the goal (BFS path).
        conflicts:    Pairs of facts that contradict each other within the chain.
        missing_prereqs: Facts in the chain that are not yet VERIFIED.
        depth:        Number of hops from the starting facts to the goal.
    """

    goal_fact: Fact
    chain: list[Fact] = field(default_factory=list)
    conflicts: list[tuple[Fact, Fact]] = field(default_factory=list)
    missing_prereqs: list[Fact] = field(default_factory=list)
    depth: int = 0

    def is_achievable(self) -> bool:
        """
        Return True if the goal is reachable without unresolved conflicts or
        missing verified prerequisites.
        """
        return not self.conflicts and not self.missing_prereqs

    def summary(self) -> str:
        lines = [f"Goal: {self.goal_fact.title}"]
        lines.append(f"  Depth      : {self.depth}")
        lines.append(f"  Chain      : {' → '.join(f.title for f in self.chain)}")
        if self.conflicts:
            for a, b in self.conflicts:
                lines.append(f"  ⚠ Conflict : {a.title!r} ↔ {b.title!r}")
        if self.missing_prereqs:
            for p in self.missing_prereqs:
                lines.append(f"  ✗ Unverified prerequisite: {p.title!r}")
        lines.append(f"  Achievable : {'yes' if self.is_achievable() else 'NO'}")
        return "\n".join(lines)


@dataclass
class DecisionNode:
    """
    A node in a decision tree derived from the fact graph.

    Attributes:
        fact:     The fact at this node.
        children: Child nodes keyed by relationship type, ordered by weight.
    """

    fact: Fact
    children: list[tuple[FactRelationship, "DecisionNode"]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "fact_id": self.fact.id,
            "title": self.fact.title,
            "detail_level": self.fact.detail_level,
            "children": [
                {
                    "relationship": rel.relationship_type,
                    "weight": rel.weight,
                    "node": child.as_dict(),
                }
                for rel, child in self.children
            ],
        }


# ---------------------------------------------------------------------------
# ReasoningEngine
# ---------------------------------------------------------------------------


class ReasoningEngine:
    """
    Graph-based reasoning over the FactDB relationship graph.

    The engine supports:
    * **Backward chaining** to collect prerequisites of a goal fact.
    * **Forward chaining** to derive consequences of known facts.
    * **Conflict detection** between a set of facts.
    * **Decision tree construction** from a root fact.

    Args:
        session: An active SQLAlchemy session bound to the FactDB database.
    """

    # Edges followed when collecting prerequisites (backward chaining)
    _PREREQ_EDGE_TYPES = {
        RelationshipType.DEPENDS_ON,
        RelationshipType.PREREQUISITE,
    }
    # Edges followed when deriving forward consequences
    _FORWARD_EDGE_TYPES = {
        RelationshipType.SUPPORTS,
        RelationshipType.DERIVED_FROM,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Backward chaining
    # ------------------------------------------------------------------

    def collect_prerequisites(
        self,
        goal_fact_id: str,
        max_depth: int = 10,
    ) -> InferenceResult:
        """
        Collect all prerequisite facts needed to reach *goal_fact_id*.

        Performs a BFS over DEPENDS_ON and PREREQUISITE edges in the
        *incoming* direction (i.e. "what does this fact depend on?").

        Args:
            goal_fact_id: PK of the target fact.
            max_depth:    Maximum graph traversal depth (default 10).

        Returns:
            :class:`InferenceResult` with the traversal chain, any conflicts,
            and any unverified prerequisites.

        Raises:
            ValueError: If the goal fact is not found.
        """
        goal = self.session.get(Fact, goal_fact_id)
        if goal is None:
            raise ValueError(f"Fact not found: {goal_fact_id!r}")

        visited: dict[str, Fact] = {}
        chain: list[Fact] = []
        queue: deque[tuple[Fact, int]] = deque([(goal, 0)])
        max_reached_depth = 0

        while queue:
            current, depth = queue.popleft()
            if current.id in visited or depth > max_depth:
                continue
            visited[current.id] = current
            chain.append(current)
            max_reached_depth = max(max_reached_depth, depth)

            # Follow outgoing DEPENDS_ON / PREREQUISITE edges:
            # "what facts does the current fact depend on?"
            for rel in current.outgoing_relationships:
                if rel.relationship_type in {rt.value for rt in self._PREREQ_EDGE_TYPES}:
                    if rel.target_fact_id not in visited:
                        queue.append((rel.target_fact, depth + 1))

        conflicts = self._find_conflicts(list(visited.values()))
        missing = [
            f for f in visited.values()
            if f.id != goal_fact_id
            and f.status != FactStatus.VERIFIED.value
        ]

        return InferenceResult(
            goal_fact=goal,
            chain=chain,
            conflicts=conflicts,
            missing_prereqs=missing,
            depth=max_reached_depth,
        )

    # ------------------------------------------------------------------
    # Forward chaining
    # ------------------------------------------------------------------

    def derive_consequences(
        self,
        known_fact_ids: list[str],
        max_depth: int = 5,
    ) -> list[Fact]:
        """
        Given a set of known facts, derive all facts that can be logically
        inferred by following SUPPORTS and DERIVED_FROM edges.

        Args:
            known_fact_ids: PKs of the initially known facts.
            max_depth:      Maximum traversal depth (default 5).

        Returns:
            List of newly derived :class:`~factdb.models.Fact` objects (does
            not include the originally known facts).
        """
        visited: set[str] = set(known_fact_ids)
        derived: list[Fact] = []
        queue: deque[tuple[str, int]] = deque((fid, 0) for fid in known_fact_ids)

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            stmt = (
                select(FactRelationship)
                .where(
                    FactRelationship.source_fact_id == current_id,
                    FactRelationship.relationship_type.in_(
                        [rt.value for rt in self._FORWARD_EDGE_TYPES]
                    ),
                )
            )
            for rel in self.session.execute(stmt).scalars().all():
                if rel.target_fact_id not in visited:
                    visited.add(rel.target_fact_id)
                    target = self.session.get(Fact, rel.target_fact_id)
                    if target and target.is_active:
                        derived.append(target)
                        queue.append((rel.target_fact_id, depth + 1))

        return derived

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self, fact_ids: list[str]) -> list[tuple[Fact, Fact]]:
        """
        Detect CONTRADICTS relationships within a given set of facts.

        Args:
            fact_ids: PKs of the facts to check.

        Returns:
            List of ``(fact_a, fact_b)`` tuples where a CONTRADICTS edge exists.
        """
        facts = [self.session.get(Fact, fid) for fid in fact_ids]
        facts = [f for f in facts if f is not None]
        return self._find_conflicts(facts)

    # ------------------------------------------------------------------
    # Decision tree construction
    # ------------------------------------------------------------------

    def build_decision_tree(
        self,
        root_fact_id: str,
        max_depth: int = 5,
        edge_types: set[RelationshipType] | None = None,
    ) -> DecisionNode:
        """
        Build a decision tree starting from *root_fact_id*.

        Each node expands its children by following the specified edge types
        in order of descending weight.  Cycles are detected and pruned.

        Args:
            root_fact_id: PK of the root fact.
            max_depth:    Maximum tree depth (default 5).
            edge_types:   Edge types to follow; defaults to all forward types
                          (SUPPORTS, DERIVED_FROM, DEPENDS_ON, EXAMPLE_OF).

        Returns:
            :class:`DecisionNode` representing the root of the tree.

        Raises:
            ValueError: If the root fact is not found.
        """
        if edge_types is None:
            edge_types = {
                RelationshipType.SUPPORTS,
                RelationshipType.DERIVED_FROM,
                RelationshipType.DEPENDS_ON,
                RelationshipType.EXAMPLE_OF,
            }

        root_fact = self.session.get(Fact, root_fact_id)
        if root_fact is None:
            raise ValueError(f"Fact not found: {root_fact_id!r}")

        return self._build_node(root_fact, edge_types, visited=set(), depth=0, max_depth=max_depth)

    # ------------------------------------------------------------------
    # Expert system: rule evaluation
    # ------------------------------------------------------------------

    def evaluate_applicability(
        self, fact_id: str, context_fact_ids: list[str]
    ) -> dict:
        """
        Check whether a fact is applicable given a context (set of known facts).

        A fact is *applicable* if:
        1. It is VERIFIED.
        2. All of its DEPENDS_ON / PREREQUISITE parents are present in
           *context_fact_ids*.
        3. None of its CONTRADICTS peers are present in *context_fact_ids*.

        Args:
            fact_id:          PK of the candidate fact.
            context_fact_ids: PKs of currently known/true facts.

        Returns:
            Dictionary with keys:
              - ``applicable`` (bool)
              - ``missing_prereqs`` (list of fact titles)
              - ``conflicts`` (list of fact titles)
              - ``reason`` (human-readable explanation)
        """
        fact = self.session.get(Fact, fact_id)
        if fact is None:
            raise ValueError(f"Fact not found: {fact_id!r}")

        context_set = set(context_fact_ids)
        missing_prereqs: list[str] = []
        conflicts: list[str] = []

        for rel in fact.outgoing_relationships:
            if rel.relationship_type in {
                RelationshipType.DEPENDS_ON.value,
                RelationshipType.PREREQUISITE.value,
            }:
                if rel.target_fact_id not in context_set:
                    tgt = self.session.get(Fact, rel.target_fact_id)
                    missing_prereqs.append(tgt.title if tgt else rel.target_fact_id)

        for rel in fact.outgoing_relationships:
            if rel.relationship_type == RelationshipType.CONTRADICTS.value:
                if rel.target_fact_id in context_set:
                    tgt = self.session.get(Fact, rel.target_fact_id)
                    conflicts.append(tgt.title if tgt else rel.target_fact_id)

        applicable = (
            fact.status == FactStatus.VERIFIED.value
            and not missing_prereqs
            and not conflicts
        )
        reason_parts = []
        if fact.status != FactStatus.VERIFIED.value:
            reason_parts.append(f"fact is not verified (status={fact.status!r})")
        if missing_prereqs:
            reason_parts.append(f"missing prerequisites: {missing_prereqs}")
        if conflicts:
            reason_parts.append(f"conflicts with context: {conflicts}")

        return {
            "applicable": applicable,
            "missing_prereqs": missing_prereqs,
            "conflicts": conflicts,
            "reason": "; ".join(reason_parts) if reason_parts else "all conditions met",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_conflicts(self, facts: list[Fact]) -> list[tuple[Fact, Fact]]:
        fact_ids = {f.id for f in facts}
        fact_map = {f.id: f for f in facts}
        conflicts: list[tuple[Fact, Fact]] = []

        for fact in facts:
            for rel in fact.outgoing_relationships:
                if (
                    rel.relationship_type == RelationshipType.CONTRADICTS.value
                    and rel.target_fact_id in fact_ids
                ):
                    a = fact_map[rel.source_fact_id]
                    b = fact_map[rel.target_fact_id]
                    # Avoid duplicate pairs
                    pair = tuple(sorted([a.id, b.id]))
                    if not any(
                        tuple(sorted([x.id, y.id])) == pair for x, y in conflicts
                    ):
                        conflicts.append((a, b))

        return conflicts

    def _build_node(
        self,
        fact: Fact,
        edge_types: set[RelationshipType],
        visited: set[str],
        depth: int,
        max_depth: int,
    ) -> DecisionNode:
        node = DecisionNode(fact=fact)
        if depth >= max_depth or fact.id in visited:
            return node

        visited = visited | {fact.id}  # immutable copy for this branch

        # Sort children by weight descending
        relevant_rels = sorted(
            [
                rel for rel in fact.outgoing_relationships
                if rel.relationship_type in {et.value for et in edge_types}
                and rel.target_fact_id not in visited
            ],
            key=lambda r: r.weight,
            reverse=True,
        )

        for rel in relevant_rels:
            child_fact = rel.target_fact
            if child_fact and child_fact.is_active:
                child_node = self._build_node(
                    child_fact, edge_types, visited, depth + 1, max_depth
                )
                node.children.append((rel, child_node))

        return node
