"""
Device design seed data — engineering facts for FactDB.

.. deprecated::
    The authoritative source of fact data has moved to the JSON folder tree
    under ``data/facts/``.  This module is retained as an empty stub for
    backward compatibility only.  Use ``factdb seed-devices`` to populate
    the database from the JSON files.
"""

from __future__ import annotations

DEVICE_FACTS: list[dict] = []
DEVICE_FACT_RELATIONSHIPS: list[dict] = []
