"""
Tests for JsonFactStore — JSON file-based fact persistence.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from factdb.json_store import JsonFactStore, DEFAULT_FACTS_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_fact(**overrides) -> dict:
    base = {
        "id": "aaaaaaaa-1111-2222-3333-444444444444",
        "title": "Ohm's Law",
        "domain": "electrical",
        "category": "circuit theory",
        "subcategory": "basic circuits",
        "detail_level": "fundamental",
        "content": "V = I * R",
        "extended_content": "Voltage equals current times resistance.",
        "formula": "V = I * R",
        "units": "V, A, Ω",
        "source": "Textbook",
        "source_url": None,
        "confidence_score": 1.0,
        "status": "verified",
        "version": 1,
        "tags": ["circuit", "voltage"],
        "created_by": "tester",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        # Runtime fields that should be excluded from files
        "use_count": 5,
        "last_used_at": "2024-06-01T12:00:00+00:00",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def tmp_store(tmp_path):
    """Return a JsonFactStore backed by a temporary directory."""
    return JsonFactStore(tmp_path)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self):
        assert JsonFactStore.slugify("Circuit Theory") == "circuit-theory"

    def test_spaces_to_hyphens(self):
        assert JsonFactStore.slugify("heat transfer") == "heat-transfer"

    def test_special_chars_stripped(self):
        assert JsonFactStore.slugify("C++ (advanced)") == "c-advanced"

    def test_empty_returns_misc(self):
        assert JsonFactStore.slugify("") == "_misc"

    def test_underscore_to_hyphen(self):
        assert JsonFactStore.slugify("circuit_theory") == "circuit-theory"


# ---------------------------------------------------------------------------
# fact_path
# ---------------------------------------------------------------------------


class TestFactPath:
    def test_path_structure(self, tmp_store):
        fact = _sample_fact()
        path = tmp_store.fact_path(fact)
        assert path.parent.parent.name == "electrical"
        assert path.parent.name == "circuit-theory"
        assert path.name == f"{fact['id']}.json"
        assert path.parent.parent.parent == tmp_store.base_dir

    def test_missing_category_defaults(self, tmp_store):
        fact = _sample_fact(category=None)
        path = tmp_store.fact_path(fact)
        assert path.parent.name == "-general"

    def test_missing_domain_defaults(self, tmp_store):
        fact = _sample_fact(domain=None)
        path = tmp_store.fact_path(fact)
        assert path.parent.parent.name == "general"


# ---------------------------------------------------------------------------
# write_fact
# ---------------------------------------------------------------------------


class TestWriteFact:
    def test_creates_file(self, tmp_store):
        fact = _sample_fact()
        path = tmp_store.write_fact(fact)
        assert path.exists()

    def test_content_is_valid_json(self, tmp_store):
        fact = _sample_fact()
        path = tmp_store.write_fact(fact)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["id"] == fact["id"]
        assert data["title"] == fact["title"]

    def test_runtime_fields_excluded(self, tmp_store):
        fact = _sample_fact()
        path = tmp_store.write_fact(fact)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "use_count" not in data
        assert "last_used_at" not in data

    def test_content_fields_preserved(self, tmp_store):
        fact = _sample_fact()
        path = tmp_store.write_fact(fact)
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in ("title", "domain", "category", "content", "formula", "tags", "status"):
            assert field in data

    def test_creates_parent_directories(self, tmp_store):
        fact = _sample_fact(domain="aerospace", category="propulsion")
        path = tmp_store.write_fact(fact)
        assert path.parent.exists()
        assert path.parent.parent.exists()

    def test_overwrite_existing(self, tmp_store):
        fact = _sample_fact()
        tmp_store.write_fact(fact)
        updated = {**fact, "title": "Updated Title"}
        path = tmp_store.write_fact(updated)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["title"] == "Updated Title"


# ---------------------------------------------------------------------------
# delete_fact
# ---------------------------------------------------------------------------


class TestDeleteFact:
    def test_delete_existing(self, tmp_store):
        fact = _sample_fact()
        path = tmp_store.write_fact(fact)
        assert path.exists()
        result = tmp_store.delete_fact(fact["id"])
        assert result is True
        assert not path.exists()

    def test_delete_nonexistent_returns_false(self, tmp_store):
        result = tmp_store.delete_fact("does-not-exist")
        assert result is False

    def test_delete_prunes_empty_directories(self, tmp_store):
        fact = _sample_fact(domain="civil", category="structural")
        path = tmp_store.write_fact(fact)
        cat_dir = path.parent
        dom_dir = path.parent.parent
        tmp_store.delete_fact(fact["id"])
        assert not cat_dir.exists()
        assert not dom_dir.exists()

    def test_delete_leaves_non_empty_directory(self, tmp_store):
        fact1 = _sample_fact(id="id-001")
        fact2 = _sample_fact(id="id-002")
        tmp_store.write_fact(fact1)
        path2 = tmp_store.write_fact(fact2)
        cat_dir = path2.parent
        tmp_store.delete_fact("id-001")
        # cat_dir still has fact2 → should NOT be removed
        assert cat_dir.exists()


# ---------------------------------------------------------------------------
# move_fact
# ---------------------------------------------------------------------------


class TestMoveFact:
    def test_move_on_category_change(self, tmp_store):
        fact = _sample_fact()
        old_path = tmp_store.write_fact(fact)
        moved_fact = {**fact, "category": "signal processing"}
        new_path = tmp_store.move_fact(fact["id"], moved_fact)
        assert new_path.exists()
        assert not old_path.exists()
        assert new_path.parent.name == "signal-processing"

    def test_move_same_location(self, tmp_store):
        fact = _sample_fact()
        tmp_store.write_fact(fact)
        updated = {**fact, "content": "Updated content."}
        path = tmp_store.move_fact(fact["id"], updated)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["content"] == "Updated content."


# ---------------------------------------------------------------------------
# load_all
# ---------------------------------------------------------------------------


class TestLoadAll:
    def test_empty_store_returns_empty_list(self, tmp_store):
        assert tmp_store.load_all() == []

    def test_loads_written_facts(self, tmp_store):
        fact1 = _sample_fact(id="id-aaa")
        fact2 = _sample_fact(id="id-bbb", domain="mechanical", category="dynamics")
        tmp_store.write_fact(fact1)
        tmp_store.write_fact(fact2)
        results = tmp_store.load_all()
        ids = {r["id"] for r in results}
        assert "id-aaa" in ids
        assert "id-bbb" in ids

    def test_skips_malformed_json(self, tmp_store):
        bad = tmp_store.base_dir / "electrical" / "junk.json"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("{not valid json}", encoding="utf-8")

        fact = _sample_fact()
        tmp_store.write_fact(fact)
        results = tmp_store.load_all()
        # Should contain the valid fact but not crash on the bad file.
        assert len(results) == 1
        assert results[0]["id"] == fact["id"]

    def test_skips_files_without_id(self, tmp_store):
        no_id = tmp_store.base_dir / "misc.json"
        no_id.parent.mkdir(parents=True, exist_ok=True)
        no_id.write_text(json.dumps({"title": "no id here"}), encoding="utf-8")
        results = tmp_store.load_all()
        assert results == []

    def test_nonexistent_base_dir_returns_empty(self, tmp_path):
        store = JsonFactStore(tmp_path / "does_not_exist")
        assert store.load_all() == []


# ---------------------------------------------------------------------------
# DEFAULT_FACTS_DIR constant
# ---------------------------------------------------------------------------


class TestDefaultFactsDir:
    def test_default_dir_is_string(self):
        assert isinstance(DEFAULT_FACTS_DIR, str)

    def test_default_dir_ends_with_facts(self):
        assert DEFAULT_FACTS_DIR.endswith(f"data{os.sep}facts") or \
               DEFAULT_FACTS_DIR.endswith("data/facts")
