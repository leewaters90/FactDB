"""
Tests for SoftwareRepository — SoftwareArtifact, BenchmarkTest, ProjectPackage.
"""

import pytest

from factdb.models import EngineeringDomain
from factdb.project_models import ProjectStatus
from factdb.project_repository import ProjectRepository
from factdb.software_models import (
    BenchmarkTest,
    ProgrammingLanguage,
    ProjectPackage,
    SoftwareArtifact,
    SoftwareArtifactType,
)
from factdb.software_repository import SoftwareRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifact(
    repo: SoftwareRepository,
    title: str = "Test Function",
    artifact_type: SoftwareArtifactType = SoftwareArtifactType.FUNCTION,
    code: str = "def test_fn(x):\n    return x * 2",
    **kw,
) -> SoftwareArtifact:
    defaults = dict(
        title=title,
        content="A test function.",
        artifact_type=artifact_type,
        code=code,
    )
    defaults.update(kw)
    return repo.create_artifact(**defaults)


def _make_project(session, title: str = "SW Test Project") -> object:
    p_repo = ProjectRepository(session)
    return p_repo.create_project(
        title=title,
        description="A software test project.",
        domain="software",
        status=ProjectStatus.CONCEPT,
    )


# ---------------------------------------------------------------------------
# SoftwareArtifact — Create / Read
# ---------------------------------------------------------------------------


