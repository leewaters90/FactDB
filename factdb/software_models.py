"""
Software artifact ORM models for FactDB.

Hierarchy
---------
SoftwareArtifact  (1:1 with Fact — adds executable code, language, packages)
    └── BenchmarkTest  (1:many — test cases for verification and performance)

ProjectPackage  (many:1 with Project — package dependency for requirements generation)

Architecture notes
------------------
* SoftwareArtifact links to an existing Fact by ``fact_id`` (FK).  The Fact
  carries the title, description, status, tags and versioning; the artifact
  carries the executable details.
* ``artifact_type`` distinguishes *functions* (independently callable,
  verifiable units) from *transforms* (data-shape adapters used to connect
  functions).
* ``packages_json`` stores a list of ``{name, version}`` dicts representing
  the packages required to run this specific artifact.
* BenchmarkTest stores runnable Python (or other language) test code and an
  optional expected output for automatic pass/fail comparison.
* ProjectPackage aggregates package requirements at the project level so a
  ``requirements.txt`` (or equivalent) can be generated from all functions and
  transforms used in a project.
* ``ProgrammingLanguage`` is intentionally extensible — Lua scripting and
  Arduino (C++) support can be added without schema migration by appending
  enum values.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
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

from factdb.models import Base, _new_uuid, _utcnow


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProgrammingLanguage(str, PyEnum):
    """Supported programming languages for software artifacts."""

    PYTHON = "python"
    LUA = "lua"
    ARDUINO = "arduino"   # Arduino C++ subset


class SoftwareArtifactType(str, PyEnum):
    """Distinguishes independently callable functions from data transforms."""

    FUNCTION = "function"
    TRANSFORM = "transform"


# ---------------------------------------------------------------------------
# SoftwareArtifact — 1:1 with Fact, carries the executable details
# ---------------------------------------------------------------------------


class SoftwareArtifact(Base):
    """
    Code artifact linked 1:1 to a :class:`~factdb.models.Fact`.

    The parent Fact provides the title, description, tags, status and
    versioning.  This record carries the executable details: language,
    code, signature, I/O schema, and package dependencies.

    ``artifact_type``
        ``function`` — a short, independently callable and verifiable unit.
        ``transform`` — a data-shape adapter used to bridge two functions.

    ``packages_json``
        JSON list of ``{"name": str, "version": str}`` dicts, e.g.::

            [{"name": "numpy", "version": ">=1.24.0"},
             {"name": "scipy", "version": ">=1.11.0"}]
    """

    __tablename__ = "software_artifacts"
    __table_args__ = (
        Index("ix_software_artifacts_type", "artifact_type"),
        Index("ix_software_artifacts_language", "language"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    fact_id: str = Column(
        String(36),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # --- Artifact classification ---
    artifact_type: str = Column(
        Enum(SoftwareArtifactType),
        nullable=False,
    )
    language: str = Column(
        Enum(ProgrammingLanguage),
        nullable=False,
        default=ProgrammingLanguage.PYTHON,
    )
    language_version: str = Column(String(20), nullable=True)  # e.g. "3.11"

    # --- Code ---
    code: str = Column(Text, nullable=False)
    signature: str = Column(String(500), nullable=True)   # e.g. "def fn(x: float) -> float"

    # --- Schema (JSON) ---
    input_schema_json: str = Column(Text, nullable=True)   # [{name, type, description}]
    output_schema_json: str = Column(Text, nullable=True)  # {type, description}

    # --- Dependencies ---
    packages_json: str = Column(Text, nullable=True)       # [{name, version}]

    # --- Timestamps ---
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # --- Relationships ---
    fact = relationship("Fact")
    benchmark_tests = relationship(
        "BenchmarkTest",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="BenchmarkTest.name",
    )

    # ------------------------------------------------------------------
    # JSON field helpers
    # ------------------------------------------------------------------

    def get_packages(self) -> list[dict[str, str]]:
        """Return the list of package dependencies (empty list if none)."""
        if not self.packages_json:
            return []
        return json.loads(self.packages_json)

    def set_packages(self, packages: list[dict[str, str]]) -> None:
        """Store a list of ``{name, version}`` dicts as JSON."""
        self.packages_json = json.dumps(packages, ensure_ascii=False)

    def get_input_schema(self) -> list[dict[str, Any]]:
        """Return the input parameter schema (empty list if none)."""
        if not self.input_schema_json:
            return []
        return json.loads(self.input_schema_json)

    def set_input_schema(self, schema: list[dict[str, Any]]) -> None:
        self.input_schema_json = json.dumps(schema, ensure_ascii=False)

    def get_output_schema(self) -> dict[str, Any]:
        """Return the output schema (empty dict if none)."""
        if not self.output_schema_json:
            return {}
        return json.loads(self.output_schema_json)

    def set_output_schema(self, schema: dict[str, Any]) -> None:
        self.output_schema_json = json.dumps(schema, ensure_ascii=False)

    def __repr__(self) -> str:
        return (
            f"<SoftwareArtifact type={self.artifact_type!r} "
            f"lang={self.language!r} fact_id={self.fact_id!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fact_id": self.fact_id,
            "fact_title": self.fact.title if self.fact else None,
            "artifact_type": self.artifact_type,
            "language": self.language,
            "language_version": self.language_version,
            "code": self.code,
            "signature": self.signature,
            "input_schema": self.get_input_schema(),
            "output_schema": self.get_output_schema(),
            "packages": self.get_packages(),
            "benchmark_count": len(self.benchmark_tests),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# BenchmarkTest — test cases for a SoftwareArtifact
# ---------------------------------------------------------------------------


class BenchmarkTest(Base):
    """
    A benchmark / test case for a :class:`SoftwareArtifact`.

    ``test_code``
        Runnable code in the artifact's language.  For Python artifacts the
        code should assign the value under test to a variable named
        ``result`` so the runner can capture it.  Example::

            result = celsius_to_fahrenheit(100)

    ``expected_output_json``
        Optional JSON-serialised expected value for the ``result`` variable.
        When absent the test is recorded as passing if it executes without
        raising an exception.

    ``tolerance``
        Optional absolute tolerance for floating-point ``result`` comparisons.
        Ignored for non-numeric results.
    """

    __tablename__ = "benchmark_tests"
    __table_args__ = (
        UniqueConstraint("artifact_id", "name", name="uq_benchmark_test"),
        Index("ix_benchmark_tests_artifact", "artifact_id"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    artifact_id: str = Column(
        String(36),
        ForeignKey("software_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: str = Column(String(300), nullable=False)
    description: str = Column(Text, nullable=True)
    test_code: str = Column(Text, nullable=False)
    expected_output_json: str = Column(Text, nullable=True)
    tolerance: float = Column(Float, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    artifact = relationship("SoftwareArtifact", back_populates="benchmark_tests")

    def get_expected_output(self) -> Any:
        """Return the expected output value, or ``None`` if not set."""
        if not self.expected_output_json:
            return None
        return json.loads(self.expected_output_json)

    def set_expected_output(self, value: Any) -> None:
        """Serialise ``value`` to JSON and store it."""
        self.expected_output_json = json.dumps(value, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"<BenchmarkTest name={self.name!r} artifact_id={self.artifact_id!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "name": self.name,
            "description": self.description,
            "test_code": self.test_code,
            "expected_output": self.get_expected_output(),
            "tolerance": self.tolerance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# ProjectPackage — package requirement at the project level
# ---------------------------------------------------------------------------


class ProjectPackage(Base):
    """
    A package dependency declared at the :class:`~factdb.project_models.Project`
    level.

    Aggregates the packages needed across all functions and transforms used in
    a project, allowing a ``requirements.txt`` (Python) or equivalent to be
    generated automatically.

    ``package_version``
        PEP 440-style version specifier, e.g. ``">=1.24.0"`` or ``"==2.1.3"``.
        ``None`` means *any version*.
    """

    __tablename__ = "project_packages"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "package_name", "language",
            name="uq_project_package",
        ),
        Index("ix_project_packages_project", "project_id"),
    )

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    project_id: str = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    package_name: str = Column(String(200), nullable=False)
    package_version: str = Column(String(50), nullable=True)   # e.g. ">=1.24.0"
    language: str = Column(
        Enum(ProgrammingLanguage),
        nullable=False,
        default=ProgrammingLanguage.PYTHON,
    )
    notes: str = Column(Text, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    project = relationship("Project")

    def __repr__(self) -> str:
        ver = self.package_version or "*"
        return (
            f"<ProjectPackage {self.package_name}{ver} "
            f"lang={self.language!r} project={self.project_id!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "language": self.language,
            "notes": self.notes,
        }
