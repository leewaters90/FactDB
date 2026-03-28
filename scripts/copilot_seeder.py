#!/usr/bin/env python3
"""
copilot_seeder.py — Continuous AI-driven FactDB project seeder.

Runs the GitHub Copilot CLI in non-interactive mode to autonomously devise,
design, and persist new FactDB projects (including any required new facts,
relationships, and design elements).

Usage
-----
    # Run indefinitely (default):
    python3 scripts/copilot_seeder.py

    # Run a fixed number of iterations:
    python3 scripts/copilot_seeder.py --count 5

    # Dry-run (prompts printed, Copilot not invoked, JSON not saved):
    python3 scripts/copilot_seeder.py --dry-run

    # Override Copilot model:
    python3 scripts/copilot_seeder.py --model gpt-5.2

    # Pause between iterations (seconds):
    python3 scripts/copilot_seeder.py --pause 10

    # Seed the DB after every N project additions:
    python3 scripts/copilot_seeder.py --seed-every 3

Requirements
------------
    pip install click  (already a FactDB dependency)
    gh copilot CLI must be installed and authenticated.

How it works
------------
1.  Reads the current FactDB state (all fact titles, design element titles,
    and project titles) directly from the JSON files so that Copilot can avoid
    duplicates.

2.  Constructs a detailed prompt describing the task:
      - Invent a novel engineering project.
      - List any new facts required (JSON schema provided).
      - List any new design elements required (JSON schema provided).
      - Produce the full project JSON (with element_interactions and
        integration_code).
      - Output *only* a valid JSON envelope — no prose.

3.  Calls ``gh copilot -p "<prompt>" --allow-all-tools`` in non-interactive
    mode and captures stdout.

4.  Parses the JSON envelope from the response (robust extraction handles any
    leading/trailing text from Copilot).

5.  Validates each piece against the FactDB JSON schemas and saves:
      - New fact files → data/facts/{domain}/{category}/{uuid}.json
      - New design-element files → data/projects/design-elements/{slug}.json
      - New project file → data/projects/projects/{slug}.json

6.  Optionally re-seeds the SQLite DB (``factdb seed && factdb seed-projects``).

7.  Appends a summary line to PROJECT_QUEUE.md.

8.  Loops back to step 1.

Output envelope schema expected from Copilot
---------------------------------------------
{
  "new_facts": [
    {
      "id": "<uuid>",
      "title": "...",
      "domain": "electrical|mechanical|...",
      "category": "...",
      "subcategory": "...",
      "detail_level": "fundamental|intermediate|advanced",
      "content": "...",
      "extended_content": "...",
      "formula": "...",
      "units": "...",
      "source": "...",
      "confidence_score": 0.95,
      "status": "draft",
      "version": 1,
      "tags": ["..."],
      "created_by": "copilot-seeder"
    }
  ],
  "new_relationships": [
    {
      "source_title": "...",
      "target_title": "...",
      "relationship_type": "depends_on|supports",
      "weight": 0.9,
      "description": "..."
    }
  ],
  "new_design_elements": [
    {
      "title": "...",
      "component_category": "power|sensing|actuation|control|communication|software|mechanical|processing",
      "design_question": "...",
      "selected_approach": "...",
      "rationale": "...",
      "alternatives": [{"approach": "...", "reason_rejected": "..."}],
      "verification_notes": "...",
      "supporting_fact_titles": ["..."]
    }
  ],
  "project": {
    "title": "...",
    "description": "...",
    "objective": "...",
    "constraints": "...",
    "domain": "mechanical|electrical|civil|software|chemical|aerospace|materials|systems|general",
    "status": "completed",
    "supporting_fact_titles": ["..."],
    "design_element_titles": ["..."],
    "element_usage_notes": {"ElementTitle": "usage note..."},
    "element_interactions": [
      {"from": "...", "to": "...", "data": "...", "description": "..."}
    ],
    "integration_code": "/* ... */"
  }
}
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

# ---------------------------------------------------------------------------
# Paths (relative to repo root, resolved at runtime)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
FACTS_DIR = REPO_ROOT / "data" / "facts"
ELEMENTS_DIR = REPO_ROOT / "data" / "projects" / "design-elements"
PROJECTS_DIR = REPO_ROOT / "data" / "projects" / "projects"
RELATIONSHIPS_FILE = FACTS_DIR / "_relationships.json"
QUEUE_FILE = REPO_ROOT / "PROJECT_QUEUE.md"

# ---------------------------------------------------------------------------
# Valid enum values (mirrored from factdb models to avoid import overhead)
# ---------------------------------------------------------------------------
VALID_DOMAINS = {
    "mechanical", "electrical", "civil", "software",
    "chemical", "aerospace", "materials", "systems", "general",
}
VALID_CATEGORIES = {
    "power", "sensing", "actuation", "control",
    "communication", "software", "mechanical", "processing",
}
VALID_RELATIONSHIP_TYPES = {"depends_on", "supports"}
VALID_DETAIL_LEVELS = {"fundamental", "intermediate", "advanced"}
VALID_STATUSES = {"concept", "in_design", "under_review", "completed", "deprecated"}


# ---------------------------------------------------------------------------
# State readers
# ---------------------------------------------------------------------------

def load_existing_titles() -> dict[str, set[str]]:
    """Return sets of existing titles for facts, design elements, and projects."""
    fact_titles: set[str] = set()
    for path in FACTS_DIR.rglob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            data = json.loads(path.read_text())
            if t := data.get("title"):
                fact_titles.add(t)
        except Exception:
            pass

    element_titles: set[str] = set()
    for path in ELEMENTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            if t := data.get("title"):
                element_titles.add(t)
        except Exception:
            pass

    project_titles: set[str] = set()
    for path in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            if t := data.get("title"):
                project_titles.add(t)
        except Exception:
            pass

    return {
        "facts": fact_titles,
        "elements": element_titles,
        "projects": project_titles,
    }


def load_existing_relationships() -> list[dict]:
    if RELATIONSHIPS_FILE.exists():
        return json.loads(RELATIONSHIPS_FILE.read_text())
    return []


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(existing: dict[str, set[str]]) -> str:
    """Build the full Copilot prompt with current FactDB context."""
    fact_list = "\n".join(f"  - {t}" for t in sorted(existing["facts"]))
    element_list = "\n".join(f"  - {t}" for t in sorted(existing["elements"]))
    project_list = "\n".join(f"  - {t}" for t in sorted(existing["projects"]))

    return f"""You are a senior embedded-systems / mechatronics engineer designing projects for FactDB — an engineering knowledge base.

