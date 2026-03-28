#!/usr/bin/env python3
"""
copilot_seeder.py — Continuous AI-driven FactDB project seeder with
                     rich context injection and convergence tracking.

How it works
------------
Each iteration:

1.  Loads the full FactDB knowledge state from JSON files:
      - Fact summaries grouped by domain → category (title + one-line content)
      - Design-element capability index grouped by component_category
      - Relationship graph (source → target, type)
      - Domain / category coverage map with identified gaps

2.  Computes a convergence snapshot — measures how saturated the DB is:
      - reuse_rate:        fraction of a project's facts/elements already in DB
      - novelty_rate:      new facts + elements created per project (10-iter MA)
      - domain_coverage:   domains with ≥1 fact / 9 total domains
      - category_sat:      categories with ≥3 facts / TARGET_CATEGORIES
      - graph_density:     relationships / TARGET_RELATIONSHIPS
      - convergence_score: weighted composite [0 → 1]

3.  Builds a prompt that gives Copilot the full knowledge map so it can:
      - Reuse existing elements rather than reinventing them
      - Target sparse domains/categories to fill knowledge gaps
      - Correctly place new facts in the relationship graph
      - Avoid semantic duplicates (not just title duplicates)

4.  Calls ``gh copilot -p "..." --allow-all-tools --autopilot`` and parses
    the JSON envelope from stdout.

5.  Saves new facts → data/facts/{domain}/{category}/
    new design elements → data/projects/design-elements/
    new project → data/projects/projects/
    new relationships → data/facts/_relationships.json

6.  Appends an iteration record to data/convergence.jsonl and displays
    the convergence gauge.

7.  Loops (configurable pause) until --count reached or Ctrl-C.

Usage
-----
    factdb seed-copilot                     # run forever
    factdb seed-copilot --count 10          # generate 10 projects
    factdb seed-copilot --dry-run           # preview prompt, no writes
    factdb seed-copilot --model gpt-5.2
    factdb seed-copilot --convergence-only  # show convergence report, exit

    python3 scripts/copilot_seeder.py [same options]

Convergence log
---------------
    data/convergence.jsonl   — one JSON line per iteration (append-only)
    factdb seed-copilot --convergence-only   — print full report and exit
"""

from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
FACTS_DIR = REPO_ROOT / "data" / "facts"
ELEMENTS_DIR = REPO_ROOT / "data" / "projects" / "design-elements"
PROJECTS_DIR = REPO_ROOT / "data" / "projects" / "projects"
RELATIONSHIPS_FILE = FACTS_DIR / "_relationships.json"
QUEUE_FILE = REPO_ROOT / "PROJECT_QUEUE.md"
CONVERGENCE_FILE = REPO_ROOT / "data" / "convergence.jsonl"

# ---------------------------------------------------------------------------
# Domain model constants
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

# Convergence targets — estimated "complete" coverage for hobbyist/maker domain
TARGET_FACTS = 250
TARGET_ELEMENTS = 150
TARGET_PROJECTS = 120
TARGET_RELATIONSHIPS = 220
TARGET_CATEGORIES = 45   # distinct domain/category pairs
NOVELTY_SCALE = 6.0      # new items/project considered "fully novel"
CONVERGENCE_WARN = 0.80  # threshold to emit saturation warning
NOVELTY_MA_WINDOW = 10   # moving-average window for novelty_rate


# ---------------------------------------------------------------------------
# Rich context loader
# ---------------------------------------------------------------------------

@dataclass
class FactSummary:
    title: str
    domain: str
    category: str
    content: str      # first sentence only for prompt compactness
    tags: list[str]


@dataclass
class ElementSummary:
    title: str
    component_category: str
    design_question: str
    key_approach: str   # first sentence of selected_approach


@dataclass
class KnowledgeContext:
    # Grouped fact summaries: domain → category → [FactSummary]
    fact_map: dict[str, dict[str, list[FactSummary]]]
    # Flat sets for dedup
    fact_titles: set[str]
    element_titles: set[str]
    project_titles: set[str]
    # Element capability index: component_category → [ElementSummary]
    element_index: dict[str, list[ElementSummary]]
    # Relationship graph: (source_title, target_title, type)
    relationships: list[tuple[str, str, str]]
    # Coverage stats
    n_facts: int
    n_elements: int
    n_projects: int
    n_relationships: int
    # Domain/category coverage
    domains_covered: set[str]
    category_pairs: set[tuple[str, str]]    # (domain, category) pairs
    sparse_domains: list[str]               # domains with < 3 projects
    sparse_categories: list[tuple[str, str]]  # (domain, cat) pairs with < 3 facts


def _first_sentence(text: str) -> str:
    """Return the first sentence of *text*, truncated to 200 chars."""
    if not text:
        return ""
    for sep in (". ", ".\n", "! ", "? "):
        idx = text.find(sep)
        if 0 < idx < 200:
            return text[: idx + 1].strip()
    return text[:200].strip()


