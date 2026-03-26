"""
Tests for ProjectRepository — shared DesignElements, Projects, and links.
"""

import pytest

from factdb.models import EngineeringDomain
from factdb.project_models import (
    ComponentCategory,
    DesignElement,
    Project,
    ProjectDesignElement,
    ProjectStatus,
)
from factdb.project_repository import ProjectRepository
from factdb.repository import FactRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_element(repo: ProjectRepository, title: str = "Test Element", **kw) -> DesignElement:
    defaults = dict(
        title=title,
        selected_approach="Selected approach text.",
        component_category=ComponentCategory.SENSING,
    )
    defaults.update(kw)
    return repo.create_design_element(**defaults)


def _make_project(repo: ProjectRepository, title: str = "Test Project", **kw) -> Project:
    defaults = dict(
        title=title,
        description="A test project.",
        domain="systems",
        status=ProjectStatus.CONCEPT,
    )
    defaults.update(kw)
    return repo.create_project(**defaults)


# ---------------------------------------------------------------------------
# DesignElement — Create / Read
# ---------------------------------------------------------------------------


class TestDesignElementCreate:
    def test_create_minimal(self, db_session):
        repo = ProjectRepository(db_session)
        el = _make_element(repo)
        db_session.commit()

        assert el.id is not None
        assert el.title == "Test Element"
        assert el.component_category == ComponentCategory.SENSING.value
        assert el.selected_approach == "Selected approach text."

    def test_create_with_alternatives(self, db_session):
        repo = ProjectRepository(db_session)
        alts = [{"approach": "Alt A", "reason_rejected": "Too expensive."}]
        el = _make_element(repo, title="Element With Alts", alternatives=alts)
        db_session.commit()

        assert el.get_alternatives() == alts

    def test_create_with_fact_link(self, db_session):
        fact_repo = FactRepository(db_session)
        fact = fact_repo.create(title="Test Fact", content="A test fact.")
        db_session.flush()

        repo = ProjectRepository(db_session)
        el = _make_element(
            repo,
            title="Element With Fact",
            supporting_fact_titles=["Test Fact"],
        )
        db_session.commit()

        assert len(el.supporting_facts) == 1
        assert el.supporting_facts[0].title == "Test Fact"

    def test_create_silently_ignores_missing_facts(self, db_session):
        repo = ProjectRepository(db_session)
        el = _make_element(
            repo,
            title="Element Missing Fact",
            supporting_fact_titles=["Nonexistent Fact"],
        )
        db_session.commit()
        assert el.supporting_facts == []

    def test_get_by_title(self, db_session):
        repo = ProjectRepository(db_session)
        el = _make_element(repo, title="Findable Element")
        db_session.commit()

        found = repo.get_design_element_by_title("Findable Element")
        assert found is not None
        assert found.id == el.id

    def test_get_by_title_missing(self, db_session):
        repo = ProjectRepository(db_session)
        assert repo.get_design_element_by_title("No Such Element") is None

    def test_title_uniqueness(self, db_session):
        from sqlalchemy.exc import IntegrityError

        repo = ProjectRepository(db_session)
        _make_element(repo, title="Unique")
        db_session.commit()

        with pytest.raises(IntegrityError):
            _make_element(repo, title="Unique")
            db_session.commit()


class TestGetOrCreateDesignElement:
    def test_creates_new(self, db_session):
        repo = ProjectRepository(db_session)
        el, created = repo.get_or_create_design_element(
            title="New Element",
            selected_approach="Approach",
        )
        db_session.commit()
        assert created is True
        assert el.id is not None

    def test_returns_existing(self, db_session):
        repo = ProjectRepository(db_session)
        el1 = _make_element(repo, title="Existing")
        db_session.commit()

        el2, created = repo.get_or_create_design_element(
            title="Existing",
            selected_approach="Different approach",
        )
        assert created is False
        assert el2.id == el1.id


