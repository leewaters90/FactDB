"""Tests for the two-stage Copilot seeder helpers."""

from factdb.models import (
    DetailLevel,
    EngineeringDomain,
    Fact,
    FactRelationship,
    FactStatus,
    RelationshipType,
    Tag,
)
from factdb.project_models import ComponentCategory, DesignElement, Project, ProjectDesignElement, ProjectStatus
from scripts.copilot_seeder import ProjectIntent, retrieve_factdb_context, validate_intent


def test_validate_intent_normalizes_defaults():
    payload = {
        "title_hint": "Battery Health Monitor",
        "domain": "Electrical",
        "objective": "Track battery current and state of charge",
        "keywords": "battery",
        "fact_queries": [],
        "element_categories": ["sensing", "invalid", "processing"],
    }

    errors = validate_intent(payload)

    assert errors == []
    assert payload["domain"] == "electrical"
    assert payload["keywords"] == ["battery"]
    assert payload["fact_queries"] == ["battery"]
    assert payload["element_categories"] == ["sensing", "processing"]
    assert payload["fact_categories"] == []


def test_retrieve_factdb_context_returns_relevant_slice(db_session):
    battery_tag = Tag(name="battery")
    current_tag = Tag(name="current")

    fact_a = Fact(
        title="State-of-Charge Estimation via Coulomb Counting",
        domain=EngineeringDomain.ELECTRICAL,
        category="battery-management",
        detail_level=DetailLevel.INTERMEDIATE,
        content="Battery charge can be tracked by integrating current over time.",
        status=FactStatus.VERIFIED,
        confidence_score=0.98,
        tags=[battery_tag, current_tag],
    )
    fact_b = Fact(
        title="Shunt Current Measurement for Low-Voltage Systems",
        domain=EngineeringDomain.ELECTRICAL,
        category="electrical-measurement",
        detail_level=DetailLevel.INTERMEDIATE,
        content="A precision shunt and amplifier can measure bidirectional battery current.",
        status=FactStatus.VERIFIED,
        confidence_score=0.95,
        tags=[current_tag],
    )
    fact_c = Fact(
        title="Cell Voltage Monitoring with Divider Networks",
        domain=EngineeringDomain.ELECTRICAL,
        category="battery-management",
        detail_level=DetailLevel.FUNDAMENTAL,
        content="Resistive dividers scale pack voltage into the ADC input range.",
        status=FactStatus.VERIFIED,
        confidence_score=0.93,
        tags=[battery_tag],
    )
    db_session.add_all([fact_a, fact_b, fact_c])
    db_session.flush()

    db_session.add(
        FactRelationship(
            source_fact_id=fact_a.id,
            target_fact_id=fact_b.id,
            relationship_type=RelationshipType.SUPPORTS,
            weight=0.9,
            description="Current measurement supports coulomb counting.",
        )
    )

    element = DesignElement(
        title="INA219 Battery Current Monitor Module",
        component_category=ComponentCategory.SENSING,
        design_question="How do we measure battery current in a small embedded pack?",
        selected_approach="Use an INA219 high-side current monitor over I2C with a calibrated shunt.",
        supporting_facts=[fact_a, fact_b],
    )
    project = Project(
        title="Smart Battery Management System Monitor",
        description="Measures battery current, estimates state of charge, and displays pack health.",
        objective="Track current flow and estimate remaining charge.",
        constraints="Operate from a 12 V battery pack with an Arduino-class MCU.",
        domain=EngineeringDomain.ELECTRICAL,
        status=ProjectStatus.COMPLETED,
        integration_code="void setup() {}\nvoid loop() {}",
        supporting_facts=[fact_a, fact_c],
    )
    project.element_links.append(ProjectDesignElement(element=element, usage_notes="I2C current telemetry"))
    db_session.add_all([element, project])
    db_session.commit()

    intent = ProjectIntent(
        title_hint="Battery Health Telemetry Node",
        domain="electrical",
        problem_statement="Need a compact embedded monitor for battery current and charge state.",
        objective="Measure current, estimate state of charge, and log voltage trends.",
        constraints="12 V pack, low-cost MCU, I2C sensors.",
        keywords=["battery", "current", "charge", "voltage"],
        fact_queries=["coulomb counting battery", "battery current measurement"],
        fact_categories=["battery-management", "electrical-measurement"],
        element_categories=["sensing", "processing"],
    )

    retrieved = retrieve_factdb_context(intent, session=db_session)

    assert any(fact.title == fact_a.title for fact in retrieved.facts)
    assert any(fact.title == fact_b.title for fact in retrieved.facts)
    assert any(element_summary.title == element.title for element_summary in retrieved.elements)
    assert any(project_summary.title == project.title for project_summary in retrieved.projects)
    assert (fact_a.title, fact_b.title, RelationshipType.SUPPORTS.value) in retrieved.relationships