def load_knowledge_context() -> KnowledgeContext:
    """Load the full FactDB state from JSON files into a KnowledgeContext."""
    fact_map: dict[str, dict[str, list[FactSummary]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )
    fact_titles: set[str] = set()

    for path in sorted(FACTS_DIR.rglob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            d = json.loads(path.read_text())
            title = d.get("title", "")
            if not title:
                continue
            domain = d.get("domain", "general")
            category = d.get("category", "misc")
            fact_titles.add(title)
            fact_map[domain][category].append(
                FactSummary(
                    title=title,
                    domain=domain,
                    category=category,
                    content=_first_sentence(d.get("content", "")),
                    tags=d.get("tags", []),
                )
            )
        except Exception:
            pass

    element_index: dict[str, list[ElementSummary]] = collections.defaultdict(list)
    element_titles: set[str] = set()

    for path in sorted(ELEMENTS_DIR.glob("*.json")):
        try:
            d = json.loads(path.read_text())
            title = d.get("title", "")
            if not title:
                continue
            cat = d.get("component_category", "processing")
            element_titles.add(title)
            element_index[cat].append(
                ElementSummary(
                    title=title,
                    component_category=cat,
                    design_question=d.get("design_question", ""),
                    key_approach=_first_sentence(d.get("selected_approach", "")),
                )
            )
        except Exception:
            pass

    project_titles: set[str] = set()
    project_domains: list[str] = []

    for path in sorted(PROJECTS_DIR.glob("*.json")):
        try:
            d = json.loads(path.read_text())
            if t := d.get("title"):
                project_titles.add(t)
            if dom := d.get("domain"):
                project_domains.append(dom)
        except Exception:
            pass

    relationships: list[tuple[str, str, str]] = []
    if RELATIONSHIPS_FILE.exists():
        try:
            for r in json.loads(RELATIONSHIPS_FILE.read_text()):
                s = r.get("source_title", "")
                t = r.get("target_title", "")
                rt = r.get("relationship_type", "depends_on")
                if s and t:
                    relationships.append((s, t, rt))
        except Exception:
            pass

    # Coverage stats
    domains_covered = set(fact_map.keys())
    category_pairs: set[tuple[str, str]] = set()
    sparse_categories: list[tuple[str, str]] = []
    for dom, cats in fact_map.items():
        for cat, facts in cats.items():
            category_pairs.add((dom, cat))
            if len(facts) < 3:
                sparse_categories.append((dom, cat))

    domain_project_count: dict[str, int] = collections.Counter(project_domains)
    sparse_domains = [d for d in VALID_DOMAINS if domain_project_count.get(d, 0) < 3]

    n_facts = sum(
        len(facts) for cats in fact_map.values() for facts in cats.values()
    )

    return KnowledgeContext(
        fact_map=fact_map,
        fact_titles=fact_titles,
        element_titles=element_titles,
        project_titles=project_titles,
        element_index=element_index,
        relationships=relationships,
        n_facts=n_facts,
        n_elements=sum(len(v) for v in element_index.values()),
        n_projects=len(project_titles),
        n_relationships=len(relationships),
        domains_covered=domains_covered,
        category_pairs=category_pairs,
        sparse_domains=sparse_domains,
        sparse_categories=sparse_categories[:12],  # top 12
    )


# ---------------------------------------------------------------------------
# Convergence tracking
# ---------------------------------------------------------------------------

@dataclass
class IterationMetrics:
    timestamp: str
    global_iteration: int
    # DB state before this iteration
    n_facts_before: int
    n_elements_before: int
    n_projects_before: int
    n_relationships_before: int
    # What this iteration produced
    n_new_facts: int
    n_new_elements: int
    n_new_rels: int
    # Reuse tracking
    n_facts_referenced: int       # total facts referenced by new project
    n_elements_referenced: int    # total elements referenced
    n_facts_reused: int           # of those, how many already existed
    n_elements_reused: int
    # Computed scores
    reuse_rate: float             # (reused_f + reused_e) / (ref_f + ref_e), or 0
    novelty_rate: float           # new_facts + new_elements (raw, this iter)
    novelty_rate_ma: float        # 10-iteration moving average
    domain_coverage: float        # domains_covered / 9
    category_saturation: float    # category_pairs_3plus / TARGET_CATEGORIES
    graph_density: float          # relationships / TARGET_RELATIONSHIPS
    convergence_score: float      # composite [0–1]


def _compute_convergence_score(m: IterationMetrics) -> float:
    """Weighted composite score indicating DB saturation [0 = empty, 1 = full]."""
    novelty_decay = max(0.0, 1.0 - m.novelty_rate_ma / NOVELTY_SCALE)
    score = (
        0.35 * m.reuse_rate
        + 0.25 * novelty_decay
        + 0.20 * m.domain_coverage
        + 0.10 * m.category_saturation
        + 0.10 * m.graph_density
    )
    return round(min(1.0, score), 4)


def compute_metrics(
    ctx_before: KnowledgeContext,
    ctx_after: KnowledgeContext,
    project: dict,
    n_new_rels: int,
    novelty_history: list[float],
    global_iteration: int,
) -> IterationMetrics:
    """Compute convergence metrics for one completed iteration."""
    # Facts and elements referenced by the new project
    fact_refs = set(project.get("supporting_fact_titles", []))
    elem_refs = set(project.get("design_element_titles", []))

    facts_reused = len(fact_refs & ctx_before.fact_titles)
    elems_reused = len(elem_refs & ctx_before.element_titles)
    total_refs = len(fact_refs) + len(elem_refs)
    reuse_rate = (facts_reused + elems_reused) / total_refs if total_refs else 0.0

    n_new_facts = ctx_after.n_facts - ctx_before.n_facts
    n_new_elements = ctx_after.n_elements - ctx_before.n_elements
    novelty_rate_raw = float(n_new_facts + n_new_elements)

    # 10-iteration moving average of novelty
    window = novelty_history[-NOVELTY_MA_WINDOW:]
    novelty_ma = sum(window) / len(window) if window else novelty_rate_raw

    # Category saturation: (domain, cat) pairs with ≥3 facts
    cats_3plus = sum(
        1
        for dom, cats in ctx_after.fact_map.items()
        for cat, facts in cats.items()
        if len(facts) >= 3
    )
    cat_sat = min(1.0, cats_3plus / TARGET_CATEGORIES)

    domain_cov = len(ctx_after.domains_covered) / len(VALID_DOMAINS)
    graph_dens = min(1.0, ctx_after.n_relationships / TARGET_RELATIONSHIPS)

    m = IterationMetrics(
        timestamp=datetime.now(timezone.utc).isoformat(),
        global_iteration=global_iteration,
        n_facts_before=ctx_before.n_facts,
        n_elements_before=ctx_before.n_elements,
        n_projects_before=ctx_before.n_projects,
        n_relationships_before=ctx_before.n_relationships,
        n_new_facts=n_new_facts,
        n_new_elements=n_new_elements,
        n_new_rels=n_new_rels,
        n_facts_referenced=len(fact_refs),
        n_elements_referenced=len(elem_refs),
        n_facts_reused=facts_reused,
        n_elements_reused=elems_reused,
        reuse_rate=round(reuse_rate, 4),
        novelty_rate=novelty_rate_raw,
        novelty_rate_ma=round(novelty_ma, 2),
        domain_coverage=round(domain_cov, 4),
        category_saturation=round(cat_sat, 4),
        graph_density=round(graph_dens, 4),
        convergence_score=0.0,  # placeholder, filled below
    )
    m.convergence_score = _compute_convergence_score(m)
    return m


def save_metrics(m: IterationMetrics, dry_run: bool):
    """Append one metrics record to data/convergence.jsonl."""
    if dry_run:
        return
    CONVERGENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONVERGENCE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(m)) + "\n")


