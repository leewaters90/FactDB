"""
Repository layer — CRUD for SoftwareArtifact, BenchmarkTest, and ProjectPackage.

All methods accept a SQLAlchemy Session; the caller controls transaction
boundaries (call ``session.commit()`` after operations).
"""

from __future__ import annotations

import json
import time
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from factdb.models import EngineeringDomain, Fact, FactStatus, DetailLevel
from factdb.project_models import Project
from factdb.software_models import (
    BenchmarkTest,
    ProgrammingLanguage,
    ProjectPackage,
    SoftwareArtifact,
    SoftwareArtifactType,
)


class SoftwareRepository:
    """
    CRUD and utility operations for software artifacts, benchmark tests, and
    project package dependencies.

    Usage::

        repo = SoftwareRepository(session)
        artifact = repo.create_artifact(
            title="Celsius to Fahrenheit",
            content="Converts a temperature in °C to °F.",
            artifact_type=SoftwareArtifactType.FUNCTION,
            code="def celsius_to_fahrenheit(c: float) -> float:\\n    return c * 9/5 + 32",
            signature="def celsius_to_fahrenheit(celsius: float) -> float",
            packages=[],
        )
        session.commit()
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ==================================================================
    # SoftwareArtifact — Create / Read / List
    # ==================================================================

    def create_artifact(
        self,
        title: str,
        content: str,
        artifact_type: SoftwareArtifactType,
        code: str,
        *,
        language: ProgrammingLanguage = ProgrammingLanguage.PYTHON,
        language_version: str | None = None,
        signature: str | None = None,
        input_schema: list[dict] | None = None,
        output_schema: dict | None = None,
        packages: list[dict[str, str]] | None = None,
        domain: str = "software",
        category: str | None = None,
        subcategory: str | None = None,
        detail_level: str = "fundamental",
        extended_content: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        created_by: str | None = None,
    ) -> SoftwareArtifact:
        """
        Create a new Fact + SoftwareArtifact pair.

        The :class:`~factdb.models.Fact` carries the human-readable metadata
        (title, description, tags, status, versioning).  The
        :class:`SoftwareArtifact` carries the executable details (code,
        language, packages, I/O schema).

        Args:
            title:            Human-readable title for the fact.
            content:          Concise description of what the artifact does.
            artifact_type:    ``function`` or ``transform``.
            code:             Full source code of the artifact.
            language:         Programming language (default: python).
            language_version: Runtime version string, e.g. ``"3.11"``.
            signature:        Function/callable signature string.
            input_schema:     List of ``{name, type, description}`` dicts.
            output_schema:    Dict ``{type, description}`` for the return value.
            packages:         List of ``{name, version}`` package dicts.
            domain:           Engineering domain (default: ``"software"``).
            category:         Optional category within the domain.
            subcategory:      Optional subcategory.
            detail_level:     Fact detail level (default: ``"fundamental"``).
            extended_content: Longer explanation / derivation.
            source:           Reference or citation.
            tags:             Tag name strings to attach to the Fact.
            created_by:       Author identity.

        Returns:
            The newly created :class:`SoftwareArtifact`.
        """
        from factdb.repository import FactRepository

        fact_repo = FactRepository(self.session)
        fact = fact_repo.create(
            title=title,
            content=content,
            domain=EngineeringDomain(domain),
            category=category or artifact_type.value,
            subcategory=subcategory,
            detail_level=DetailLevel(detail_level),
            extended_content=extended_content,
            source=source,
            tags=tags or [],
            created_by=created_by,
        )

        artifact = SoftwareArtifact(
            fact_id=fact.id,
            artifact_type=artifact_type,
            language=language,
            language_version=language_version,
            code=code,
            signature=signature,
        )
        if input_schema:
            artifact.set_input_schema(input_schema)
        if output_schema:
            artifact.set_output_schema(output_schema)
        if packages:
            artifact.set_packages(packages)

        self.session.add(artifact)
        self.session.flush()
        return artifact

    def get_artifact(self, artifact_id: str) -> SoftwareArtifact | None:
        """Return a SoftwareArtifact by its own primary key, or None."""
        return self.session.get(SoftwareArtifact, artifact_id)

    def get_artifact_by_fact_id(self, fact_id: str) -> SoftwareArtifact | None:
        """Return the SoftwareArtifact linked to a given Fact, or None."""
        return self.session.execute(
            select(SoftwareArtifact).where(SoftwareArtifact.fact_id == fact_id)
        ).scalar_one_or_none()

    def list_artifacts(
        self,
        artifact_type: SoftwareArtifactType | None = None,
        language: ProgrammingLanguage | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[SoftwareArtifact]:
        """
        Return SoftwareArtifacts, optionally filtered by type and/or language.

        Results are joined with their parent Fact and ordered by Fact title.
        """
        stmt = (
            select(SoftwareArtifact)
            .join(SoftwareArtifact.fact)
            .order_by(Fact.title)
        )
        if artifact_type is not None:
            stmt = stmt.where(SoftwareArtifact.artifact_type == artifact_type)
        if language is not None:
            stmt = stmt.where(SoftwareArtifact.language == language)
        stmt = stmt.offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    # ==================================================================
    # BenchmarkTest — Add / List / Run
    # ==================================================================

    def add_benchmark_test(
        self,
        artifact_id: str,
        name: str,
        test_code: str,
        *,
        description: str | None = None,
        expected_output: Any = None,
        tolerance: float | None = None,
    ) -> BenchmarkTest:
        """
        Add a benchmark test to a SoftwareArtifact.

        Args:
            artifact_id:     PK of the target :class:`SoftwareArtifact`.
            name:            Short unique name for this test within the artifact.
            test_code:       Runnable test code.  For Python artifacts the code
                             should assign the outcome to a variable named
                             ``result`` so the runner can capture it.
            description:     Optional human-readable description of the test.
            expected_output: Optional expected value for ``result``.  Will be
                             JSON-serialised.
            tolerance:       Absolute tolerance for floating-point comparisons.

        Returns:
            The new :class:`BenchmarkTest`.

        Raises:
            ValueError: if the artifact is not found.
        """
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError(f"SoftwareArtifact not found: {artifact_id!r}")

        test = BenchmarkTest(
            artifact_id=artifact_id,
            name=name,
            test_code=test_code,
            description=description,
            tolerance=tolerance,
        )
        if expected_output is not None:
            test.set_expected_output(expected_output)

        self.session.add(test)
        self.session.flush()
        return test

    def list_benchmark_tests(
        self, artifact_id: str
    ) -> Sequence[BenchmarkTest]:
        """Return all benchmark tests for the given artifact, ordered by name."""
        return self.session.execute(
            select(BenchmarkTest)
            .where(BenchmarkTest.artifact_id == artifact_id)
            .order_by(BenchmarkTest.name)
        ).scalars().all()

    def run_benchmark(
        self,
        artifact_id: str,
        test_id: str | None = None,
    ) -> list[dict]:
        """
        Execute benchmark test(s) for a SoftwareArtifact and return results.

        Only Python artifacts are supported for execution.  The test code is
        executed in an isolated namespace via :func:`exec`.  The code should
        assign its outcome to a variable named ``result``; that value is then
        compared against ``expected_output_json`` when present.

        Args:
            artifact_id: PK of the :class:`SoftwareArtifact` to benchmark.
            test_id:     Run only this specific test; ``None`` runs all tests.

        Returns:
            A list of result dicts with keys:
            ``test_id``, ``name``, ``passed``, ``result``, ``elapsed_ms``,
            ``error``.

        Raises:
            ValueError: if the artifact is not found or language is unsupported.
        """
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError(f"SoftwareArtifact not found: {artifact_id!r}")

        if artifact.language != ProgrammingLanguage.PYTHON:
            raise ValueError(
                f"Benchmark execution is only supported for Python artifacts "
                f"(artifact language: {artifact.language!r})."
            )

        tests = (
            artifact.benchmark_tests
            if test_id is None
            else [t for t in artifact.benchmark_tests if t.id == test_id]
        )

        # Provide the artifact's own code in the execution namespace so test
        # code can import or call functions defined within it directly.
        shared_namespace: dict[str, Any] = {}
        try:
            exec(  # noqa: S102
                compile(artifact.code, f"<artifact:{artifact.id}>", "exec"),
                shared_namespace,
            )
        except Exception as exc:
            return [
                {
                    "test_id": None,
                    "name": "__artifact_load__",
                    "passed": False,
                    "result": None,
                    "elapsed_ms": None,
                    "error": f"Failed to load artifact code: {exc}",
                }
            ]

        results = []
        for test in tests:
            namespace = dict(shared_namespace)  # fresh copy per test
            error = None
            result_value = None
            elapsed_ms: float | None = None
            passed: bool | None = None

            try:
                start = time.perf_counter()
                exec(  # noqa: S102
                    compile(test.test_code, f"<benchmark:{test.name}>", "exec"),
                    namespace,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000
                result_value = namespace.get("result")

                if test.expected_output_json:
                    expected = json.loads(test.expected_output_json)
                    if (
                        test.tolerance is not None
                        and isinstance(result_value, (int, float))
                        and isinstance(expected, (int, float))
                    ):
                        passed = abs(float(result_value) - float(expected)) <= test.tolerance
                    else:
                        passed = result_value == expected
                else:
                    passed = True  # no expected output — pass if no exception raised

            except Exception as exc:
                error = str(exc)
                passed = False

            results.append(
                {
                    "test_id": test.id,
                    "name": test.name,
                    "passed": passed,
                    "result": result_value,
                    "elapsed_ms": elapsed_ms,
                    "error": error,
                }
            )

        return results

    # ==================================================================
    # ProjectPackage — Add / List / Generate requirements
    # ==================================================================

    def add_project_package(
        self,
        project_id: str,
        package_name: str,
        package_version: str | None = None,
        language: ProgrammingLanguage = ProgrammingLanguage.PYTHON,
        notes: str | None = None,
    ) -> ProjectPackage:
        """
        Declare a package dependency for a Project.

        Idempotent: if the combination of ``project_id``, ``package_name``,
        and ``language`` already exists the existing record is returned
        unchanged.

        Args:
            project_id:      PK of the :class:`~factdb.project_models.Project`.
            package_name:    Package name (e.g. ``"numpy"``).
            package_version: Version specifier (e.g. ``">=1.24.0"``).
            language:        Target language (default: python).
            notes:           Optional human-readable note.

        Returns:
            The :class:`ProjectPackage` record.

        Raises:
            ValueError: if the project is not found.
        """
        if self.session.get(Project, project_id) is None:
            raise ValueError(f"Project not found: {project_id!r}")

        existing = self.session.execute(
            select(ProjectPackage).where(
                ProjectPackage.project_id == project_id,
                ProjectPackage.package_name == package_name,
                ProjectPackage.language == language,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        pkg = ProjectPackage(
            project_id=project_id,
            package_name=package_name,
            package_version=package_version,
            language=language,
            notes=notes,
        )
        self.session.add(pkg)
        self.session.flush()
        return pkg

    def list_project_packages(
        self,
        project_id: str,
        language: ProgrammingLanguage | None = None,
    ) -> Sequence[ProjectPackage]:
        """Return all package dependencies for a project, ordered by name."""
        stmt = (
            select(ProjectPackage)
            .where(ProjectPackage.project_id == project_id)
            .order_by(ProjectPackage.language, ProjectPackage.package_name)
        )
        if language is not None:
            stmt = stmt.where(ProjectPackage.language == language)
        return self.session.execute(stmt).scalars().all()

    def generate_requirements_txt(
        self, project_id: str
    ) -> str:
        """
        Generate a ``requirements.txt``-style string for a project's Python
        package dependencies.

        Returns:
            A newline-separated string in ``package[version]`` format,
            suitable for writing directly to ``requirements.txt``.  Returns
            an empty string if no Python packages are declared.
        """
        packages = self.list_project_packages(
            project_id, language=ProgrammingLanguage.PYTHON
        )
        lines = []
        for pkg in packages:
            line = pkg.package_name
            if pkg.package_version:
                line += pkg.package_version
            lines.append(line)
        return "\n".join(lines)