class TestSoftwareArtifactCreate:
    def test_create_minimal(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        assert artifact.id is not None
        assert artifact.fact_id is not None
        assert artifact.artifact_type == SoftwareArtifactType.FUNCTION.value
        assert artifact.language == ProgrammingLanguage.PYTHON.value
        assert artifact.fact.title == "Test Function"

    def test_create_transform(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(
            repo,
            title="Data Transform",
            artifact_type=SoftwareArtifactType.TRANSFORM,
            code="def transform(data):\n    return {'value': data}",
        )
        db_session.commit()

        assert artifact.artifact_type == SoftwareArtifactType.TRANSFORM.value

    def test_create_with_packages(self, db_session):
        repo = SoftwareRepository(db_session)
        pkgs = [{"name": "numpy", "version": ">=1.24.0"}]
        artifact = _make_artifact(repo, title="Numpy Function", packages=pkgs)
        db_session.commit()

        assert artifact.get_packages() == pkgs

    def test_create_with_schema(self, db_session):
        repo = SoftwareRepository(db_session)
        in_schema = [{"name": "x", "type": "float", "description": "Input value"}]
        out_schema = {"type": "float", "description": "Output value"}
        artifact = _make_artifact(
            repo,
            title="Schema Function",
            input_schema=in_schema,
            output_schema=out_schema,
        )
        db_session.commit()

        assert artifact.get_input_schema() == in_schema
        assert artifact.get_output_schema() == out_schema

    def test_create_with_signature_and_language_version(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(
            repo,
            title="Typed Function",
            signature="def typed_fn(x: float) -> float",
            language_version="3.11",
        )
        db_session.commit()

        assert artifact.signature == "def typed_fn(x: float) -> float"
        assert artifact.language_version == "3.11"

    def test_create_with_tags(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo, title="Tagged Function", tags=["sensor", "math"])
        db_session.commit()

        tag_names = {t.name for t in artifact.fact.tags}
        assert tag_names == {"sensor", "math"}

    def test_to_dict(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo, title="Dict Function")
        db_session.commit()

        d = artifact.to_dict()
        assert d["fact_title"] == "Dict Function"
        assert d["artifact_type"] == "function"
        assert d["language"] == "python"
        assert "code" in d

    def test_lua_language(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(
            repo,
            title="Lua Script",
            language=ProgrammingLanguage.LUA,
            code="function double(x) return x * 2 end",
        )
        db_session.commit()

        assert artifact.language == ProgrammingLanguage.LUA.value

    def test_arduino_language(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(
            repo,
            title="Arduino Sketch",
            language=ProgrammingLanguage.ARDUINO,
            code="int ledPin = 13;\nvoid setup() { pinMode(ledPin, OUTPUT); }",
        )
        db_session.commit()

        assert artifact.language == ProgrammingLanguage.ARDUINO.value


# ---------------------------------------------------------------------------
# SoftwareArtifact — Read / List
# ---------------------------------------------------------------------------


class TestSoftwareArtifactRead:
    def test_get_by_id(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        fetched = repo.get_artifact(artifact.id)
        assert fetched is not None
        assert fetched.id == artifact.id

    def test_get_by_fact_id(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        fetched = repo.get_artifact_by_fact_id(artifact.fact_id)
        assert fetched is not None
        assert fetched.id == artifact.id

    def test_get_missing_returns_none(self, db_session):
        repo = SoftwareRepository(db_session)
        assert repo.get_artifact("nonexistent-id") is None
        assert repo.get_artifact_by_fact_id("nonexistent-id") is None

    def test_list_all(self, db_session):
        repo = SoftwareRepository(db_session)
        _make_artifact(repo, title="A Function")
        _make_artifact(repo, title="B Transform", artifact_type=SoftwareArtifactType.TRANSFORM)
        db_session.commit()

        all_artifacts = repo.list_artifacts()
        assert len(all_artifacts) == 2

    def test_list_filtered_by_type(self, db_session):
        repo = SoftwareRepository(db_session)
        _make_artifact(repo, title="F1", artifact_type=SoftwareArtifactType.FUNCTION)
        _make_artifact(repo, title="T1", artifact_type=SoftwareArtifactType.TRANSFORM)
        db_session.commit()

        fns = repo.list_artifacts(artifact_type=SoftwareArtifactType.FUNCTION)
        transforms = repo.list_artifacts(artifact_type=SoftwareArtifactType.TRANSFORM)
        assert len(fns) == 1
        assert len(transforms) == 1
        assert fns[0].fact.title == "F1"

    def test_list_filtered_by_language(self, db_session):
        repo = SoftwareRepository(db_session)
        _make_artifact(repo, title="PY", language=ProgrammingLanguage.PYTHON)
        _make_artifact(repo, title="LUA", language=ProgrammingLanguage.LUA)
        db_session.commit()

        py_artifacts = repo.list_artifacts(language=ProgrammingLanguage.PYTHON)
        lua_artifacts = repo.list_artifacts(language=ProgrammingLanguage.LUA)
        assert len(py_artifacts) == 1
        assert len(lua_artifacts) == 1


# ---------------------------------------------------------------------------
# BenchmarkTest — Add / List
# ---------------------------------------------------------------------------


class TestBenchmarkTestCreate:
    def test_add_minimal(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        test = repo.add_benchmark_test(
            artifact_id=artifact.id,
            name="basic",
            test_code="result = test_fn(2)",
        )
        db_session.commit()

        assert test.id is not None
        assert test.artifact_id == artifact.id
        assert test.name == "basic"

    def test_add_with_expected_output(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        test = repo.add_benchmark_test(
            artifact_id=artifact.id,
            name="doubles_2",
            test_code="result = test_fn(2)",
            expected_output=4,
        )
        db_session.commit()

        assert test.get_expected_output() == 4

    def test_add_with_tolerance(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        test = repo.add_benchmark_test(
            artifact_id=artifact.id,
            name="float_test",
            test_code="result = test_fn(1.5)",
            expected_output=3.0,
            tolerance=0.01,
        )
        db_session.commit()

        assert test.tolerance == 0.01

    def test_add_missing_artifact_raises(self, db_session):
        repo = SoftwareRepository(db_session)
        with pytest.raises(ValueError, match="not found"):
            repo.add_benchmark_test(
                artifact_id="nonexistent",
                name="test",
                test_code="result = 1",
            )

    def test_list_benchmark_tests(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(artifact.id, "test_a", "result = test_fn(1)")
        repo.add_benchmark_test(artifact.id, "test_b", "result = test_fn(2)")
        db_session.commit()

        tests = repo.list_benchmark_tests(artifact.id)
        assert len(tests) == 2
        # Ordered by name
        assert tests[0].name == "test_a"
        assert tests[1].name == "test_b"

    def test_to_dict(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(repo)
        db_session.commit()
        test = repo.add_benchmark_test(
            artifact.id, "dict_test", "result = test_fn(3)", expected_output=6
        )
        db_session.commit()

        d = test.to_dict()
        assert d["name"] == "dict_test"
        assert d["expected_output"] == 6
        assert d["test_code"] == "result = test_fn(3)"


# ---------------------------------------------------------------------------
# BenchmarkTest — Run
# ---------------------------------------------------------------------------


class TestBenchmarkRun:
    def _celsius_artifact(self, repo: SoftwareRepository) -> SoftwareArtifact:
        return _make_artifact(
            repo,
            title="Celsius to Fahrenheit",
            code=(
                "def celsius_to_fahrenheit(celsius):\n"
                "    return celsius * 9 / 5 + 32\n"
            ),
            language=ProgrammingLanguage.PYTHON,
        )

    def test_run_passing_test(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(
            artifact.id,
            "boiling_point",
            "result = celsius_to_fahrenheit(100)",
            expected_output=212.0,
            tolerance=0.001,
        )
        db_session.commit()

        results = repo.run_benchmark(artifact.id)
        assert len(results) == 1
        assert results[0]["passed"] is True
        assert results[0]["error"] is None
        assert abs(results[0]["result"] - 212.0) < 0.001

    def test_run_failing_test(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(
            artifact.id,
            "wrong_expected",
            "result = celsius_to_fahrenheit(0)",
            expected_output=99.0,   # wrong
            tolerance=0.001,
        )
        db_session.commit()

        results = repo.run_benchmark(artifact.id)
        assert results[0]["passed"] is False

    def test_run_exception_in_test(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(
            artifact.id,
            "exception_test",
            "result = celsius_to_fahrenheit('not_a_number')",
        )
        db_session.commit()

        results = repo.run_benchmark(artifact.id)
        assert results[0]["passed"] is False
        assert results[0]["error"] is not None

    def test_run_no_expected_output_passes(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(
            artifact.id,
            "no_expected",
            "result = celsius_to_fahrenheit(25)",
        )
        db_session.commit()

        results = repo.run_benchmark(artifact.id)
        assert results[0]["passed"] is True

    def test_run_specific_test_by_id(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        t1 = repo.add_benchmark_test(artifact.id, "t1", "result = celsius_to_fahrenheit(0)", expected_output=32.0, tolerance=0.001)
        repo.add_benchmark_test(artifact.id, "t2", "result = celsius_to_fahrenheit(100)", expected_output=212.0, tolerance=0.001)
        db_session.commit()

        results = repo.run_benchmark(artifact.id, test_id=t1.id)
        assert len(results) == 1
        assert results[0]["test_id"] == t1.id

    def test_run_elapsed_time_recorded(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(artifact.id, "timing", "result = celsius_to_fahrenheit(20)")
        db_session.commit()

        results = repo.run_benchmark(artifact.id)
        assert results[0]["elapsed_ms"] is not None
        assert results[0]["elapsed_ms"] >= 0

    def test_run_non_python_raises(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = _make_artifact(
            repo,
            title="Lua Fn",
            language=ProgrammingLanguage.LUA,
            code="function double(x) return x * 2 end",
        )
        db_session.commit()
        repo.add_benchmark_test(artifact.id, "t", "result = double(2)")
        db_session.commit()

        with pytest.raises(ValueError, match="Python"):
            repo.run_benchmark(artifact.id)

    def test_run_missing_artifact_raises(self, db_session):
        repo = SoftwareRepository(db_session)
        with pytest.raises(ValueError, match="not found"):
            repo.run_benchmark("nonexistent")

    def test_run_multiple_tests_returns_all(self, db_session):
        repo = SoftwareRepository(db_session)
        artifact = self._celsius_artifact(repo)
        db_session.commit()

        repo.add_benchmark_test(artifact.id, "freezing", "result = celsius_to_fahrenheit(0)", expected_output=32.0, tolerance=0.001)
        repo.add_benchmark_test(artifact.id, "body_temp", "result = celsius_to_fahrenheit(37)", expected_output=98.6, tolerance=0.1)
        repo.add_benchmark_test(artifact.id, "boiling", "result = celsius_to_fahrenheit(100)", expected_output=212.0, tolerance=0.001)
        db_session.commit()

        results = repo.run_benchmark(artifact.id)
        assert len(results) == 3
        assert all(r["passed"] for r in results)


# ---------------------------------------------------------------------------
# ProjectPackage — Add / List / Requirements
# ---------------------------------------------------------------------------


class TestProjectPackage:
    def test_add_package(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        pkg = repo.add_project_package(
            project_id=project.id,
            package_name="numpy",
            package_version=">=1.24.0",
        )
        db_session.commit()

        assert pkg.id is not None
        assert pkg.package_name == "numpy"
        assert pkg.package_version == ">=1.24.0"
        assert pkg.language == ProgrammingLanguage.PYTHON.value

    def test_add_package_idempotent(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        p1 = repo.add_project_package(project.id, "requests", ">=2.28.0")
        db_session.commit()
        p2 = repo.add_project_package(project.id, "requests", ">=2.28.0")
        db_session.commit()

        assert p1.id == p2.id

    def test_add_package_missing_project_raises(self, db_session):
        repo = SoftwareRepository(db_session)
        with pytest.raises(ValueError, match="not found"):
            repo.add_project_package("nonexistent", "numpy")

    def test_list_packages(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        repo.add_project_package(project.id, "scipy", ">=1.11.0")
        repo.add_project_package(project.id, "numpy", ">=1.24.0")
        db_session.commit()

        pkgs = repo.list_project_packages(project.id)
        assert len(pkgs) == 2
        # ordered by language then name
        assert pkgs[0].package_name == "numpy"
        assert pkgs[1].package_name == "scipy"

    def test_list_packages_filter_by_language(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        repo.add_project_package(project.id, "numpy", ">=1.24.0", language=ProgrammingLanguage.PYTHON)
        repo.add_project_package(project.id, "luasocket", language=ProgrammingLanguage.LUA)
        db_session.commit()

        py_pkgs = repo.list_project_packages(project.id, language=ProgrammingLanguage.PYTHON)
        assert len(py_pkgs) == 1
        assert py_pkgs[0].package_name == "numpy"

    def test_generate_requirements_txt(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        repo.add_project_package(project.id, "numpy", ">=1.24.0")
        repo.add_project_package(project.id, "scipy", ">=1.11.0")
        db_session.commit()

        req_txt = repo.generate_requirements_txt(project.id)
        lines = req_txt.splitlines()
        assert "numpy>=1.24.0" in lines
        assert "scipy>=1.11.0" in lines

    def test_generate_requirements_empty(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        req_txt = repo.generate_requirements_txt(project.id)
        assert req_txt == ""

    def test_generate_requirements_excludes_non_python(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        repo.add_project_package(project.id, "numpy", ">=1.24.0", language=ProgrammingLanguage.PYTHON)
        repo.add_project_package(project.id, "luasocket", language=ProgrammingLanguage.LUA)
        db_session.commit()

        req_txt = repo.generate_requirements_txt(project.id)
        assert "numpy" in req_txt
        assert "luasocket" not in req_txt

    def test_package_without_version(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        repo.add_project_package(project.id, "requests")
        db_session.commit()

        req_txt = repo.generate_requirements_txt(project.id)
        assert "requests" in req_txt
        # No version specifier appended
        assert "requests\n" in (req_txt + "\n")

    def test_to_dict(self, db_session):
        project = _make_project(db_session)
        db_session.commit()

        repo = SoftwareRepository(db_session)
        pkg = repo.add_project_package(project.id, "pandas", ">=2.0.0")
        db_session.commit()

        d = pkg.to_dict()
        assert d["package_name"] == "pandas"
        assert d["package_version"] == ">=2.0.0"
        assert d["language"] == "python"