def load_convergence_history() -> list[IterationMetrics]:
    """Load all historical metrics from convergence.jsonl."""
    records = []
    if not CONVERGENCE_FILE.exists():
        return records
    for line in CONVERGENCE_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(IterationMetrics(**json.loads(line)))
        except Exception:
            pass
    return records


def load_novelty_history() -> list[float]:
    """Return the raw novelty_rate values from historical convergence records."""
    return [r.novelty_rate for r in load_convergence_history()]


def _gauge(value: float, width: int = 30) -> str:
    """Return a coloured ASCII progress bar for a 0–1 value."""
    filled = int(round(value * width))
    bar = "█" * filled + "░" * (width - filled)
    pct = f"{value * 100:.1f}%"
    if value >= CONVERGENCE_WARN:
        color = "bright_yellow"
    elif value >= 0.5:
        color = "bright_cyan"
    else:
        color = "bright_green"
    return click.style(f"[{bar}] {pct}", fg=color)


def display_convergence(m: IterationMetrics, history: list[IterationMetrics]):
    """Print a compact convergence dashboard to stdout."""
    click.echo("")
    click.echo(click.style("  ┌─── Convergence Dashboard ──────────────────────────────┐", fg="bright_blue"))

    def row(label: str, value: float, width: int = 28):
        click.echo(f"  │  {label:<22}  {_gauge(value, width)}")

    row("Reuse rate",         m.reuse_rate)
    row("Novelty decay",      max(0.0, 1.0 - m.novelty_rate_ma / NOVELTY_SCALE))
    row("Domain coverage",    m.domain_coverage)
    row("Category saturation", m.category_saturation)
    row("Graph density",      m.graph_density)
    click.echo(click.style("  ├────────────────────────────────────────────────────────┤", fg="bright_blue"))
    click.echo(f"  │  {'CONVERGENCE SCORE':<22}  {_gauge(m.convergence_score, 28)}")

    # Trend line (last 5 scores)
    if len(history) >= 2:
        recent = [f"{h.convergence_score:.3f}" for h in history[-5:]]
        click.echo(f"  │  Trend (last {min(5, len(history))}):  {' → '.join(recent)}")

    click.echo(click.style("  └────────────────────────────────────────────────────────┘", fg="bright_blue"))

    if m.convergence_score >= CONVERGENCE_WARN:
        click.echo(
            click.style(
                f"\n  ⚠  Convergence score {m.convergence_score:.1%} ≥ {CONVERGENCE_WARN:.0%} — "
                "DB is approaching domain saturation.\n"
                "  Consider broadening to adjacent domains or increasing detail depth.",
                fg="bright_yellow", bold=True,
            )
        )

    # Stats line
    click.echo(
        click.style(
            f"  Stats: {m.n_facts_before + m.n_new_facts} facts  |  "
            f"{m.n_elements_before + m.n_new_elements} elements  |  "
            f"{m.n_projects_before + (1 if m.n_new_facts >= 0 else 0)} projects  |  "
            f"novelty MA {m.novelty_rate_ma:.1f}/iter",
            dim=True,
        )
    )