class TestListDesignElements:
    def test_list_all(self, db_session):
        repo = ProjectRepository(db_session)
        _make_element(repo, title="E1", component_category=ComponentCategory.SENSING)
        _make_element(repo, title="E2", component_category=ComponentCategory.ACTUATION)
        db_session.commit()

        elements = repo.list_design_elements()
        assert len(elements) == 2

    def test_filter_by_category(self, db_session):
        repo = ProjectRepository(db_session)
        _make_element(repo, title="S1", component_category=ComponentCategory.SENSING)
        _make_element(repo, title="A1", component_category=ComponentCategory.ACTUATION)
        db_session.commit()

        sensing = repo.list_design_elements(component_category=ComponentCategory.SENSING)
        assert len(sensing) == 1
        assert sensing[0].title == "S1"


# ---------------------------------------------------------------------------
# Project — Create / Read
# ---------------------------------------------------------------------------


class TestProjectCreate:
    def test_create_minimal(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo)
        db_session.commit()

        assert p.id is not None
        assert p.title == "Test Project"
        assert p.status == ProjectStatus.CONCEPT.value
        assert p.elements == []

    def test_create_sets_domain(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, domain="electrical")
        db_session.commit()
        assert p.domain == EngineeringDomain.ELECTRICAL.value

    def test_get_by_title(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="Named Project")
        db_session.commit()
        found = repo.get_project_by_title("Named Project")
        assert found is not None
        assert found.id == p.id

    def test_list_projects(self, db_session):
        repo = ProjectRepository(db_session)
        _make_project(repo, title="P1")
        _make_project(repo, title="P2", status=ProjectStatus.COMPLETED)
        db_session.commit()

        all_projects = repo.list_projects()
        assert len(all_projects) == 2

    def test_list_projects_filter_status(self, db_session):
        repo = ProjectRepository(db_session)
        _make_project(repo, title="P1")
        _make_project(repo, title="P2", status=ProjectStatus.COMPLETED)
        db_session.commit()

        completed = repo.list_projects(status=ProjectStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].title == "P2"


# ---------------------------------------------------------------------------
# Project ↔ DesignElement — Linking
# ---------------------------------------------------------------------------


class TestProjectElementLinking:
    def test_link_element_to_project(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="Proj")
        el = _make_element(repo, title="Elem")
        db_session.flush()

        link = repo.link_element_to_project(p.id, el.id)
        db_session.commit()

        assert link.project_id == p.id
        assert link.element_id == el.id
        assert link.usage_notes is None

    def test_link_with_usage_notes(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="Proj2")
        el = _make_element(repo, title="Elem2")
        db_session.flush()

        link = repo.link_element_to_project(p.id, el.id, usage_notes="Project-specific note.")
        db_session.commit()

        assert link.usage_notes == "Project-specific note."

    def test_link_is_idempotent(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="Proj3")
        el = _make_element(repo, title="Elem3")
        db_session.flush()

        link1 = repo.link_element_to_project(p.id, el.id)
        db_session.commit()
        link2 = repo.link_element_to_project(p.id, el.id)
        db_session.commit()

        assert link1.id == link2.id

    def test_element_accessible_from_project(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="ProjAccess")
        el = _make_element(repo, title="ElemAccess")
        db_session.flush()
        repo.link_element_to_project(p.id, el.id)
        db_session.commit()

        # Reload project
        p2 = repo.get_project(p.id)
        assert len(p2.elements) == 1
        assert p2.elements[0].title == "ElemAccess"

    def test_element_shared_across_projects(self, db_session):
        repo = ProjectRepository(db_session)
        p1 = _make_project(repo, title="ProjectA")
        p2 = _make_project(repo, title="ProjectB")
        el = _make_element(repo, title="SharedElem")
        db_session.flush()

        repo.link_element_to_project(p1.id, el.id, usage_notes="Use in ProjectA.")
        repo.link_element_to_project(p2.id, el.id, usage_notes="Use in ProjectB.")
        db_session.commit()

        # Both projects see the element
        assert len(repo.get_project(p1.id).elements) == 1
        assert len(repo.get_project(p2.id).elements) == 1

        # Element reports both projects
        projects_using = repo.get_projects_using_element(el.id)
        assert len(projects_using) == 2
        titles = {proj.title for proj in projects_using}
        assert titles == {"ProjectA", "ProjectB"}

    def test_unlink_element(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="ProjUnlink")
        el = _make_element(repo, title="ElemUnlink")
        db_session.flush()
        repo.link_element_to_project(p.id, el.id)
        db_session.commit()

        repo.unlink_element_from_project(p.id, el.id)
        db_session.commit()

        p2 = repo.get_project(p.id)
        assert p2.elements == []

    def test_link_raises_for_unknown_project(self, db_session):
        repo = ProjectRepository(db_session)
        el = _make_element(repo, title="ElemErr")
        db_session.flush()
        with pytest.raises(ValueError, match="Project not found"):
            repo.link_element_to_project("nonexistent-id", el.id)

    def test_link_raises_for_unknown_element(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="ProjErr")
        db_session.flush()
        with pytest.raises(ValueError, match="DesignElement not found"):
            repo.link_element_to_project(p.id, "nonexistent-id")


