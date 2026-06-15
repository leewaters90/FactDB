"""
World-model ORM schema for robotics-oriented state tracking in FactDB.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from factdb.models import Base, Fact, _new_uuid, _utcnow


class Modality(str, PyEnum):
    VIDEO = "video"
    SFM = "sfm"
    GPS = "gps"
    DISTANCE = "distance"
    MOISTURE = "moisture"
    AUDIO = "audio"
    TEXT = "text"
    SPEECH = "speech"
    GESTURE = "gesture"
    LIDAR = "lidar"
    IMU = "imu"
    OTHER = "other"


class WorldEntityType(str, PyEnum):
    ROBOT = "robot"
    SCENE_OBJECT = "scene_object"
    TERRAIN_CELL = "terrain_cell"
    REGION = "region"
    TASK = "task"
    CONSTRAINT = "constraint"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    OBJECTIVE = "objective"


class AnomalyStatus(str, PyEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class ObjectiveStatus(str, PyEnum):
    RECEIVED = "received"
    NEEDS_CLARIFICATION = "needs_clarification"
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"


class ModelLinkType(str, PyEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"


class SkillKind(str, PyEnum):
    FUNCTION = "function"
    TRANSFORM = "transform"
    TOOL = "tool"
    AGENT = "agent"


class WorldEntity(Base):
    __tablename__ = "world_entities"
    __table_args__ = (
        Index("ix_world_entities_type", "entity_type"),
        Index("ix_world_entities_parent", "parent_id"),
        UniqueConstraint("name", "entity_type", name="uq_world_entity_name_type"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    name: str = Column(String(200), nullable=False, index=True)
    entity_type: str = Column(Enum(WorldEntityType), nullable=False, index=True)
    parent_id: str | None = Column(
        String(36),
        ForeignKey("world_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: str | None = Column(Text, nullable=True)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    parent = relationship("WorldEntity", remote_side=[id], back_populates="children")
    children = relationship("WorldEntity", back_populates="parent")
    observations = relationship(
        "ObservationEvent",
        foreign_keys="ObservationEvent.entity_id",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    state_estimates = relationship("StateEstimate", back_populates="entity", cascade="all, delete-orphan")

    def get_metadata(self) -> dict[str, Any]:
        if not self.metadata_json:
            return {}
        return json.loads(self.metadata_json)

    def set_metadata(self, payload: dict[str, Any] | None) -> None:
        self.metadata_json = json.dumps(payload or {}, ensure_ascii=False)


class ObservationEvent(Base):
    __tablename__ = "observation_events"
    __table_args__ = (
        Index("ix_observation_entity_prop_time", "entity_id", "property_name", "observed_at"),
        Index("ix_observation_modality", "source_modality"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    entity_id: str = Column(String(36), ForeignKey("world_entities.id", ondelete="CASCADE"), nullable=False)
    source_sensor_id: str | None = Column(String(36), ForeignKey("world_entities.id", ondelete="SET NULL"), nullable=True)
    property_name: str = Column(String(150), nullable=False, index=True)
    value_json: str = Column(Text, nullable=False)
    confidence: float = Column(Float, nullable=False, default=1.0)
    source_modality: str = Column(Enum(Modality), nullable=False, default=Modality.OTHER)
    observed_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    valid_from: datetime | None = Column(DateTime(timezone=True), nullable=True)
    valid_to: datetime | None = Column(DateTime(timezone=True), nullable=True)
    processing_method: str | None = Column(String(200), nullable=True)
    raw_payload_json: str | None = Column(Text, nullable=True)

    entity = relationship("WorldEntity", foreign_keys=[entity_id], back_populates="observations")
    source_sensor = relationship("WorldEntity", foreign_keys=[source_sensor_id])

    def get_value(self) -> Any:
        return json.loads(self.value_json)

    def set_value(self, value: Any) -> None:
        self.value_json = json.dumps(value, ensure_ascii=False)


class StateEstimate(Base):
    __tablename__ = "state_estimates"
    __table_args__ = (
        Index("ix_state_entity_prop_updated", "entity_id", "property_name", "updated_at"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    entity_id: str = Column(String(36), ForeignKey("world_entities.id", ondelete="CASCADE"), nullable=False)
    property_name: str = Column(String(150), nullable=False, index=True)
    value_json: str = Column(Text, nullable=False)
    confidence: float = Column(Float, nullable=False, default=0.5)
    fusion_method: str = Column(String(100), nullable=False, default="weighted_consensus")
    source_observation_ids_json: str | None = Column(Text, nullable=True)
    valid_from: datetime | None = Column(DateTime(timezone=True), nullable=True)
    valid_to: datetime | None = Column(DateTime(timezone=True), nullable=True)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, index=True)

    entity = relationship("WorldEntity", back_populates="state_estimates")
    hypotheses = relationship("StateHypothesis", back_populates="state_estimate", cascade="all, delete-orphan")

    def get_value(self) -> Any:
        return json.loads(self.value_json)

    def set_value(self, value: Any) -> None:
        self.value_json = json.dumps(value, ensure_ascii=False)

    def get_source_observation_ids(self) -> list[str]:
        if not self.source_observation_ids_json:
            return []
        return json.loads(self.source_observation_ids_json)

    def set_source_observation_ids(self, observation_ids: list[str] | None) -> None:
        self.source_observation_ids_json = json.dumps(observation_ids or [], ensure_ascii=False)


class StateHypothesis(Base):
    __tablename__ = "state_hypotheses"
    __table_args__ = (
        Index("ix_state_hypothesis_estimate", "state_estimate_id"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    state_estimate_id: str = Column(String(36), ForeignKey("state_estimates.id", ondelete="CASCADE"), nullable=False)
    hypothesis_label: str = Column(String(200), nullable=False)
    explanation: str | None = Column(Text, nullable=True)
    probability: float = Column(Float, nullable=False, default=0.0)
    source: str | None = Column(String(100), nullable=True)
    is_selected: bool = Column(Boolean, nullable=False, default=False)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    state_estimate = relationship("StateEstimate", back_populates="hypotheses")


class SensorHealth(Base):
    __tablename__ = "sensor_health"
    __table_args__ = (
        Index("ix_sensor_health_sensor", "sensor_entity_id"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    sensor_entity_id: str = Column(String(36), ForeignKey("world_entities.id", ondelete="CASCADE"), nullable=False, unique=True)
    dropout_rate: float = Column(Float, nullable=False, default=0.0)
    drift_score: float = Column(Float, nullable=False, default=0.0)
    noise_score: float = Column(Float, nullable=False, default=0.0)
    calibration_age_hours: float = Column(Float, nullable=False, default=0.0)
    reliability_score: float = Column(Float, nullable=False, default=1.0)
    last_seen_at: datetime | None = Column(DateTime(timezone=True), nullable=True)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    sensor_entity = relationship("WorldEntity")


class ModelAssumption(Base):
    __tablename__ = "model_assumptions"
    __table_args__ = (
        Index("ix_model_assumptions_title", "title"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    title: str = Column(String(300), nullable=False)
    description: str = Column(Text, nullable=False)
    confidence: float = Column(Float, nullable=False, default=0.5)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    fact_links = relationship("ModelAssumptionFactLink", back_populates="assumption", cascade="all, delete-orphan")


class ModelAssumptionFactLink(Base):
    __tablename__ = "model_assumption_fact_links"
    __table_args__ = (
        UniqueConstraint("assumption_id", "fact_id", "link_type", name="uq_assumption_fact_link"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    assumption_id: str = Column(String(36), ForeignKey("model_assumptions.id", ondelete="CASCADE"), nullable=False)
    fact_id: str = Column(String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False)
    link_type: str = Column(Enum(ModelLinkType), nullable=False)
    notes: str | None = Column(Text, nullable=True)

    assumption = relationship("ModelAssumption", back_populates="fact_links")
    fact = relationship(Fact)


class AnomalyCase(Base):
    __tablename__ = "anomaly_cases"
    __table_args__ = (
        Index("ix_anomaly_status", "status"),
        Index("ix_anomaly_entity_prop", "entity_id", "property_name"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    entity_id: str = Column(String(36), ForeignKey("world_entities.id", ondelete="SET NULL"), nullable=True)
    property_name: str | None = Column(String(150), nullable=True)
    expected_value_json: str | None = Column(Text, nullable=True)
    observed_value_json: str | None = Column(Text, nullable=True)
    residual_score: float = Column(Float, nullable=False, default=0.0)
    status: str = Column(Enum(AnomalyStatus), nullable=False, default=AnomalyStatus.OPEN, index=True)
    diagnosis_json: str | None = Column(Text, nullable=True)
    resolution_action: str | None = Column(Text, nullable=True)
    evidence_json: str | None = Column(Text, nullable=True)
    opened_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    resolved_at: datetime | None = Column(DateTime(timezone=True), nullable=True)

    entity = relationship("WorldEntity")

    def set_expected(self, value: Any) -> None:
        self.expected_value_json = json.dumps(value, ensure_ascii=False)

    def set_observed(self, value: Any) -> None:
        self.observed_value_json = json.dumps(value, ensure_ascii=False)

    def set_diagnosis(self, payload: Any) -> None:
        self.diagnosis_json = json.dumps(payload, ensure_ascii=False)

    def set_evidence(self, payload: Any) -> None:
        self.evidence_json = json.dumps(payload, ensure_ascii=False)


class ObjectiveRecord(Base):
    __tablename__ = "objective_records"
    __table_args__ = (
        Index("ix_objective_status", "status"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    modality: str = Column(Enum(Modality), nullable=False, default=Modality.TEXT)
    raw_input_json: str = Column(Text, nullable=False)
    canonical_task_graph_json: str | None = Column(Text, nullable=True)
    intent_confidence: float = Column(Float, nullable=False, default=0.0)
    status: str = Column(Enum(ObjectiveStatus), nullable=False, default=ObjectiveStatus.RECEIVED)
    clarification_requested: bool = Column(Boolean, nullable=False, default=False)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class SkillFunction(Base):
    __tablename__ = "skill_functions"
    __table_args__ = (
        Index("ix_skill_kind_active", "kind", "is_active"),
        UniqueConstraint("name", "kind", name="uq_skill_name_kind"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    name: str = Column(String(250), nullable=False, index=True)
    kind: str = Column(Enum(SkillKind), nullable=False, default=SkillKind.FUNCTION)
    input_schema_json: str | None = Column(Text, nullable=True)
    output_schema_json: str | None = Column(Text, nullable=True)
    cost_score: float = Column(Float, nullable=False, default=1.0)
    latency_ms: float = Column(Float, nullable=False, default=0.0)
    reliability_score: float = Column(Float, nullable=False, default=1.0)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    metadata_json: str | None = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    last_used_at: datetime | None = Column(DateTime(timezone=True), nullable=True)