def print_convergence_report():
    """Print a full historical convergence report and exit."""
    history = load_convergence_history()
    if not history:
        click.echo("No convergence data yet (data/convergence.jsonl is empty or missing).")
        return

    click.echo(click.style("\n══ FactDB Convergence Report ══\n", fg="bright_blue", bold=True))
    click.echo(
        f"{'Iter':>5}  {'Timestamp':<22}  {'Facts':>5}  {'Elems':>5}  "
        f"{'Projs':>5}  {'Reuse':>6}  {'NovelMA':>7}  {'Score':>6}"
    )
    click.echo("─" * 80)
    for m in history:
        ts = m.timestamp[:19].replace("T", " ")
        click.echo(
            f"{m.global_iteration:>5}  {ts:<22}  "
            f"{m.n_facts_before + m.n_new_facts:>5}  "
            f"{m.n_elements_before + m.n_new_elements:>5}  "
            f"{m.n_projects_before:>5}  "
            f"{m.reuse_rate:>5.1%}  "
            f"{m.novelty_rate_ma:>7.2f}  "
            f"{m.convergence_score:>6.3f}"
        )

    last = history[-1]
    click.echo("─" * 80)
    click.echo(f"\nLatest convergence score: {last.convergence_score:.1%}")
    click.echo(f"Estimated DB completeness: {last.convergence_score * 100:.1f}% of target saturation")

    if last.convergence_score >= CONVERGENCE_WARN:
        click.echo(
            click.style(
                f"\n⚠  Score {last.convergence_score:.1%} ≥ {CONVERGENCE_WARN:.0%}: "
                "consider seeding underrepresented domains.",
                fg="bright_yellow",
            )
        )
    elif last.convergence_score < 0.40:
        click.echo(click.style("\n✅  DB is in early growth phase — plenty of territory to explore.", fg="bright_green"))
    else:
        click.echo(click.style("\n🔵  DB is in mid-stage growth — key domains covered, filling depth.", fg="bright_cyan"))


# ---------------------------------------------------------------------------
# Prompt construction (rich context)
# ---------------------------------------------------------------------------

def _build_knowledge_map(ctx: KnowledgeContext) -> str:
    """
    Build a compact knowledge coverage map for the prompt.

    Groups facts by domain/category, lists elements by capability category,
    shows coverage gaps, and summarises the relationship graph.
    Returns a multi-section string.
    """
    lines: list[str] = []

    # ── Fact coverage map ─────────────────────────────────────────────────
    lines.append("=== EXISTING KNOWLEDGE MAP (facts grouped by domain/category) ===")
    for domain in sorted(ctx.fact_map.keys()):
        cats = ctx.fact_map[domain]
        domain_count = sum(len(v) for v in cats.values())
        lines.append(f"\n[{domain.upper()}]  ({domain_count} facts)")
        for cat in sorted(cats.keys()):
            facts = cats[cat]
            titles = [f.title for f in facts]
            # Compact: show titles on one line, truncated if too many
            if len(titles) <= 6:
                lines.append(f"  {cat} ({len(titles)}): {', '.join(titles)}")
            else:
                shown = ', '.join(titles[:5])
                lines.append(f"  {cat} ({len(titles)}): {shown}, … +{len(titles)-5} more")

    # ── Coverage gaps ────────────────────────────────────────────────────
    uncovered_domains = VALID_DOMAINS - ctx.domains_covered
    lines.append("\n=== COVERAGE GAPS (target these for maximum new knowledge value) ===")
    if uncovered_domains:
        lines.append(f"  Domains with NO facts: {', '.join(sorted(uncovered_domains))}")
    lines.append(f"  Domains with < 3 projects: {', '.join(sorted(ctx.sparse_domains[:6]))}")
    if ctx.sparse_categories:
        sparse_str = ", ".join(f"{d}/{c}" for d, c in ctx.sparse_categories[:8])
        lines.append(f"  Sparse fact categories (< 3 facts): {sparse_str}")

    # ── Element capability index ─────────────────────────────────────────
    lines.append("\n=== REUSABLE DESIGN ELEMENTS (PREFER THESE — only create new ones if genuinely missing) ===")
    for cat in sorted(ctx.element_index.keys()):
        elements = ctx.element_index[cat]
        lines.append(f"\n[{cat}]  ({len(elements)} elements)")
        for el in elements:
            # Show title + key approach fragment
            approach_snippet = el.key_approach[:100] if el.key_approach else ""
            lines.append(f"  • {el.title}")
            if approach_snippet:
                lines.append(f"      → {approach_snippet}")

    # ── Relationship graph (compact) ─────────────────────────────────────
    lines.append("\n=== RELATIONSHIP GRAPH (existing edges — extend these) ===")
    if ctx.relationships:
        for src, tgt, rt in ctx.relationships[:60]:  # cap at 60 for prompt length
            lines.append(f"  {src}  --[{rt}]-->  {tgt}")
        if len(ctx.relationships) > 60:
            lines.append(f"  … and {len(ctx.relationships) - 60} more edges (not shown)")
    else:
        lines.append("  (no relationships yet)")

    return "\n".join(lines)