# ---------------------------------------------------------------------------
# to_dict serialisation
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_element_to_dict(self, db_session):
        repo = ProjectRepository(db_session)
        el = _make_element(
            repo,
            title="Serialise Me",
            component_category=ComponentCategory.POWER,
            design_question="Q?",
            rationale="R.",
            alternatives=[{"approach": "A", "reason_rejected": "X"}],
        )
        db_session.commit()
        d = el.to_dict()
        assert d["title"] == "Serialise Me"
        assert d["component_category"] == ComponentCategory.POWER.value
        assert len(d["alternatives"]) == 1
        assert d["supporting_fact_titles"] == []

    def test_project_to_dict_includes_elements(self, db_session):
        repo = ProjectRepository(db_session)
        p = _make_project(repo, title="SerialiseProject")
        el = _make_element(repo, title="SerialiseElem")
        db_session.flush()
        repo.link_element_to_project(p.id, el.id, usage_notes="A note.")
        db_session.commit()

        d = p.to_dict()
        assert d["title"] == "SerialiseProject"
        assert len(d["design_elements"]) == 1
        assert d["design_elements"][0]["title"] == "SerialiseElem"
        assert d["design_elements"][0]["usage_notes"] == "A note."


# ---------------------------------------------------------------------------
# Project seeder integration
# ---------------------------------------------------------------------------


class TestProjectSeeder:
    def test_seeder_creates_elements_and_projects(self, db_session):
        from factdb.seeder import seed as seed_facts
        from factdb.device_seeder import seed_devices
        from factdb.project_seeder import seed_projects

        seed_facts(db_session)
        seed_devices(db_session)
        result = seed_projects(db_session)

        assert result["elements_created"] > 0
        assert result["projects_created"] == 50
        assert result["links_created"] > 0

    def test_seeder_is_idempotent(self, db_session):
        from factdb.seeder import seed as seed_facts
        from factdb.device_seeder import seed_devices
        from factdb.project_seeder import seed_projects

        seed_facts(db_session)
        seed_devices(db_session)
        r1 = seed_projects(db_session)
        r2 = seed_projects(db_session)

        assert r2["elements_created"] == 0
        assert r2["elements_skipped"] == r1["elements_created"]
        assert r2["projects_created"] == 0
        assert r2["projects_skipped"] == 50

    def test_seeder_elements_are_shared(self, db_session):
        """Verify that at least one DesignElement is used by multiple projects."""
        from factdb.seeder import seed as seed_facts
        from factdb.device_seeder import seed_devices
        from factdb.project_seeder import seed_projects

        seed_facts(db_session)
        seed_devices(db_session)
        seed_projects(db_session)

        repo = ProjectRepository(db_session)
        elements = repo.list_design_elements()
        # Find any element used by more than one project
        shared = [el for el in elements if len(el.project_links) > 1]
        assert len(shared) > 0, "Expected at least one DesignElement shared across projects"

    def test_esp32_element_shared_across_multiple_projects(self, db_session):
        """The ESP32 WiFi + MQTT element should appear in ≥4 projects."""
        from factdb.seeder import seed as seed_facts
        from factdb.device_seeder import seed_devices
        from factdb.project_seeder import seed_projects

        seed_facts(db_session)
        seed_devices(db_session)
        seed_projects(db_session)

        repo = ProjectRepository(db_session)
        el = repo.get_design_element_by_title("ESP32 WiFi + MQTT IoT Telemetry")
        assert el is not None
        projects_using = repo.get_projects_using_element(el.id)
        assert len(projects_using) >= 4
