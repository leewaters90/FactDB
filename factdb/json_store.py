"""
JSON-file-based fact store for FactDB.

Each fact is persisted as a single JSON file under a folder hierarchy::

    {base_dir}/{domain}/{category}/{fact_id}.json

This makes the fact database fully human-readable and editable in any text
editor or version-control system.  SQLite is retained as a runtime index
(FTS5 search, relationships, verifications, usage logs); the JSON files are
the canonical source of truth for fact *content*.

Example tree::

    data/facts/
        mechanical/
            thermodynamics/
                3f4a...json
                9c1b...json
            dynamics/
                7e2d...json
        electrical/
            circuit-theory/
                a1b2...json
        _general/
            misc-fact-id.json
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterator

# Fields that reflect runtime SQLite state and should not be written to the
# human-readable JSON files (they would go stale between edits).
_RUNTIME_FIELDS = frozenset({"use_count", "last_used_at"})

# Default location — sibling ``data/facts`` directory next to the package root.
DEFAULT_FACTS_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "facts"
)


class JsonFactStore:
    """
    Read/write individual fact JSON files under a base directory.

    Folder structure::

        {base_dir}/{domain}/{category}/{fact_id}.json

    Both *domain* and *category* are slugified (lowercased, spaces replaced
    with hyphens) so the tree is portable across operating systems.

    Args:
        base_dir: Root directory under which all fact JSON files are stored.
                  Defaults to :data:`DEFAULT_FACTS_DIR`.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or DEFAULT_FACTS_DIR)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def slugify(text: str) -> str:
        """Convert *text* to a lowercase, hyphen-separated filesystem slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        return text or "_misc"

    def fact_path(self, fact_dict: dict) -> Path:
        """
        Return the canonical file path for a fact.

        Args:
            fact_dict: Plain dictionary representation of the fact.  Must
                       contain at least ``"id"``, ``"domain"``, and
                       ``"category"`` keys.

        Returns:
            :class:`~pathlib.Path` of the form
            ``{base_dir}/{domain}/{category}/{fact_id}.json``.
        """
        domain = self.slugify(str(fact_dict.get("domain") or "general"))
        category = self.slugify(str(fact_dict.get("category") or "_general"))
        return self.base_dir / domain / category / f"{fact_dict['id']}.json"

    # ------------------------------------------------------------------
    # Write / delete
    # ------------------------------------------------------------------

    def write_fact(self, fact_dict: dict) -> Path:
        """
        Persist *fact_dict* to its JSON file, creating parent directories as
        needed.

        Runtime-only fields (``use_count``, ``last_used_at``) are omitted so
        the file remains human-focused and does not change on every read.

        Args:
            fact_dict: Plain dictionary representation of the fact (e.g.
                       from :meth:`~factdb.models.Fact.to_dict`).

        Returns:
            The :class:`~pathlib.Path` of the written file.
        """
        path = self.fact_path(fact_dict)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in fact_dict.items() if k not in _RUNTIME_FIELDS}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def delete_fact(self, fact_id: str) -> bool:
        """
        Remove the JSON file for *fact_id* by scanning the store.

        Empty parent directories are pruned automatically.

        Args:
            fact_id: Primary key of the fact to remove.

        Returns:
            ``True`` if a file was deleted, ``False`` if not found.
        """
        for path in self._iter_fact_files():
            if path.stem == fact_id:
                path.unlink()
                # Prune empty category and domain directories.
                for parent in (path.parent, path.parent.parent):
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                return True
        return False

    def move_fact(self, fact_id: str, new_fact_dict: dict) -> Path:
        """
        Update the JSON file for *fact_id*, moving it to a new location if
        its domain or category changed.

        Args:
            fact_id:      Primary key of the fact.
            new_fact_dict: Updated plain dictionary representation.

        Returns:
            The :class:`~pathlib.Path` of the new file.
        """
        self.delete_fact(fact_id)
        return self.write_fact(new_fact_dict)

    # ------------------------------------------------------------------
    # Read / iterate
    # ------------------------------------------------------------------

    def load_all(self) -> list[dict]:
        """
        Return all fact dicts found under :attr:`base_dir`.

        Files that fail to parse (e.g. malformed JSON) are silently skipped.

        Returns:
            List of plain dictionaries, one per fact file.
        """
        results: list[dict] = []
        for path in self._iter_fact_files():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data:
                    results.append(data)
            except (json.JSONDecodeError, OSError):
                pass
        return results

    def _iter_fact_files(self) -> Iterator[Path]:
        """Yield all ``*.json`` files found recursively under :attr:`base_dir`."""
        if not self.base_dir.exists():
            return
        yield from self.base_dir.rglob("*.json")