def build_prompt(ctx: KnowledgeContext) -> str:
    """Build the full Copilot prompt with rich context injection."""
    knowledge_map = _build_knowledge_map(ctx)

    fact_list = "\n".join(f"  - {t}" for t in sorted(ctx.fact_titles))
    element_list = "\n".join(f"  - {t}" for t in sorted(ctx.element_titles))
    project_list = "\n".join(f"  - {t}" for t in sorted(ctx.project_titles))

    # Suggest a focus domain based on sparse coverage
    if ctx.sparse_domains:
        focus_hint = (
            f"PREFERRED FOCUS: Target one of these under-represented domains to maximise "
            f"knowledge coverage: {', '.join(sorted(ctx.sparse_domains[:4]))}"
        )
    else:
        focus_hint = "All domains have reasonable coverage — choose the most novel project angle."

    return f"""You are a senior embedded-systems / mechatronics engineer designing projects for FactDB.

FactDB stores engineering FACTS (laws, sensor specs, algorithms), DESIGN ELEMENTS (reusable hardware/software blocks
justified by facts), and PROJECTS (fully designed systems assembled from elements).

Your task: INVENT ONE NEW, GENUINELY NOVEL PROJECT not already in FactDB.

{focus_hint}

──────────────────────────────────────────────────────────────────────────────────
FULL KNOWLEDGE CONTEXT — Use this to REUSE existing elements and EXTEND existing facts.
Reading this carefully is essential: it shows what's already known so you can build on it.
──────────────────────────────────────────────────────────────────────────────────
{knowledge_map}

──────────────────────────────────────────────────────────────────────────────────
DEDUPLICATION LISTS — Do NOT produce items with these exact titles.
──────────────────────────────────────────────────────────────────────────────────
=== ALL EXISTING FACT TITLES ===
{fact_list}

=== ALL EXISTING DESIGN ELEMENT TITLES ===
{element_list}

=== ALL EXISTING PROJECT TITLES ===
{project_list}

──────────────────────────────────────────────────────────────────────────────────
PROJECT DESIGN RULES
──────────────────────────────────────────────────────────────────────────────────
1. REUSE existing design elements wherever possible — only create new ones if genuinely needed.
2. REFERENCE existing facts in supporting_fact_titles — only add new facts for genuinely novel knowledge.
3. For new facts, ADD relationships to existing facts (depends_on / supports).
4. Domain must be one of: mechanical, electrical, civil, software, chemical, aerospace, materials, systems, general.
5. Must use ≥ 4 design elements (existing or new), include element_interactions, and a complete integration_code sketch.
6. integration_code must be a complete, runnable Arduino C++ or MicroPython program (not pseudocode).

──────────────────────────────────────────────────────────────────────────────────
OUTPUT FORMAT — Respond with ONLY one valid JSON object (no markdown, no prose).
──────────────────────────────────────────────────────────────────────────────────
{{
  "new_facts": [
    {{
      "id": "<UUID v4>",
      "title": "<unique title not in existing list>",
      "domain": "<domain>",
      "category": "<slug>",
      "subcategory": "<slug>",
      "detail_level": "fundamental|intermediate|advanced",
      "content": "<concise 1-3 sentence summary>",
      "extended_content": "<150-300 word detailed explanation with practical notes>",
      "formula": "<formula or null>",
      "units": "<units or null>",
      "source": "<datasheet/textbook/standard>",
      "source_url": null,
      "confidence_score": 0.95,
      "status": "draft",
      "version": 1,
      "tags": ["tag1"],
      "created_by": "copilot-seeder"
    }}
  ],
  "new_relationships": [
    {{
      "source_title": "<existing or new fact title>",
      "target_title": "<existing or new fact title>",
      "relationship_type": "depends_on|supports",
      "weight": 0.9,
      "description": "<one sentence>"
    }}
  ],
  "new_design_elements": [
    {{
      "title": "<unique element title>",
      "component_category": "power|sensing|actuation|control|communication|software|mechanical|processing",
      "design_question": "<engineering question this element answers>",
      "selected_approach": "<specific components + wiring + library>",
      "rationale": "<why this approach, 2-3 sentences>",
      "alternatives": [{{"approach": "...", "reason_rejected": "..."}}],
      "verification_notes": "<fact titles that support this element>",
      "supporting_fact_titles": ["<title>"]
    }}
  ],
  "project": {{
    "title": "<unique project title>",
    "description": "<2-3 sentence overview>",
    "objective": "<measurable goals>",
    "constraints": "<budget, voltage, platform, enclosure>",
    "domain": "<domain>",
    "status": "completed",
    "supporting_fact_titles": ["<existing or new>"],
    "design_element_titles": ["<existing or new>"],
    "element_usage_notes": {{"<ElementTitle>": "<specific configuration in this project>"}},
    "element_interactions": [
      {{"from": "<el>", "to": "<el>", "data": "<signal/protocol>", "description": "<purpose>"}}
    ],
    "integration_code": "<complete sketch as escaped string>"
  }}
}}
"""


