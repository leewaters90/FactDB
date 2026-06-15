import pytest

from factdb.models import Fact, FactStatus, EngineeringDomain, DetailLevel
from factdb.world_model import (
    AnomalyStatus,
    ModelAssumption,
    ModelAssumptionFactLink,
    ModelLinkType,
    Modality,
    ObjectiveStatus,
    SkillKind,
    WorldEntityType,
)
from factdb.world_model_service import ObservationInput, WorldModelService


class TestWorldModelService:
    def test_ingestion_fusion_alignment_and_resolution(self, db_session):
        service = WorldModelService(db_session)
        robot = service.ensure_entity("robot-alpha", WorldEntityType.ROBOT)
        sensor = service.ensure_entity("gps-main", WorldEntityType.SENSOR)

        service.ingest_observation(
            ObservationInput(
                entity_id=robot.id,
                source_sensor_id=sensor.id,
                property_name="x_position",
                value=10.0,
                confidence=0.8,
                source_modality=Modality.GPS,
                processing_method="gps-filter",
            )
        )
        service.ingest_observation(
            ObservationInput(
                entity_id=robot.id,
                source_sensor_id=sensor.id,
                property_name="x_position",
                value=14.0,
                confidence=0.2,
                source_modality=Modality.VIDEO,
                processing_method="visual-odometry",
            )
        )

        estimate = service.fuse_state(entity_id=robot.id, property_name="x_position")
        assert estimate is not None
        assert estimate.confidence > 0.0
        assert estimate.get_value() == pytest.approx(10.8)
        assert len(estimate.get_source_observation_ids()) == 2

        residual, anomaly = service.align_expected_state(
            entity_id=robot.id,
            property_name="x_position",
            expected_value=8.0,
            tolerance=0.1,
        )
        assert residual > 0.0
        assert anomaly is not None
        assert anomaly.status == AnomalyStatus.OPEN

        diagnosed = service.diagnose_anomaly(anomaly.id)
        assert diagnosed.status == AnomalyStatus.INVESTIGATING
        assert diagnosed.diagnosis_json is not None

        resolved = service.resolve_anomaly(anomaly.id, action="down_weight_sensor")
        assert resolved.status == AnomalyStatus.RESOLVED
        assert resolved.resolution_action == "down_weight_sensor"

    def test_objective_grounding_and_hierarchical_planning(self, db_session):
        service = WorldModelService(db_session)
        service.register_skill(
            name="route_plan",
            kind=SkillKind.FUNCTION,
            input_schema={"waypoint": "str"},
            output_schema={"path": "list"},
            reliability_score=0.95,
            cost_score=0.4,
            latency_ms=40,
        )
        service.register_skill(
            name="avoid_obstacle",
            kind=SkillKind.TRANSFORM,
            input_schema={"occupancy_grid": "array"},
            output_schema={"safe_path": "list"},
            reliability_score=0.9,
            cost_score=0.5,
            latency_ms=20,
        )
        service.register_skill(
            name="fallback_operator_assist",
            kind=SkillKind.AGENT,
            reliability_score=0.99,
            cost_score=1.0,
            latency_ms=200,
        )

        low_conf = service.ingest_objective(
            raw_input={"speech": "go there"},
            modality=Modality.SPEECH,
            canonical_task_graph={"objective": "navigate"},
            intent_confidence=0.4,
        )
        assert low_conf.status == ObjectiveStatus.NEEDS_CLARIFICATION
        assert low_conf.clarification_requested is True

        objective = service.ingest_objective(
            raw_input={"text": "deliver sample to waypoint A"},
            modality=Modality.TEXT,
            canonical_task_graph={"objective": "deliver_sample", "target": "waypoint_A"},
            intent_confidence=0.9,
        )
        assert objective.status == ObjectiveStatus.PLANNED

        plan = service.build_hierarchical_plan(objective_id=objective.id)
        assert plan["objective_id"] == objective.id
        assert plan["strategic"]["policy"] == "maximize_expected_success"
        assert len(plan["tactical"]["selected_skills"]) > 0

    def test_assumption_fact_linking(self, db_session):
        fact = Fact(
            title="Gravity affects unsupported masses",
            content="Objects accelerate downward at 9.81 m/s² near Earth.",
            domain=EngineeringDomain.SYSTEMS,
            detail_level=DetailLevel.FUNDAMENTAL,
            status=FactStatus.VERIFIED,
        )
        db_session.add(fact)
        db_session.flush()

        assumption = ModelAssumption(
            title="Earth gravity present",
            description="The robot is operating in Earth gravity conditions.",
            confidence=0.9,
        )
        db_session.add(assumption)
        db_session.flush()

        link = ModelAssumptionFactLink(
            assumption_id=assumption.id,
            fact_id=fact.id,
            link_type=ModelLinkType.SUPPORTS,
            notes="Used by manipulation planner.",
        )
        db_session.add(link)
        db_session.flush()

        stored = db_session.get(ModelAssumption, assumption.id)
        assert stored is not None
        assert len(stored.fact_links) == 1
        assert stored.fact_links[0].fact.title.startswith("Gravity")