FactDB stores:
  - Engineering FACTS (physical laws, sensor datasheets, algorithms, materials principles).
  - DESIGN ELEMENTS (reusable hardware/software building blocks, each justified by supporting facts).
  - PROJECTS (fully designed mechatronics / electrical / systems projects, each assembled from design elements).

Your task: INVENT ONE NEW PROJECT that does NOT already exist in FactDB.

Constraints on the project:
  - Must be genuinely novel — not a variation of any existing project listed below.
  - Must be practical and buildable with off-the-shelf hobbyist/maker components (Arduino, ESP32, sensors, actuators).
  - Must have a clear engineering purpose.
  - Must use at least 4 design elements.
  - Must include element_interactions and a complete integration_code sketch (Arduino C++ or MicroPython).
  - Domain must be one of: mechanical, electrical, civil, software, chemical, aerospace, materials, systems, general.

For every required design element or fact that is NOT in the existing lists below, you MUST invent and provide it in full.

=== EXISTING FACT TITLES (do NOT duplicate these) ===
{fact_list}

=== EXISTING DESIGN ELEMENT TITLES (do NOT duplicate these) ===
{element_list}

=== EXISTING PROJECT TITLES (do NOT duplicate these) ===
{project_list}

=== OUTPUT REQUIREMENTS ===
Respond with ONLY a single valid JSON object (no markdown, no prose, no code fences).
The JSON must exactly match this schema:

{{
  "new_facts": [
    {{
      "id": "<new UUID v4>",
      "title": "<unique title not in existing list>",
      "domain": "<one of: mechanical|electrical|civil|software|chemical|aerospace|materials|systems|general>",
      "category": "<short category slug, e.g. sensors|motors|thermodynamics|algorithms>",
      "subcategory": "<more specific, e.g. temperature-measurement>",
      "detail_level": "<fundamental|intermediate|advanced>",
      "content": "<concise 1-3 sentence factual summary>",
      "extended_content": "<detailed explanation with practical notes, calibration, gotchas, 150-300 words>",
      "formula": "<primary formula if applicable, else null>",
      "units": "<formula variable units, else null>",
      "source": "<textbook, datasheet, or standard>",
      "source_url": null,
      "confidence_score": 0.95,
      "status": "draft",
      "version": 1,
      "tags": ["tag1", "tag2"],
      "created_by": "copilot-seeder"
    }}
  ],
  "new_relationships": [
    {{
      "source_title": "<existing or new fact title>",
      "target_title": "<existing or new fact title>",
      "relationship_type": "<depends_on|supports>",
      "weight": 0.9,
      "description": "<one sentence>"
    }}
  ],
  "new_design_elements": [
    {{
      "title": "<unique element title not in existing list>",
      "component_category": "<one of: power|sensing|actuation|control|communication|software|mechanical|processing>",
      "design_question": "<the engineering question this element answers>",
      "selected_approach": "<specific components + wiring + library choices>",
      "rationale": "<why this approach was chosen, 2-3 sentences>",
      "alternatives": [
        {{"approach": "<alt approach>", "reason_rejected": "<why rejected>"}}
      ],
      "verification_notes": "<which fact titles support this element>",
      "supporting_fact_titles": ["<fact title 1>", "<fact title 2>"]
    }}
  ],
  "project": {{
    "title": "<unique project title not in existing list>",
    "description": "<2-3 sentence overview>",
    "objective": "<measurable goals>",
    "constraints": "<budget, voltage, enclosure, platform>",
    "domain": "<one of: mechanical|electrical|civil|software|chemical|aerospace|materials|systems|general>",
    "status": "completed",
    "supporting_fact_titles": ["<existing or new fact title>"],
    "design_element_titles": ["<existing or new element title>"],
    "element_usage_notes": {{
      "<ElementTitle>": "<how this element is specifically configured in this project>"
    }},
    "element_interactions": [
      {{
        "from": "<element title>",
        "to": "<element title>",
        "data": "<data type, protocol, signal>",
        "description": "<what flows between them and why>"
      }}
    ],
    "integration_code": "<complete Arduino C++ or MicroPython sketch as a single escaped string>"
  }}
}}

Generate one complete, novel, well-engineered project now. Output valid JSON only.
"""


# ---------------------------------------------------------------------------
# Copilot invocation
# ---------------------------------------------------------------------------

def call_copilot(prompt: str, model: str, timeout: int = 300) -> str:
    """Invoke ``gh copilot`` non-interactively and return raw stdout."""
    cmd = [
        "gh", "copilot",
        "-p", prompt,
        "--allow-all-tools",
        "--autopilot",
    ]
    if model:
        cmd += ["--model", model]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh copilot exited {result.returncode}:\n{result.stderr[:1000]}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# JSON extraction + validation
# ---------------------------------------------------------------------------

def extract_json(raw: str) -> dict:
    """
    Robustly extract the first complete JSON object from *raw*.

    Copilot may wrap its response in markdown code fences or add leading prose.
    """
    # Try to strip markdown fences
    stripped = re.sub(r"```(?:json)?\s*", "", raw)
    stripped = re.sub(r"```", "", stripped)

    # Find the outermost { ... }
    start = stripped.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Copilot response")

    # Walk to find matching close brace
    depth = 0
    end = -1
    in_string = False
    escape = False
    for i, ch in enumerate(stripped[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        raise ValueError("Unbalanced JSON braces in Copilot response")

    candidate = stripped[start:end]
    return json.loads(candidate)


def _slug(title: str) -> str:
    """Convert a project/element title to a filename slug."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:80]