# ---------------------------------------------------------------------------
# Copilot invocation
# ---------------------------------------------------------------------------

def call_copilot(prompt: str, model: str, timeout: int = 300) -> str:
    """Invoke ``gh copilot`` non-interactively and return raw stdout."""
    cmd = ["gh", "copilot", "-p", prompt, "--allow-all-tools", "--autopilot"]
    if model:
        cmd += ["--model", model]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT),
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
    """Robustly extract the first complete JSON object from *raw*."""
    stripped = re.sub(r"```(?:json)?\s*", "", raw)
    stripped = re.sub(r"```", "", stripped)
    start = stripped.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Copilot response")
    depth = end = 0
    in_string = escape = False
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
    if not end:
        raise ValueError("Unbalanced JSON braces in Copilot response")
    return json.loads(stripped[start:end])


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:80]


def validate_fact(fact: dict) -> list[str]:
    errors = []
    for field in ("id", "title", "domain", "category", "content"):
        if not fact.get(field):
            errors.append(f"fact missing required field: {field}")
    if fact.get("domain") not in VALID_DOMAINS:
        errors.append(f"fact domain '{fact.get('domain')}' invalid")
    if fact.get("detail_level") not in VALID_DETAIL_LEVELS:
        fact["detail_level"] = "intermediate"
    return errors


def validate_element(el: dict) -> list[str]:
    errors = []
    for field in ("title", "component_category", "selected_approach"):
        if not el.get(field):
            errors.append(f"element missing required field: {field}")
    if el.get("component_category") not in VALID_CATEGORIES:
        errors.append(f"element category '{el.get('component_category')}' invalid")
    return errors


def validate_project(proj: dict) -> list[str]:
    errors = []
    for field in ("title", "description", "domain", "integration_code"):
        if not proj.get(field):
            errors.append(f"project missing required field: {field}")
    if proj.get("domain") not in VALID_DOMAINS:
        errors.append(f"project domain '{proj.get('domain')}' invalid")
    if proj.get("status") not in VALID_STATUSES:
        proj["status"] = "completed"
    return errors


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_fact(fact: dict, dry_run: bool) -> Path:
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
    path = ELEMENTS_DIR / f"{_slug(el['title'])}.json"
    if not dry_run:
        path.write_text(json.dumps(el, indent=2, ensure_ascii=False))
    return path


def save_project(proj: dict, dry_run: bool) -> Path:
    path = PROJECTS_DIR / f"{_slug(proj['title'])}.json"
    if not dry_run:
        path.write_text(json.dumps(proj, indent=2, ensure_ascii=False))
    return path


def append_relationships(new_rels: list[dict], dry_run: bool) -> int:
    existing: list[dict] = []
    if RELATIONSHIPS_FILE.exists():
        existing = json.loads(RELATIONSHIPS_FILE.read_text())
    existing_keys = {(r["source_title"], r["target_title"]) for r in existing}
    added = 0
    for rel in new_rels:
        if rel.get("relationship_type") not in VALID_RELATIONSHIP_TYPES:
            rel["relationship_type"] = "depends_on"
        key = (rel.get("source_title", ""), rel.get("target_title", ""))
        if all(key) and key not in existing_keys:
            existing.append(rel)
            existing_keys.add(key)
            added += 1
    if not dry_run and added:
        RELATIONSHIPS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    return added


def append_queue_entry(title: str, n_facts: int, n_elements: int, score: float, dry_run: bool):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = (
        f"\n- [x] **{title}** — "
        f"{n_facts} new fact(s), {n_elements} new element(s), "
        f"convergence {score:.1%} — auto-seeded {ts} ✓"
    )
    if not dry_run and QUEUE_FILE.exists():
        with QUEUE_FILE.open("a", encoding="utf-8") as f:
            f.write(line)


def reseed_db(verbose: bool):
    for cmd in [
        [sys.executable, "-m", "factdb.cli", "seed"],
        [sys.executable, "-m", "factdb.cli", "seed-projects"],
    ]:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        if verbose:
            click.echo(result.stdout.strip())
        if result.returncode != 0:
            click.echo(click.style(f"  ⚠  seed failed: {result.stderr[:300]}", fg="yellow"))


