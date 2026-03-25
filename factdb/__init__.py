"""
FactDB — A structured fact database for engineering knowledge.

Designed to support small AI models in planning and executing complex
engineering tasks, with a reasoning architecture (decision trees, expert
systems) built on top.
"""

from factdb.database import get_engine, init_db
from factdb.models import (
    Fact,
    FactVersion,
    FactVerification,
    FactRelationship,
    Tag,
    DetailLevel,
    FactStatus,
    VerificationStatus,
    RelationshipType,
    EngineeringDomain,
)
from factdb.repository import FactRepository
from factdb.search import FactSearch
from factdb.verification import VerificationWorkflow
from factdb.reasoning import ReasoningEngine

__all__ = [
    "get_engine",
    "init_db",
    "Fact",
    "FactVersion",
    "FactVerification",
    "FactRelationship",
    "Tag",
    "DetailLevel",
    "FactStatus",
    "VerificationStatus",
    "RelationshipType",
    "EngineeringDomain",
    "FactRepository",
    "FactSearch",
    "VerificationWorkflow",
    "ReasoningEngine",
]