def validate_fact(fact: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors = []
    for field in ("id", "title", "domain", "category", "content"):
        if not fact.get(field):
            errors.append(f"fact missing required field: {field}")
    if fact.get("domain") not in VALID_DOMAINS:
        errors.append(f"fact domain '{fact.get('domain')}' not valid")
    if fact.get("detail_level") not in VALID_DETAIL_LEVELS:
        fact["detail_level"] = "intermediate"  # default silently
    return errors


def validate_element(el: dict) -> list[str]:
    errors = []
    for field in ("title", "component_category", "selected_approach"):
        if not el.get(field):
            errors.append(f"element missing required field: {field}")
    if el.get("component_category") not in VALID_CATEGORIES:
        errors.append(f"element category '{el.get('component_category')}' not valid")
    return errors


def validate_project(proj: dict) -> list[str]:
    errors = []
    for field in ("title", "description", "domain", "integration_code"):
        if not proj.get(field):
            errors.append(f"project missing required field: {field}")
    if proj.get("domain") not in VALID_DOMAINS:
        errors.append(f"project domain '{proj.get('domain')}' not valid")
    if proj.get("status") not in VALID_STATUSES:
        proj["status"] = "completed"
    return errors


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_fact(fact: dict, dry_run: bool) -> Path:
    """Write a new fact JSON file; return its path."""
    domain = fact.get("domain", "general")
    category = re.sub(r"[^a-z0-9-]", "-", fact.get("category", "misc").lower())
    target_dir = FACTS_DIR / domain / category
    fact_id = fact.get("id") or str(uuid.uuid4())
    fact["id"] = fact_id
    path = target_dir / f"{fact_id}.json"
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fact, indent=2, ensure_ascii=False))
    return path


def save_element(el: dict, dry_run: bool) -> Path:
    """Write a new design element JSON file; return its path."""
    slug = _slug(el["title"])
    path = ELEMENTS_DIR / f"{slug}.json"
    if not dry_run:
        path.write_text(json.dumps(el, indent=2, ensure_ascii=False))
    return path


def save_project(proj: dict, dry_run: bool) -> Path:
    """Write a new project JSON file; return its path."""
    slug = _slug(proj["title"])
    path = PROJECTS_DIR / f"{slug}.json"
    if not dry_run:
        path.write_text(json.dumps(proj, indent=2, ensure_ascii=False))
    return path


def append_relationships(new_rels: list[dict], dry_run: bool) -> int:
    """Merge new relationships into _relationships.json; return count added."""
    existing = load_existing_relationships()
    existing_keys = {
        (r["source_title"], r["target_title"]) for r in existing
    }
    added = 0
    for rel in new_rels:
        rt = rel.get("relationship_type", "depends_on")
        if rt not in VALID_RELATIONSHIP_TYPES:
            rel["relationship_type"] = "depends_on"
        key = (rel.get("source_title", ""), rel.get("target_title", ""))
        if key not in existing_keys and all(key):
            existing.append(rel)
            existing_keys.add(key)
            added += 1
    if not dry_run and added:
        RELATIONSHIPS_FILE.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False)
        )
    return added