# ---------------------------------------------------------------------------
# Core iteration
# ---------------------------------------------------------------------------

def run_one_iteration(
    ctx: KnowledgeContext,
    novelty_history: list[float],
    global_iteration: int,
    model: str,
    dry_run: bool,
    verbose: bool,
    timeout: int,
) -> dict[str, Any]:
    """Run one prompt → parse → save cycle.  Returns summary dict."""
    summary: dict[str, Any] = {
        "title": None,
        "n_facts": 0,
        "n_elements": 0,
        "n_relationships": 0,
        "project": {},
        "errors": [],
        "metrics": None,
    }

    prompt = build_prompt(ctx)
    if verbose:
        click.echo(click.style(f"  Prompt length: {len(prompt):,} chars", dim=True))

    if dry_run:
        click.echo(click.style("  [dry-run] Prompt preview (first 800 chars):", fg="cyan"))
        click.echo(prompt[:800] + "\n…")
        return summary

    click.echo(click.style("  Invoking Copilot CLI…", dim=True))
    try:
        raw = call_copilot(prompt, model, timeout)
    except (subprocess.TimeoutExpired, RuntimeError) as exc:
        summary["errors"].append(str(exc))
        return summary

    if verbose:
        click.echo(click.style(f"  Response: {len(raw):,} chars", dim=True))

    try:
        envelope = extract_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        summary["errors"].append(f"JSON parse error: {exc}")
        if verbose:
            click.echo(raw[:2000])
        return summary

    # ── Save new facts ────────────────────────────────────────────────────
    for fact in envelope.get("new_facts", []):
        errs = validate_fact(fact)
        if errs:
            summary["errors"].extend(errs)
            continue
        if fact["title"] in ctx.fact_titles:
            click.echo(click.style(f"    ↳ Fact exists, skipping: {fact['title']}", fg="yellow"))
            continue
        save_fact(fact, dry_run)
        ctx.fact_titles.add(fact["title"])
        summary["n_facts"] += 1
        click.echo(click.style(f"    ✓ Fact: {fact['title']}", fg="green"))

    # ── Save new elements ─────────────────────────────────────────────────
    for el in envelope.get("new_design_elements", []):
        errs = validate_element(el)
        if errs:
            summary["errors"].extend(errs)
            continue
        if el["title"] in ctx.element_titles:
            click.echo(click.style(f"    ↳ Element exists, skipping: {el['title']}", fg="yellow"))
            continue
        save_element(el, dry_run)
        ctx.element_titles.add(el["title"])
        summary["n_elements"] += 1
        click.echo(click.style(f"    ✓ Element: {el['title']}", fg="green"))

    # ── Save project ──────────────────────────────────────────────────────
    proj = envelope.get("project", {})
    errs = validate_project(proj)
    if errs:
        summary["errors"].extend(errs)
    elif proj.get("title") in ctx.project_titles:
        click.echo(click.style(f"    ↳ Project exists, skipping: {proj['title']}", fg="yellow"))
    else:
        save_project(proj, dry_run)
        ctx.project_titles.add(proj["title"])
        summary["title"] = proj["title"]
        summary["project"] = proj
        click.echo(click.style(f"    ✓ Project: {proj['title']}", fg="green"))

    # ── Save relationships ────────────────────────────────────────────────
    summary["n_relationships"] = append_relationships(
        envelope.get("new_relationships", []), dry_run
    )

    # ── Compute convergence metrics ───────────────────────────────────────
    if summary["title"] and not dry_run:
        ctx_after = load_knowledge_context()
        metrics = compute_metrics(
            ctx_before=ctx,
            ctx_after=ctx_after,
            project=proj,
            n_new_rels=summary["n_relationships"],
            novelty_history=novelty_history,
            global_iteration=global_iteration,
        )
        summary["metrics"] = metrics
        save_metrics(metrics, dry_run)
        append_queue_entry(
            summary["title"],
            summary["n_facts"],
            summary["n_elements"],
            metrics.convergence_score,
            dry_run,
        )

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command(name="copilot-seeder")
@click.option("--count", "-n", default=0, show_default=True,
              help="Number of projects to generate (0 = infinite).")
@click.option("--pause", "-p", default=5, show_default=True,
              help="Seconds to wait between iterations.")
@click.option("--model", "-m", default="", show_default=True,
              help="Copilot model override (e.g. gpt-5.2).")
@click.option("--seed-every", default=1, show_default=True,
              help="Re-seed SQLite DB every N successful additions.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview prompt without invoking Copilot or writing files.")
@click.option("--verbose", "-v", is_flag=True, default=False,
              help="Show extra diagnostic output.")
@click.option("--timeout", default=300, show_default=True,
              help="Seconds before a Copilot call is aborted.")
@click.option("--convergence-only", is_flag=True, default=False,
              help="Print historical convergence report and exit.")
