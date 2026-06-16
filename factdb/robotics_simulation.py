"""
Deterministic FPS-style robotics simulation workflow for FactDB.

This module simulates a first-person navigation episode, ingests each step into
FactDB as draft facts, validates quality/integrity, repairs missing/invalid
records, and replays the same scenario to compare before/after stability.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import DetailLevel, EngineeringDomain, Fact, FactRelationship, FactStatus, RelationshipType
from factdb.repository import FactRepository
from factdb.verification import VerificationWorkflow


_DIRECTION_ORDER = ("N", "E", "S", "W")
_DIRECTION_VECTORS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}
_SUCCESS_CONFIDENCE = 0.9
_FAILURE_CONFIDENCE = 0.35
_REFILL_MIN_CONFIDENCE = 0.8


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass
class EpisodeStep:
    step_index: int
    action: str
    observation: dict[str, Any]
    outcome: str
    confidence: float
    source_url: str


@dataclass
class SimulationEpisode:
    episode_id: str
    scenario_name: str
    objective: str
    steps: list[EpisodeStep]
    success: bool
    collisions: int
    reached_target: bool


class FPSGridSimulator:
    """Simple deterministic first-person grid simulation."""

    DEFAULT_MAP = (
        "#########",
        "#S.#..T.#",
        "#..#....#",
        "#.......#",
        "#########",
    )

    def __init__(self, scenario_name: str = "arena-alpha", grid_layout: tuple[str, ...] | None = None) -> None:
        self.scenario_name = scenario_name
        self.grid_map = grid_layout or self.DEFAULT_MAP
        self._episode_counter = 0
        self.start = self._find_marker("S")
        self.target = self._find_marker("T")
        self.reset()

    def reset(self) -> None:
        self.position = self.start
        self.heading = "N"

    def run_episode(self, *, max_steps: int = 64) -> SimulationEpisode:
        self._episode_counter += 1
        episode_id = f"{self.scenario_name}-{self._episode_counter:04d}"
        steps: list[EpisodeStep] = []
        collisions = 0

        # Intentionally probe once at start (often blocked), then navigate.
        outcome = self._apply_action("move_forward")
        if outcome == "collision":
            collisions += 1
        steps.append(
            self._make_step(
                episode_id=episode_id,
                step_index=len(steps) + 1,
                action="move_forward",
                outcome=outcome,
            )
        )

        while len(steps) < max_steps and self.position != self.target:
            route = self._shortest_path(self.position, self.target)
            if len(route) < 2:
                break
            next_cell = route[1]
            desired_heading = self._heading_to(self.position, next_cell)
            if self.heading != desired_heading:
                turn_action = self._turn_towards(desired_heading)
                outcome = self._apply_action(turn_action)
                steps.append(
                    self._make_step(
                        episode_id=episode_id,
                        step_index=len(steps) + 1,
                        action=turn_action,
                        outcome=outcome,
                    )
                )
                continue

            outcome = self._apply_action("move_forward")
            if outcome == "collision":
                collisions += 1
            steps.append(
                self._make_step(
                    episode_id=episode_id,
                    step_index=len(steps) + 1,
                    action="move_forward",
                    outcome=outcome,
                )
            )

        if self.position == self.target and len(steps) < max_steps:
            outcome = self._apply_action("interact")
            steps.append(
                self._make_step(
                    episode_id=episode_id,
                    step_index=len(steps) + 1,
                    action="interact",
                    outcome=outcome,
                )
            )

        return SimulationEpisode(
            episode_id=episode_id,
            scenario_name=self.scenario_name,
            objective="Navigate FPS arena, avoid obstacles, and interact with target.",
            steps=steps,
            success=(self.position == self.target and any(s.action == "interact" for s in steps)),
            collisions=collisions,
            reached_target=(self.position == self.target),
        )

    def _make_step(self, *, episode_id: str, step_index: int, action: str, outcome: str) -> EpisodeStep:
        confidence = _SUCCESS_CONFIDENCE if outcome in {"ok", "target_interacted"} else _FAILURE_CONFIDENCE
        source_url = f"sim://fps/{self.scenario_name}/{episode_id}/step/{step_index}"
        return EpisodeStep(
            step_index=step_index,
            action=action,
            observation=self._observe(),
            outcome=outcome,
            confidence=confidence,
            source_url=source_url,
        )

    def _apply_action(self, action: str) -> str:
        if action == "turn_left":
            idx = _DIRECTION_ORDER.index(self.heading)
            self.heading = _DIRECTION_ORDER[(idx - 1) % len(_DIRECTION_ORDER)]
            return "ok"
        if action == "turn_right":
            idx = _DIRECTION_ORDER.index(self.heading)
            self.heading = _DIRECTION_ORDER[(idx + 1) % len(_DIRECTION_ORDER)]
            return "ok"
        if action == "interact":
            return "target_interacted" if self.position == self.target else "no_target"

        if action == "move_forward":
            dx, dy = _DIRECTION_VECTORS[self.heading]
            nx, ny = self.position[0] + dx, self.position[1] + dy
            if self._is_wall((nx, ny)):
                return "collision"
            self.position = (nx, ny)
            return "ok"

        return "invalid_action"

    def _observe(self) -> dict[str, Any]:
        dx, dy = _DIRECTION_VECTORS[self.heading]
        front = (self.position[0] + dx, self.position[1] + dy)
        return {
            "position": {"x": self.position[0], "y": self.position[1]},
            "heading": self.heading,
            "obstacle_ahead": self._is_wall(front),
            "target_visible": self._target_visible(),
            "distance_to_target": abs(self.target[0] - self.position[0]) + abs(self.target[1] - self.position[1]),
        }

    def _target_visible(self) -> bool:
        dx, dy = _DIRECTION_VECTORS[self.heading]
        x, y = self.position
        while True:
            x += dx
            y += dy
            if self._is_wall((x, y)):
                return False
            if (x, y) == self.target:
                return True

    def _is_wall(self, cell: tuple[int, int]) -> bool:
        x, y = cell
        if y < 0 or y >= len(self.grid_map) or x < 0 or x >= len(self.grid_map[0]):
            return True
        return self.grid_map[y][x] == "#"

    def _find_marker(self, marker: str) -> tuple[int, int]:
        for y, row in enumerate(self.grid_map):
            x = row.find(marker)
            if x != -1:
                return (x, y)
        raise ValueError(f"Missing marker in map: {marker!r}")

    def _shortest_path(self, start: tuple[int, int], target: tuple[int, int]) -> list[tuple[int, int]]:
        q = deque([(start, [start])])
        seen = {start}
        while q:
            node, path = q.popleft()
            if node == target:
                return path
            for dx, dy in _DIRECTION_VECTORS.values():
                nxt = (node[0] + dx, node[1] + dy)
                if nxt in seen or self._is_wall(nxt):
                    continue
                seen.add(nxt)
                q.append((nxt, path + [nxt]))
        return [start]

    @staticmethod
    def _heading_to(src: tuple[int, int], dst: tuple[int, int]) -> str:
        dx, dy = (dst[0] - src[0], dst[1] - src[1])
        for direction, vector in _DIRECTION_VECTORS.items():
            if vector == (dx, dy):
                return direction
        raise ValueError(f"Unsupported heading transition: {src} -> {dst}")

    def _turn_towards(self, desired_heading: str) -> str:
        curr = _DIRECTION_ORDER.index(self.heading)
        dest = _DIRECTION_ORDER.index(desired_heading)
        right_steps = (dest - curr) % len(_DIRECTION_ORDER)
        left_steps = (curr - dest) % len(_DIRECTION_ORDER)
        return "turn_right" if right_steps <= left_steps else "turn_left"


class RoboticsSimulationWorkflow:
    """Run the complete simulation->ingest->validate->refill->replay loop."""

    def __init__(self, session: Session, *, scenario_name: str = "arena-alpha") -> None:
        self.session = session
        self.repo = FactRepository(session)
        self.workflow = VerificationWorkflow(session)
        self.simulator = FPSGridSimulator(scenario_name=scenario_name)

    def run_iteration(self, *, max_steps: int = 64, inject_loss: bool = True) -> dict[str, Any]:
        baseline_count = self._count_sim_facts()

        self.simulator.reset()
        episode = self.simulator.run_episode(max_steps=max_steps)
        ingested_fact_ids = self._ingest_episode(episode)
        validation = self._validate_fact_batch(ingested_fact_ids)

        corruption = {"deactivated": 0, "degraded": 0}
        if inject_loss:
            corruption = self._inject_loss_and_corruption(ingested_fact_ids)

        refill = self._refill_from_episode(episode)

        self.simulator.reset()
        replay = self.simulator.run_episode(max_steps=max_steps)

        final_count = self._count_sim_facts()
        success_criteria = {
            "stable_task_completion": episode.success and replay.success,
            "consistent_fact_graph_growth": final_count >= baseline_count,
            "no_integrity_regressions": refill["post_validation"]["invalid_count"] == 0,
        }

        return {
            "scenario": episode.scenario_name,
            "episode_id": episode.episode_id,
            "objective": episode.objective,
            "baseline_fact_count": baseline_count,
            "final_fact_count": final_count,
            "episode": {
                "steps": len(episode.steps),
                "success": episode.success,
                "collisions": episode.collisions,
            },
            "validation": validation,
            "corruption": corruption,
            "refill": refill,
            "replay": {
                "steps": len(replay.steps),
                "success": replay.success,
                "collisions": replay.collisions,
                "replay_consistent": [s.action for s in replay.steps] == [s.action for s in episode.steps],
            },
            "success_criteria": success_criteria,
        }

    def run_iterations(self, *, iterations: int = 1, max_steps: int = 64, inject_loss: bool = True) -> dict[str, Any]:
        reports = [
            self.run_iteration(max_steps=max_steps, inject_loss=inject_loss)
            for _ in range(max(1, iterations))
        ]
        return {
            "iterations": reports,
            "all_successful": all(
                r["success_criteria"]["stable_task_completion"]
                and r["success_criteria"]["no_integrity_regressions"]
                for r in reports
            ),
        }

    def _ingest_episode(self, episode: SimulationEpisode) -> list[str]:
        fact_ids: list[str] = []

        for step in episode.steps:
            fact = self.repo.create(
                title=f"[RoboticsSim] {episode.episode_id} step {step.step_index}: {step.action}",
                content=(
                    f"Action={step.action}; Outcome={step.outcome}; "
                    f"Observation={json.dumps(step.observation, sort_keys=True)}"
                ),
                domain=EngineeringDomain.SYSTEMS,
                category="robotics",
                subcategory="fps-simulation",
                detail_level=DetailLevel.INTERMEDIATE,
                source="robotics-fps-sim",
                source_url=step.source_url,
                confidence_score=step.confidence,
                status=FactStatus.DRAFT,
                tags=[
                    "robotics-sim",
                    "fps-sim",
                    episode.scenario_name,
                    f"action:{step.action}",
                    f"outcome:{step.outcome}",
                ],
                created_by="robotics-sim",
            )
            fact_ids.append(fact.id)

        for src_id, dst_id in zip(fact_ids, fact_ids[1:]):
            self.repo.add_relationship(
                source_id=src_id,
                target_id=dst_id,
                relationship_type=RelationshipType.DEPENDS_ON,
                weight=1.0,
                description="Episode step dependency chain",
            )

        self.session.flush()
        return fact_ids

    def _validate_fact_batch(self, fact_ids: list[str], *, min_confidence: float = 0.6) -> dict[str, Any]:
        valid_ids: list[str] = []
        invalid: dict[str, list[str]] = {}

        for fact_id in fact_ids:
            fact = self.session.get(Fact, fact_id)
            if fact is None or not fact.is_active:
                invalid[fact_id] = ["missing_or_inactive"]
                continue

            reasons: list[str] = []
            if not fact.title or not fact.content or not fact.source_url:
                reasons.append("schema_invalid")

            duplicates = self.session.execute(
                select(Fact)
                .where(Fact.source_url == fact.source_url, Fact.is_active.is_(True))
            ).scalars().all()
            if len(duplicates) > 1:
                reasons.append("duplicate_source_url")

            if fact.confidence_score < min_confidence:
                reasons.append("low_confidence")

            out_edges = self.session.execute(
                select(FactRelationship).where(FactRelationship.source_fact_id == fact.id)
            ).scalars().all()
            for edge in out_edges:
                target = self.session.get(Fact, edge.target_fact_id)
                if target is None or not target.is_active:
                    reasons.append("broken_relationship")
                    break

            if reasons:
                invalid[fact_id] = reasons
                continue

            if fact.status == FactStatus.DRAFT.value:
                self.workflow.submit_for_review(fact.id, submitted_by="robotics-validator")
                self.workflow.approve(fact.id, verified_by="robotics-validator", notes="Simulation validation passed")
            valid_ids.append(fact.id)

        self.session.flush()
        return {
            "validated": len(fact_ids),
            "valid_count": len(valid_ids),
            "invalid_count": len(invalid),
            "invalid_reasons": invalid,
        }

    def _inject_loss_and_corruption(self, fact_ids: list[str]) -> dict[str, int]:
        if not fact_ids:
            return {"deactivated": 0, "degraded": 0}

        deactivated = 0
        degraded = 0

        first = self.session.get(Fact, fact_ids[0])
        if first is not None:
            first.is_active = False
            deactivated += 1

        second = self.session.get(Fact, fact_ids[1]) if len(fact_ids) > 1 else None
        if second is not None:
            second.confidence_score = 0.2
            second.status = FactStatus.DRAFT
            degraded += 1

        self.session.flush()
        return {"deactivated": deactivated, "degraded": degraded}

    def _refill_from_episode(self, episode: SimulationEpisode) -> dict[str, Any]:
        repaired_or_created = 0
        touched_ids: list[str] = []

        for step in episode.steps:
            fact = self.session.execute(
                select(Fact).where(Fact.source_url == step.source_url).order_by(Fact.created_at.desc())
            ).scalars().first()

            if fact is None:
                fact = self.repo.create(
                    title=f"[RoboticsSim] {episode.episode_id} step {step.step_index}: {step.action} (refill)",
                    content=(
                        f"Refilled from simulation log. Action={step.action}; Outcome={step.outcome}; "
                        f"Observation={json.dumps(step.observation, sort_keys=True)}"
                    ),
                    domain=EngineeringDomain.SYSTEMS,
                    category="robotics",
                    subcategory="fps-simulation",
                    detail_level=DetailLevel.INTERMEDIATE,
                    source="robotics-fps-sim",
                    source_url=step.source_url,
                    confidence_score=max(_REFILL_MIN_CONFIDENCE, step.confidence),
                    status=FactStatus.DRAFT,
                    tags=["robotics-sim", "fps-sim", "refilled", episode.scenario_name],
                    created_by="robotics-refill",
                )
                repaired_or_created += 1
                touched_ids.append(fact.id)
                continue

            changed = False
            if not fact.is_active:
                fact.is_active = True
                changed = True
            if fact.confidence_score < 0.6:
                fact.confidence_score = max(_REFILL_MIN_CONFIDENCE, step.confidence)
                changed = True
            if fact.status != FactStatus.VERIFIED.value:
                fact.status = FactStatus.DRAFT
                changed = True
            if changed:
                repaired_or_created += 1
                touched_ids.append(fact.id)

        self.session.flush()

        scenario = _escape_like(episode.scenario_name)
        episode_id = _escape_like(episode.episode_id)
        active_step_facts = self.session.execute(
            select(Fact)
            .where(
                Fact.source_url.like(
                    f"sim://fps/{scenario}/{episode_id}/step/%",
                    escape="\\",
                ),
                Fact.is_active.is_(True),
            )
            .order_by(Fact.source_url.asc())
        ).scalars().all()

        for src, dst in zip(active_step_facts, active_step_facts[1:]):
            rel = self.session.execute(
                select(FactRelationship).where(
                    FactRelationship.source_fact_id == src.id,
                    FactRelationship.target_fact_id == dst.id,
                    FactRelationship.relationship_type == RelationshipType.DEPENDS_ON,
                )
            ).scalar_one_or_none()
            if rel is None:
                self.repo.add_relationship(
                    source_id=src.id,
                    target_id=dst.id,
                    relationship_type=RelationshipType.DEPENDS_ON,
                    weight=1.0,
                    description="Refilled episode dependency chain",
                )

        self.session.flush()
        post_validation = self._validate_fact_batch([fact.id for fact in active_step_facts])
        return {
            "repaired_or_created": repaired_or_created,
            "touched_count": len(set(touched_ids)),
            "post_validation": post_validation,
        }

    def _count_sim_facts(self) -> int:
        return len(
            self.session.execute(
                select(Fact).where(
                    Fact.source_url.like("sim://fps/%"),
                    Fact.is_active.is_(True),
                )
            ).scalars().all()
        )