def append_queue_entry(title: str, n_facts: int, n_elements: int, dry_run: bool):
    """Append a one-line summary to PROJECT_QUEUE.md."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = (
        f"\n- [x] **{title}** — "
        f"{n_facts} new fact(s), {n_elements} new element(s) — "
        f"auto-seeded {ts} ✓"
    )
    if not dry_run and QUEUE_FILE.exists():
        with QUEUE_FILE.open("a", encoding="utf-8") as f:
            f.write(line)


# ---------------------------------------------------------------------------
# Seed DB helper
# ---------------------------------------------------------------------------

def reseed_db(verbose: bool):
    """Re-run `factdb seed` and `factdb seed-projects` to import new JSON."""
    for cmd in [
        [sys.executable, "-m", "factdb.cli", "seed"],
        [sys.executable, "-m", "factdb.cli", "seed-projects"],
    ]:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if verbose:
            click.echo(result.stdout.strip())
        if result.returncode != 0:
            click.echo(
                click.style(f"  ⚠  seed command failed: {result.stderr[:300]}", fg="yellow")
            )


# ---------------------------------------------------------------------------
# Core loop iteration
# ---------------------------------------------------------------------------

def run_one_iteration(
    existing: dict[str, set[str]],
    model: str,
    dry_run: bool,
    verbose: bool,
) -> dict[str, Any]:
    """
    Run one prompt-parse-save cycle.

    Returns a summary dict with keys: title, n_facts, n_elements,
    n_relationships, saved_paths, errors.
    """
    summary: dict[str, Any] = {
        "title": None,
        "n_facts": 0,
        "n_elements": 0,
        "n_relationships": 0,
        "saved_paths": [],
        "errors": [],
    }

    # 1. Build prompt
    prompt = build_prompt(existing)
    if verbose:
        click.echo(click.style("  Prompt length: ", dim=True) + str(len(prompt)))

    # 2. Call Copilot (or mock in dry-run)
    if dry_run:
        click.echo(click.style("  [dry-run] Skipping Copilot invocation.", fg="cyan"))
        click.echo(click.style("  Sample prompt (first 500 chars):", dim=True))
        click.echo(prompt[:500] + "…")
        return summary

    click.echo(click.style("  Invoking Copilot CLI…", dim=True))
    try:
        raw = call_copilot(prompt, model)
    except (subprocess.TimeoutExpired, RuntimeError) as exc:
        summary["errors"].append(str(exc))
        return summary

    if verbose:
        click.echo(click.style("  Raw response length: ", dim=True) + str(len(raw)))

    # 3. Extract + parse JSON
    try:
        envelope = extract_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        summary["errors"].append(f"JSON parse error: {exc}")
        if verbose:
            click.echo(click.style("  Raw (first 2000 chars):", dim=True))
            click.echo(raw[:2000])
        return summary

    # 4. Validate + save facts
    for fact in envelope.get("new_facts", []):
        errs = validate_fact(fact)
        if errs:
            summary["errors"].extend(errs)
            continue
        if fact["title"] in existing["facts"]:
            click.echo(
                click.style(f"    ↳ Fact already exists, skipping: {fact['title']}", fg="yellow")
            )
            continue
        path = save_fact(fact, dry_run)
        existing["facts"].add(fact["title"])
        summary["n_facts"] += 1
        summary["saved_paths"].append(str(path))
        click.echo(click.style(f"    ✓ Fact: {fact['title']}", fg="green"))

    # 5. Validate + save design elements
    for el in envelope.get("new_design_elements", []):
        errs = validate_element(el)
        if errs:
            summary["errors"].extend(errs)
            continue
        if el["title"] in existing["elements"]:
            click.echo(
                click.style(f"    ↳ Element already exists, skipping: {el['title']}", fg="yellow")
            )
            continue
        path = save_element(el, dry_run)
        existing["elements"].add(el["title"])
        summary["n_elements"] += 1
        summary["saved_paths"].append(str(path))
        click.echo(click.style(f"    ✓ Element: {el['title']}", fg="green"))

    # 6. Save project
    proj = envelope.get("project", {})
    errs = validate_project(proj)
    if errs:
        summary["errors"].extend(errs)
    elif proj.get("title") in existing["projects"]:
        click.echo(
            click.style(f"    ↳ Project already exists, skipping: {proj['title']}", fg="yellow")
        )
    else:
        path = save_project(proj, dry_run)
        existing["projects"].add(proj["title"])
        summary["title"] = proj["title"]
        summary["saved_paths"].append(str(path))
        click.echo(click.style(f"    ✓ Project: {proj['title']}", fg="green"))

    # 7. Append relationships
    rels = envelope.get("new_relationships", [])
    summary["n_relationships"] = append_relationships(rels, dry_run)

    # 8. Append queue entry
    if summary["title"]:
        append_queue_entry(
            summary["title"], summary["n_facts"], summary["n_elements"], dry_run
        )

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command(name="copilot-seeder")
@click.option(
    "--count", "-n",
    default=0,
    show_default=True,
    help="Number of projects to generate (0 = infinite).",
)
@click.option(
    "--pause", "-p",
    default=5,
    show_default=True,
    help="Seconds to wait between iterations.",
)
@click.option(
    "--model", "-m",
    default="",
    show_default=True,
    help="Copilot model override (e.g. gpt-5.2). Empty = Copilot default.",
)
@click.option(
    "--seed-every",
    default=1,
    show_default=True,
    help="Re-seed the SQLite DB every N successful project additions.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print prompts without invoking Copilot or writing files.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show extra diagnostic output.",
)
@click.option(
    "--timeout",
    default=300,
    show_default=True,
    help="Seconds before a single Copilot call is aborted.",
)
def main(count, pause, model, seed_every, dry_run, verbose, timeout):
    """
    Continuously prompt GitHub Copilot CLI to design new FactDB projects.

    Each iteration invents a novel project, creates any missing supporting
    facts and design elements, and writes the JSON files into the data/
    directory tree.  The SQLite database is re-seeded automatically.

    Runs until --count iterations complete, or interrupted with Ctrl-C.
    """
    click.echo(
        click.style(
            "╔══════════════════════════════════════════════╗\n"
            "║       FactDB Copilot Continuous Seeder       ║\n"
            "╚══════════════════════════════════════════════╝",
            fg="bright_blue", bold=True,
        )
    )
    if dry_run:
        click.echo(click.style("  Mode: DRY RUN — no files will be written.\n", fg="cyan"))

    iteration = 0
    successes = 0
    total_facts = 0
    total_elements = 0

    try:
        while True:
            iteration += 1
            if count > 0 and iteration > count:
                break

            click.echo(
                click.style(
                    f"\n── Iteration {iteration}"
                    + (f" / {count}" if count else "")
                    + f"  ({datetime.now().strftime('%H:%M:%S')}) ──",
                    fg="bright_cyan", bold=True,
                )
            )

            # Reload existing titles on each iteration to pick up new files
            existing = load_existing_titles()
            click.echo(
                click.style(
                    f"  DB: {len(existing['facts'])} facts | "
                    f"{len(existing['elements'])} elements | "
                    f"{len(existing['projects'])} projects",
                    dim=True,
                )
            )

            summary = run_one_iteration(existing, model, dry_run, verbose)

            if summary["errors"]:
                click.echo(
                    click.style(
                        "  Errors:\n" + "\n".join(f"    • {e}" for e in summary["errors"]),
                        fg="red",
                    )
                )

            if summary["title"]:
                successes += 1
                total_facts += summary["n_facts"]
                total_elements += summary["n_elements"]

                click.echo(
                    click.style(
                        f"  ✔  Added project '{summary['title']}' "
                        f"(+{summary['n_facts']} facts, "
                        f"+{summary['n_elements']} elements, "
                        f"+{summary['n_relationships']} rels)",
                        fg="bright_green",
                    )
                )

                if not dry_run and successes % seed_every == 0:
                    click.echo(click.style("  Reseeding SQLite DB…", dim=True))
                    reseed_db(verbose)
            else:
                click.echo(
                    click.style(
                        "  ⚠  No project saved this iteration.",
                        fg="yellow",
                    )
                )

            if count == 0 or iteration < count:
                if pause > 0:
                    click.echo(
                        click.style(f"  Pausing {pause}s before next iteration…", dim=True)
                    )
                    time.sleep(pause)

    except KeyboardInterrupt:
        click.echo(click.style("\n\nInterrupted by user (Ctrl-C).", fg="yellow"))

    click.echo(
        click.style(
            f"\n── Session complete ──\n"
            f"  Iterations:        {iteration - 1}\n"
            f"  Projects added:    {successes}\n"
            f"  Facts added:       {total_facts}\n"
            f"  Elements added:    {total_elements}\n",
            fg="bright_blue",
        )
    )


if __name__ == "__main__":
    main()