def main(count, pause, model, seed_every, dry_run, verbose, timeout, convergence_only):
    """
    Continuously prompt GitHub Copilot CLI to design new FactDB projects.

    Provides Copilot with the FULL knowledge map (facts grouped by domain,
    element capability index, relationship graph, coverage gaps) so it can
    reuse existing building blocks and target knowledge gaps intelligently.

    Tracks convergence metrics per iteration in data/convergence.jsonl.
    Use --convergence-only to print the historical report without seeding.

    Examples::

        factdb seed-copilot                # run forever
        factdb seed-copilot --count 10     # 10 projects then stop
        factdb seed-copilot --dry-run      # preview prompts only
        factdb seed-copilot --convergence-only
    """
    if convergence_only:
        print_convergence_report()
        return

    click.echo(
        click.style(
            "╔══════════════════════════════════════════════════════╗\n"
            "║    FactDB Copilot Seeder  (rich context + convergence)  ║\n"
            "╚══════════════════════════════════════════════════════╝",
            fg="bright_blue", bold=True,
        )
    )
    if dry_run:
        click.echo(click.style("  Mode: DRY RUN — no files will be written.\n", fg="cyan"))

    # Load historical novelty for MA baseline
    novelty_history = load_novelty_history()
    history = load_convergence_history()

    # Global iteration counter (continues from history)
    global_iter_base = max((h.global_iteration for h in history), default=0)

    iteration = 0
    successes = 0
    total_new_facts = 0
    total_new_elements = 0

    try:
        while True:
            iteration += 1
            if count > 0 and iteration > count:
                break

            global_iter = global_iter_base + iteration
            click.echo(
                click.style(
                    f"\n── Iteration {iteration}"
                    + (f" / {count}" if count else "")
                    + f"  (global #{global_iter})  "
                    + f"({datetime.now().strftime('%H:%M:%S')}) ──",
                    fg="bright_cyan", bold=True,
                )
            )

            # Load full context on every iteration to pick up new files
            ctx = load_knowledge_context()
            click.echo(
                click.style(
                    f"  DB: {ctx.n_facts} facts | {ctx.n_elements} elements | "
                    f"{ctx.n_projects} projects | {ctx.n_relationships} rels | "
                    f"{len(ctx.domains_covered)}/{len(VALID_DOMAINS)} domains",
                    dim=True,
                )
            )

            summary = run_one_iteration(
                ctx=ctx,
                novelty_history=novelty_history,
                global_iteration=global_iter,
                model=model,
                dry_run=dry_run,
                verbose=verbose,
                timeout=timeout,
            )

            if summary["errors"]:
                click.echo(
                    click.style(
                        "  Errors:\n" + "\n".join(f"    • {e}" for e in summary["errors"]),
                        fg="red",
                    )
                )

            if summary["title"]:
                successes += 1
                total_new_facts += summary["n_facts"]
                total_new_elements += summary["n_elements"]
                novelty_history.append(float(summary["n_facts"] + summary["n_elements"]))

                m: IterationMetrics | None = summary.get("metrics")
                if m:
                    reuse_pct = f"{m.reuse_rate:.0%}"
                    score_str = f"convergence {m.convergence_score:.3f}"
                else:
                    reuse_pct = "n/a"
                    score_str = ""

                click.echo(
                    click.style(
                        f"  ✔  '{summary['title']}' | "
                        f"+{summary['n_facts']} facts, +{summary['n_elements']} elements, "
                        f"+{summary['n_relationships']} rels | "
                        f"reuse {reuse_pct} | {score_str}",
                        fg="bright_green",
                    )
                )

                if m:
                    history.append(m)
                    display_convergence(m, history)

                if not dry_run and successes % seed_every == 0:
                    click.echo(click.style("  Reseeding SQLite DB…", dim=True))
                    reseed_db(verbose)
            else:
                click.echo(click.style("  ⚠  No project saved this iteration.", fg="yellow"))

            if count == 0 or iteration < count:
                if pause > 0:
                    click.echo(click.style(f"  Pausing {pause}s…", dim=True))
                    time.sleep(pause)

    except KeyboardInterrupt:
        click.echo(click.style("\n\nInterrupted (Ctrl-C).", fg="yellow"))

    # ── Session summary ───────────────────────────────────────────────────
    click.echo(
        click.style(
            f"\n── Session complete ──\n"
            f"  Iterations:        {iteration}\n"
            f"  Projects added:    {successes}\n"
            f"  Facts added:       {total_new_facts}\n"
            f"  Elements added:    {total_new_elements}\n",
            fg="bright_blue",
        )
    )
    if history:
        last = history[-1]
        click.echo(
            click.style(
                f"  Final convergence score: {last.convergence_score:.1%}  "
                f"(reuse {last.reuse_rate:.0%}, "
                f"novelty MA {last.novelty_rate_ma:.1f}/iter)",
                fg="bright_blue",
            )
        )
        click.echo(click.style("\nRun `factdb seed-copilot --convergence-only` to see full report.", dim=True))


if __name__ == "__main__":
    main()
