"""
Software seeder — loads SoftwareArtifact, BenchmarkTest, and ProjectPackage
records from the JSON seed files under ``data/software/``.

Directory layout::

    data/software/
        functions/        ← SoftwareArtifactType.FUNCTION JSON files
        transforms/       ← SoftwareArtifactType.TRANSFORM JSON files

Each JSON file describes one artifact and may include an optional
``benchmark_tests`` array.

Usage::

    from factdb.software_seeder import seed_software
    result = seed_software(session)
    session.commit()
"""

from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy.orm import Session

from factdb.software_models import ProgrammingLanguage, SoftwareArtifactType
from factdb.software_repository import SoftwareRepository

_DATA_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "software"
)

_TYPE_DIRS: dict[SoftwareArtifactType, str] = {
    SoftwareArtifactType.FUNCTION: "functions",
    SoftwareArtifactType.TRANSFORM: "transforms",
}


def _load_json_files(directory: str) -> list[dict[str, Any]]:
    """Return all JSON objects found in ``*.json`` files under *directory*."""
    items = []
    if not os.path.isdir(directory):
        return items
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".json"):
            fpath = os.path.join(directory, fname)
            with open(fpath, encoding="utf-8") as fh:
                items.append(json.load(fh))
    return items


def seed_software(session: Session) -> dict:
    """
    Seed software artifacts and their benchmark tests from JSON files.

    Skips artifacts whose Fact title already exists in the database (idempotent).

    Returns:
        dict with counts: ``artifacts_created``, ``artifacts_skipped``,
        ``benchmarks_created``.
    """
    from factdb.repository import FactRepository

    fact_repo = FactRepository(session)
    sw_repo = SoftwareRepository(session)

    artifacts_created = 0
    artifacts_skipped = 0
    benchmarks_created = 0

    for artifact_type, subdir in _TYPE_DIRS.items():
        directory = os.path.join(_DATA_ROOT, subdir)
        for data in _load_json_files(directory):
            title = data["title"]

            # Skip if a Fact with this title already exists
            from sqlalchemy import select
            from factdb.models import Fact

            existing_fact = session.execute(
                select(Fact).where(Fact.title == title)
            ).scalar_one_or_none()

            if existing_fact is not None:
                artifacts_skipped += 1
                continue

            language = ProgrammingLanguage(data.get("language", "python"))
            artifact = sw_repo.create_artifact(
                title=title,
                content=data["content"],
                artifact_type=artifact_type,
                code=data["code"],
                language=language,
                language_version=data.get("language_version"),
                signature=data.get("signature"),
                input_schema=data.get("input_schema"),
                output_schema=data.get("output_schema"),
                packages=data.get("packages"),
                domain=data.get("domain", "software"),
                category=data.get("category"),
                tags=data.get("tags", []),
            )
            session.flush()
            artifacts_created += 1

            for bt in data.get("benchmark_tests", []):
                expected = bt.get("expected_output")
                sw_repo.add_benchmark_test(
                    artifact_id=artifact.id,
                    name=bt["name"],
                    test_code=bt["test_code"],
                    description=bt.get("description"),
                    expected_output=expected,
                    tolerance=bt.get("tolerance"),
                )
                benchmarks_created += 1

    session.flush()
    return {
        "artifacts_created": artifacts_created,
        "artifacts_skipped": artifacts_skipped,
        "benchmarks_created": benchmarks_created,
    }
