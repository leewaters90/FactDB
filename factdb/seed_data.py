"""
Seed data — engineering facts for FactDB.

.. deprecated::
    The authoritative source of fact data has moved to the JSON folder tree
    under ``data/facts/``.  This module is retained as an empty stub for
    backward compatibility only.  Use ``factdb seed`` to populate the
    database from the JSON files.
"""

from __future__ import annotations

ENGINEERING_FACTS: list[dict] = []
FACT_RELATIONSHIPS: list[dict] = []
