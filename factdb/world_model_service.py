"""
Service layer for world-model ingestion, fusion, anomaly handling, and planning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.world_model import (
    AnomalyCase,
    AnomalyStatus,
    Modality,
    ObjectiveRecord,
    ObjectiveStatus,
    ObservationEvent,
    SensorHealth,
    SkillFunction,
    SkillKind,
    StateEstimate,
    StateHypothesis,
    WorldEntity,
    WorldEntityType,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Baseline prior scores and residual multipliers used for anomaly diagnosis.
_ANOMALY_CAUSE_WEIGHTS: dict[str, tuple[float, float]] = {
    "sensor_fault": (0.25, 0.35),
    "model_gap": (0.25, 0.25),
    "environment_change": (0.2, 0.2),
    "bad_calibration": (0.1, 0.2),
    "unmodeled_physics": (0.1, 0.2),
}

# Ranking policy constants for hierarchical planner skill selection.
_SKILL_COST_WEIGHT = 0.1
_SKILL_LATENCY_NORMALIZER_MS = 10000.0
_EPSILON = 1e-9


@dataclass
class ObservationInput:
    entity_id: str
    property_name: str
    value: Any
    confidence: float
    source_modality: Modality
    source_sensor_id: str | None = None
    processing_method: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    raw_payload: dict[str, Any] | None = None


class WorldModelService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Entity + skill registry
    # ------------------------------------------------------------------
    def ensure_entity(
        self,
        name: str,
        entity_type: WorldEntityType,
        *,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorldEntity:
        stmt = select(WorldEntity).where(
            WorldEntity.name == name,
            WorldEntity.entity_type == entity_type,
        )
        entity = self.session.execute(stmt).scalar_one_or_none()
        if entity is None:
            entity = WorldEntity(name=name, entity_type=entity_type, parent_id=parent_id)
            entity.set_metadata(metadata)
            self.session.add(entity)
            self.session.flush()
        return entity

    def register_skill(
        self,
        *,
        name: str,
        kind: SkillKind,
        input_schema: dict[str, Any] | list[dict[str, Any]] | None = None,
        output_schema: dict[str, Any] | list[dict[str, Any]] | None = None,
        cost_score: float = 1.0,
        latency_ms: float = 0.0,
        reliability_score: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> SkillFunction:
        stmt = select(SkillFunction).where(SkillFunction.name == name, SkillFunction.kind == kind)
        skill = self.session.execute(stmt).scalar_one_or_none()
        if skill is None:
            skill = SkillFunction(name=name, kind=kind)
            self.session.add(skill)
        skill.input_schema_json = json.dumps(input_schema or {}, ensure_ascii=False)
        skill.output_schema_json = json.dumps(output_schema or {}, ensure_ascii=False)
        skill.cost_score = cost_score
        skill.latency_ms = latency_ms
        skill.reliability_score = reliability_score
        skill.metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        self.session.flush()
        return skill

    # ------------------------------------------------------------------
    # Ingestion + fusion
    # ------------------------------------------------------------------
    def ingest_observation(self, observation: ObservationInput) -> ObservationEvent:
        event = ObservationEvent(
            entity_id=observation.entity_id,
            source_sensor_id=observation.source_sensor_id,
            property_name=observation.property_name,
            confidence=max(0.0, min(1.0, observation.confidence)),
            source_modality=observation.source_modality,
            valid_from=observation.valid_from,
            valid_to=observation.valid_to,
            processing_method=observation.processing_method,
            raw_payload_json=json.dumps(observation.raw_payload or {}, ensure_ascii=False),
        )
        event.set_value(observation.value)
        self.session.add(event)
        self.session.flush()
        if observation.source_sensor_id:
            self._mark_sensor_seen(observation.source_sensor_id)
        return event

    def fuse_state(
        self,
        *,
        entity_id: str,
        property_name: str,
        limit: int = 20,
        method: str = "weighted_consensus",
    ) -> StateEstimate | None:
        observations = self._latest_observations(entity_id=entity_id, property_name=property_name, limit=limit)
        if not observations:
            return None

        values = [obs.get_value() for obs in observations]
        confidences = [obs.confidence for obs in observations]
        fused_value = self._fuse_values(values=values, confidences=confidences)
        total_confidence = sum(confidences)
        # Confidence-weighted confidence score:
        # sum(c_i^2) / sum(c_i), equivalent to a confidence self-weighted mean
        # that increases when more mass sits on high-confidence observations.
        fused_confidence = (
            sum(confidence * confidence for confidence in confidences) / total_confidence
            if total_confidence > _EPSILON
            else 0.0
        )

        estimate = StateEstimate(
            entity_id=entity_id,
            property_name=property_name,
            confidence=max(0.0, min(1.0, fused_confidence)),
            fusion_method=method,
            valid_from=min((o.valid_from or o.observed_at) for o in observations),
            valid_to=max((o.valid_to or o.observed_at) for o in observations),
        )
        estimate.set_value(fused_value)
        estimate.set_source_observation_ids([obs.id for obs in observations])
        self.session.add(estimate)
        self.session.flush()
        return estimate

    def create_hypotheses(
        self,
        *,
        state_estimate_id: str,
        hypotheses: Iterable[dict[str, Any]],
    ) -> list[StateHypothesis]:
        created: list[StateHypothesis] = []
        for item in hypotheses:
            hypothesis = StateHypothesis(
                state_estimate_id=state_estimate_id,
                hypothesis_label=item.get("label", "hypothesis"),
                explanation=item.get("explanation"),
                probability=float(item.get("probability", 0.0)),
                source=item.get("source"),
                is_selected=bool(item.get("is_selected", False)),
            )
            self.session.add(hypothesis)
            created.append(hypothesis)
        self.session.flush()
        return created

    # ------------------------------------------------------------------
    # Alignment + anomaly handling
    # ------------------------------------------------------------------
    def align_expected_state(
        self,
        *,
        entity_id: str,
        property_name: str,
        expected_value: Any,
        tolerance: float = 0.0,
    ) -> tuple[float, AnomalyCase | None]:
        estimate = self._latest_state_estimate(entity_id=entity_id, property_name=property_name)
        if estimate is None:
            anomaly = self._open_anomaly(
                entity_id=entity_id,
                property_name=property_name,
                expected_value=expected_value,
                observed_value=None,
                residual_score=1.0,
                evidence={"reason": "no_state_estimate"},
            )
            return 1.0, anomaly

        observed_value = estimate.get_value()
        residual = self._compute_residual(expected_value, observed_value, tolerance=tolerance)
        if residual <= 0:
            return residual, None

        anomaly = self._open_anomaly(
            entity_id=entity_id,
            property_name=property_name,
            expected_value=expected_value,
            observed_value=observed_value,
            residual_score=residual,
            evidence={"state_estimate_id": estimate.id},
        )
        return residual, anomaly

    def diagnose_anomaly(self, anomaly_id: str) -> AnomalyCase:
        anomaly = self.session.get(AnomalyCase, anomaly_id)
        if anomaly is None:
            raise ValueError(f"Anomaly not found: {anomaly_id!r}")

        normalized_residual = max(0.0, min(anomaly.residual_score, 1.0))
        scores = {
            cause: baseline + normalized_residual * multiplier
            for cause, (baseline, multiplier) in _ANOMALY_CAUSE_WEIGHTS.items()
        }

        diagnosis = sorted(
            [{"cause": cause, "score": round(score, 3)} for cause, score in scores.items()],
            key=lambda item: item["score"],
            reverse=True,
        )

        anomaly.status = AnomalyStatus.INVESTIGATING
        anomaly.set_diagnosis(diagnosis)
        self.session.flush()
        return anomaly

    def resolve_anomaly(self, anomaly_id: str, *, action: str, evidence: dict[str, Any] | None = None) -> AnomalyCase:
        anomaly = self.session.get(AnomalyCase, anomaly_id)
        if anomaly is None:
            raise ValueError(f"Anomaly not found: {anomaly_id!r}")
        anomaly.status = AnomalyStatus.RESOLVED
        anomaly.resolution_action = action
        anomaly.resolved_at = _utcnow()
        if evidence is not None:
            anomaly.set_evidence(evidence)
        self.session.flush()
        return anomaly

    # ------------------------------------------------------------------
    # Objective grounding + hierarchical planning
    # ------------------------------------------------------------------
    def ingest_objective(
        self,
        *,
        raw_input: dict[str, Any],
        modality: Modality,
        canonical_task_graph: dict[str, Any] | None,
        intent_confidence: float,
        clarification_threshold: float = 0.65,
    ) -> ObjectiveRecord:
        confidence = max(0.0, min(1.0, intent_confidence))
        needs_clarification = confidence < clarification_threshold
        objective = ObjectiveRecord(
            modality=modality,
            raw_input_json=json.dumps(raw_input, ensure_ascii=False),
            canonical_task_graph_json=json.dumps(canonical_task_graph or {}, ensure_ascii=False),
            intent_confidence=confidence,
            status=ObjectiveStatus.NEEDS_CLARIFICATION if needs_clarification else ObjectiveStatus.PLANNED,
            clarification_requested=needs_clarification,
        )
        self.session.add(objective)
        self.session.flush()
        return objective

    def build_hierarchical_plan(self, *, objective_id: str) -> dict[str, Any]:
        objective = self.session.get(ObjectiveRecord, objective_id)
        if objective is None:
            raise ValueError(f"Objective not found: {objective_id!r}")

        active_skills = self.session.execute(
            select(SkillFunction).where(SkillFunction.is_active.is_(True))
        ).scalars().all()
        ranked = sorted(
            active_skills,
            key=lambda skill: (
                max(
                    0.0,
                    skill.reliability_score
                    - skill.cost_score * _SKILL_COST_WEIGHT
                    - skill.latency_ms / _SKILL_LATENCY_NORMALIZER_MS,
                )
            ),
            reverse=True,
        )

        objective.status = ObjectiveStatus.EXECUTING
        self.session.flush()

        return {
            "objective_id": objective.id,
            "strategic": {
                "policy": "maximize_expected_success",
                "intent_confidence": objective.intent_confidence,
            },
            "tactical": {
                "selected_skills": [skill.name for skill in ranked[:3]],
            },
            "reactive": {
                "safety_mode": "enabled",
                "fallback_action": "request_human_override",
            },
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _mark_sensor_seen(self, sensor_entity_id: str) -> None:
        health = self.session.execute(
            select(SensorHealth).where(SensorHealth.sensor_entity_id == sensor_entity_id)
        ).scalar_one_or_none()
        if health is None:
            health = SensorHealth(sensor_entity_id=sensor_entity_id)
            self.session.add(health)
        health.last_seen_at = _utcnow()
        self.session.flush()

    def _latest_observations(self, *, entity_id: str, property_name: str, limit: int) -> list[ObservationEvent]:
        stmt = (
            select(ObservationEvent)
            .where(
                ObservationEvent.entity_id == entity_id,
                ObservationEvent.property_name == property_name,
            )
            .order_by(ObservationEvent.observed_at.desc())
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()

    def _latest_state_estimate(self, *, entity_id: str, property_name: str) -> StateEstimate | None:
        stmt = (
            select(StateEstimate)
            .where(
                StateEstimate.entity_id == entity_id,
                StateEstimate.property_name == property_name,
            )
            .order_by(StateEstimate.updated_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _fuse_values(*, values: list[Any], confidences: list[float]) -> Any:
        if not values:
            return None
        if all(isinstance(value, (int, float)) for value in values):
            total_weight = sum(confidences)
            if total_weight <= _EPSILON:
                return sum(values) / len(values)
            return sum(value * confidence for value, confidence in zip(values, confidences)) / total_weight

        weighted: dict[str, float] = {}
        for value, confidence in zip(values, confidences):
            key = json.dumps(value, sort_keys=True)
            weighted[key] = weighted.get(key, 0.0) + confidence
        winner = max(weighted.items(), key=lambda item: item[1])[0]
        return json.loads(winner)

    @staticmethod
    def _compute_residual(expected: Any, observed: Any, *, tolerance: float) -> float:
        if isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
            diff = abs(float(expected) - float(observed))
            if diff <= tolerance:
                return 0.0
            return diff
        return 0.0 if expected == observed else 1.0

    def _open_anomaly(
        self,
        *,
        entity_id: str,
        property_name: str,
        expected_value: Any,
        observed_value: Any,
        residual_score: float,
        evidence: dict[str, Any] | None,
    ) -> AnomalyCase:
        anomaly = AnomalyCase(
            entity_id=entity_id,
            property_name=property_name,
            residual_score=residual_score,
            status=AnomalyStatus.OPEN,
        )
        anomaly.set_expected(expected_value)
        anomaly.set_observed(observed_value)
        anomaly.set_evidence(evidence or {})
        self.session.add(anomaly)
        self.session.flush()
        return anomaly
