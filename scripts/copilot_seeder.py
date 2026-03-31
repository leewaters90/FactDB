#!/usr/bin/env python3
"""
copilot_seeder.py — Continuous AI-driven FactDB project seeder with
                     retrieval-first prompting and convergence tracking.

How it works
------------
Each iteration:

1.  Loads the current FactDB knowledge state from JSON files:
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

3.  Generates a compact project intent only:
      - target domain
      - objective / constraints
      - retrieval keywords and likely categories

4.  Retrieves a narrow FactDB context slice from SQLite:
      - relevant facts via keyword + structured search
      - adjacent facts via tags / relationships
      - matching design elements and similar projects

5.  Builds the final generation prompt from that retrieved context, calls
    ``gh copilot -p "..." --allow-all-tools --autopilot``, and parses
    the JSON envelope from stdout.

6.  Saves new facts → data/facts/{domain}/{category}/
    new design elements → data/projects/design-elements/
    new project → data/projects/projects/
    new relationships → data/facts/_relationships.json

7.  Appends an iteration record to data/convergence.jsonl and displays
    the convergence gauge.

8.  Loops (configurable pause) until --count reached or Ctrl-C.

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
import os
import re
import shutil
import subprocess
import sys
import threading
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
MAX_INTENT_SPARSE_CATEGORIES = 8
MAX_INTENT_PROJECT_TITLES = 24
MAX_RETRIEVED_FACTS = 12
MAX_RETRIEVED_ELEMENTS = 8
MAX_RETRIEVED_PROJECTS = 5
MAX_RETRIEVED_RELATIONSHIPS = 16
MAX_RETRIEVAL_TERMS = 8
MAX_RETRIEVAL_CATEGORY_TERMS = 4
STOP_WORDS = {
    "and", "the", "with", "from", "into", "onto", "over", "under",
    "for", "using", "via", "that", "this", "than", "then", "their",
    "your", "have", "will", "would", "should", "about", "system",
    "project", "controller", "monitor", "design", "build",
}


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


@dataclass
class ProjectIntent:
    title_hint: str
    domain: str
    problem_statement: str
    objective: str
    constraints: str
    keywords: list[str]
    fact_queries: list[str]
    fact_categories: list[str]
    element_categories: list[str]


@dataclass
class RetrievedFact:
    id: str
    title: str
    domain: str
    category: str
    detail_level: str
    content: str
    confidence_score: float
    tags: list[str]


@dataclass
class RetrievedElement:
    id: str
    title: str
    component_category: str
    design_question: str
    selected_approach: str
    supporting_fact_titles: list[str]
    used_in_projects: list[str]


@dataclass
class RetrievedProject:
    id: str
    title: str
    domain: str
    description: str
    objective: str
    constraints: str
    supporting_fact_titles: list[str]
    design_element_titles: list[str]


@dataclass
class RetrievedContext:
    intent: ProjectIntent
    facts: list[RetrievedFact]
    elements: list[RetrievedElement]
    projects: list[RetrievedProject]
    relationships: list[tuple[str, str, str]]
    retrieval_terms: list[str]


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
# Prompt construction + retrieval
# ---------------------------------------------------------------------------

def _dedupe_preserve(items: list[str], limit: int | None = None) -> list[str]:
    """Return unique, stripped items preserving order."""
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def _coerce_list(value: Any) -> list[str]:
    """Convert a scalar or list-like field into a flat list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _tokenize(text: str) -> set[str]:
    """Return a compact token set for simple lexical ranking."""
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+-]*", text.lower())
        if len(token) >= 3 and token not in STOP_WORDS
    }


def _score_overlap(*texts: str, keywords: set[str]) -> float:
    """Score a record by keyword overlap with the intent vocabulary."""
    haystack = _tokenize(" ".join(text for text in texts if text))
    return float(len(haystack & keywords))


def _safe_preview(text: str, limit: int = 120) -> str:
    """Collapse whitespace and truncate text for prompt summaries."""
    collapsed = re.sub(r"\s+", " ", text or "").strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "..."


def validate_intent(intent: dict) -> list[str]:
    """Validate and normalise a compact project intent envelope."""
    errors = []
    for field in ("title_hint", "domain", "objective"):
        if not str(intent.get(field, "")).strip():
            errors.append(f"intent missing required field: {field}")

    domain = str(intent.get("domain", "")).strip().lower()
    intent["domain"] = domain
    if domain not in VALID_DOMAINS:
        errors.append(f"intent domain '{intent.get('domain')}' invalid")

    intent["title_hint"] = str(intent.get("title_hint", "")).strip()
    intent["problem_statement"] = str(intent.get("problem_statement", "")).strip()
    intent["objective"] = str(intent.get("objective", "")).strip()
    intent["constraints"] = str(intent.get("constraints", "")).strip()

    keywords = _dedupe_preserve(_coerce_list(intent.get("keywords")), limit=8)
    if not keywords and intent["title_hint"]:
        keywords = _dedupe_preserve(re.findall(r"[A-Za-z0-9+-]+", intent["title_hint"]), limit=6)
    intent["keywords"] = keywords

    fact_queries = _dedupe_preserve(_coerce_list(intent.get("fact_queries")), limit=6)
    if not fact_queries:
        fact_queries = keywords[:4]
    intent["fact_queries"] = fact_queries

    fact_categories = []
    for item in _coerce_list(intent.get("fact_categories")):
        slug = re.sub(r"[^a-z0-9-]", "-", item.lower()).strip("-")
        if slug:
            fact_categories.append(slug)
    intent["fact_categories"] = _dedupe_preserve(fact_categories, limit=MAX_RETRIEVAL_CATEGORY_TERMS)

    element_categories = [
        item.lower().strip()
        for item in _coerce_list(intent.get("element_categories"))
        if item and str(item).lower().strip() in VALID_CATEGORIES
    ]
    if not element_categories:
        element_categories = ["sensing", "control", "processing"]
    intent["element_categories"] = _dedupe_preserve(element_categories, limit=4)
    return errors


def build_intent_prompt(ctx: KnowledgeContext) -> str:
    """Build a compact prompt that only asks Copilot for retrieval intent."""
    uncovered_domains = sorted(VALID_DOMAINS - ctx.domains_covered)
    sparse_categories = ", ".join(
        f"{domain}/{category}" for domain, category in ctx.sparse_categories[:MAX_INTENT_SPARSE_CATEGORIES]
    )
    project_titles = ", ".join(sorted(ctx.project_titles)[:MAX_INTENT_PROJECT_TITLES])
    focus_domains = ", ".join(sorted(ctx.sparse_domains[:4])) or "any domain"

    return f"""You are planning the next FactDB project.

Return ONLY a compact JSON intent that will be used to retrieve relevant FactDB context.
Do NOT emit facts, design elements, relationships, integration code, or explanatory prose.

Current FactDB summary:
- {ctx.n_facts} facts
- {ctx.n_elements} design elements
- {ctx.n_projects} projects
- {ctx.n_relationships} relationships
- Covered domains: {', '.join(sorted(ctx.domains_covered))}
- Domains with sparse project coverage: {', '.join(sorted(ctx.sparse_domains[:6]))}
- Domains with no facts yet: {', '.join(uncovered_domains) if uncovered_domains else 'none'}
- Sparse fact categories: {sparse_categories or 'none listed'}
- Existing project titles sample: {project_titles or 'none'}

Target an under-represented domain when it still allows a credible project idea.
Preferred focus domains right now: {focus_domains}

Respond with ONLY this JSON shape:
{{
  "title_hint": "<distinct project title idea>",
  "domain": "mechanical|electrical|civil|software|chemical|aerospace|materials|systems|general",
  "problem_statement": "<one sentence problem framing>",
  "objective": "<measurable outcome>",
  "constraints": "<budget, voltage, environment, platform>",
  "keywords": ["4-8 short retrieval keywords"],
  "fact_queries": ["3-6 search queries for relevant facts"],
  "fact_categories": ["0-4 likely fact categories"],
  "element_categories": ["2-4 of power|sensing|actuation|control|communication|software|mechanical|processing"]
}}
"""


def _build_intent(intent: dict) -> ProjectIntent:
    """Convert a normalised dict into a ProjectIntent dataclass."""
    return ProjectIntent(
        title_hint=intent["title_hint"],
        domain=intent["domain"],
        problem_statement=intent["problem_statement"],
        objective=intent["objective"],
        constraints=intent["constraints"],
        keywords=intent["keywords"],
        fact_queries=intent["fact_queries"],
        fact_categories=intent["fact_categories"],
        element_categories=intent["element_categories"],
    )


def build_local_intent(ctx: KnowledgeContext) -> ProjectIntent:
    """Build a deterministic project intent from current coverage gaps."""
    if ctx.sparse_domains:
        domain = sorted(ctx.sparse_domains)[0]
    else:
        domain = sorted(VALID_DOMAINS)[0]

    domain_categories = sorted(
        cat for dom, cat in ctx.sparse_categories if dom == domain
    )
    if not domain_categories:
        domain_categories = sorted(
            cat for dom, cat in ctx.category_pairs if dom == domain
        )
    picked_categories = domain_categories[:2]

    keywords = [domain] + picked_categories + [
        "embedded",
        "control",
        "telemetry",
        "safety",
    ]
    fact_queries = [
        f"{domain} {cat}" for cat in picked_categories[:2]
    ] + [
        f"{domain} system design",
        f"{domain} sensing control",
    ]

    category_to_elements = {
        "power": ["power"],
        "battery-management": ["power", "sensing"],
        "communication": ["communication", "processing"],
        "control-systems": ["control", "processing"],
        "embedded-systems": ["processing", "software"],
        "position-sensing": ["sensing", "control"],
        "sensors": ["sensing", "processing"],
        "signal-processing": ["processing", "software"],
        "telemetry": ["communication", "processing"],
    }
    element_categories: list[str] = []
    for cat in picked_categories:
        element_categories.extend(category_to_elements.get(cat, []))
    if not element_categories:
        element_categories = ["sensing", "control", "processing"]

    title_tokens = [token.replace("-", " ").title() for token in [domain] + picked_categories[:1]]
    title_hint = " ".join(title_tokens + ["Adaptive Controller"]).strip()

    return ProjectIntent(
        title_hint=title_hint,
        domain=domain,
        problem_statement=f"Design a novel {domain} project that strengthens sparse FactDB coverage.",
        objective="Deliver measurable closed-loop behavior with logging and fault handling.",
        constraints="Low-cost MCU platform, realistic BOM, explicit safety constraints.",
        keywords=_dedupe_preserve(keywords, limit=8),
        fact_queries=_dedupe_preserve(fact_queries, limit=6),
        fact_categories=_dedupe_preserve(picked_categories, limit=MAX_RETRIEVAL_CATEGORY_TERMS),
        element_categories=_dedupe_preserve(element_categories, limit=4),
    )


def generate_project_intent(
    ctx: KnowledgeContext,
    model: str,
    timeout: int,
    verbose: bool = False,
) -> tuple[ProjectIntent | None, str, str | None]:
    """Generate a compact project intent and return the prompt and any error.

    Default behavior is local deterministic intent generation to avoid
    additional Copilot round-trips and timeout risk on Windows terminals.
    Set FACTDB_INTENT_WITH_COPILOT=1 to use model-driven intent generation.
    """
    prompt = build_intent_prompt(ctx)
    if os.environ.get("FACTDB_INTENT_WITH_COPILOT", "0") not in {"1", "true", "TRUE"}:
        return build_local_intent(ctx), prompt, None

    intent_timeout = max(timeout, 240)
    try:
        raw = call_copilot(prompt, model, intent_timeout, verbose=verbose)
        intent_dict = extract_json(raw)
    except (subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return None, prompt, str(exc)

    errors = validate_intent(intent_dict)
    if errors:
        return None, prompt, "; ".join(errors)
    return _build_intent(intent_dict), prompt, None


def _enum_or_none(enum_cls, value: str | None):
    """Return an Enum member for *value* or None if parsing fails."""
    if not value:
        return None
    try:
        return enum_cls(value)
    except Exception:
        return None


def retrieve_factdb_context(intent: ProjectIntent, session: Any | None = None) -> RetrievedContext:
    """Retrieve a compact FactDB slice for the generated project intent."""
    from factdb.database import get_session_factory, init_db
    from factdb.models import DetailLevel, FactStatus
    from factdb.project_models import ComponentCategory
    from factdb.project_repository import ProjectRepository
    from factdb.repository import FactRepository
    from factdb.search import FactSearch

    own_session = session is None
    if own_session:
        init_db()
        session = get_session_factory()()

    try:
        searcher = FactSearch(session)
        fact_repo = FactRepository(session)
        project_repo = ProjectRepository(session)

        from factdb.models import EngineeringDomain  # local import keeps module startup cheap
        domain_enum = _enum_or_none(EngineeringDomain, intent.domain)

        retrieval_terms = _dedupe_preserve(
            intent.fact_queries + intent.keywords + [intent.title_hint, intent.problem_statement, intent.objective],
            limit=MAX_RETRIEVAL_TERMS,
        )
        keyword_tokens = _tokenize(" ".join(retrieval_terms + intent.fact_categories + intent.element_categories))

        fact_scores: dict[str, dict[str, Any]] = {}

        def add_fact(fact: Any, score: float):
            if fact is None or not getattr(fact, "is_active", True):
                return
            bucket = fact_scores.setdefault(fact.id, {"fact": fact, "score": 0.0})
            bucket["score"] += score + float(getattr(fact, "confidence_score", 0.0) or 0.0)

        for query_index, query in enumerate(retrieval_terms):
            scoped = searcher.search(
                query=query,
                domain=domain_enum,
                status=FactStatus.VERIFIED,
                limit=5,
            )
            fallback = []
            if not scoped and domain_enum is not None:
                fallback = searcher.search(query=query, status=FactStatus.VERIFIED, limit=3)
            for rank, fact in enumerate(scoped or fallback):
                add_fact(fact, max(0.75, 5.0 - rank - (query_index * 0.25)))

        for category in intent.fact_categories[:MAX_RETRIEVAL_CATEGORY_TERMS]:
            for rank, fact in enumerate(
                searcher.search(
                    domain=domain_enum,
                    category=category,
                    status=FactStatus.VERIFIED,
                    limit=4,
                )
            ):
                add_fact(fact, 2.0 - (rank * 0.2))

        if domain_enum is not None:
            for fact in searcher.get_by_domain_and_level(domain_enum, DetailLevel.INTERMEDIATE)[:4]:
                add_fact(fact, 1.25)

        ranked_seed_facts = sorted(
            fact_scores.values(),
            key=lambda item: (-item["score"], item["fact"].title),
        )[:6]
        for seed in ranked_seed_facts:
            fact = seed["fact"]
            for rank, related in enumerate(searcher.suggest_related_by_tags(fact.id, limit=2)):
                add_fact(related, 1.5 - (rank * 0.2))
            for rel, target in fact_repo.get_related_facts(fact.id):
                bonus = 1.2 if rel.relationship_type in VALID_RELATIONSHIP_TYPES else 0.8
                add_fact(target, bonus)

        ranked_facts = sorted(
            fact_scores.values(),
            key=lambda item: (-item["score"], -float(item["fact"].confidence_score or 0.0), item["fact"].title),
        )[:MAX_RETRIEVED_FACTS]
        selected_fact_ids = {item["fact"].id for item in ranked_facts}

        relationships: list[tuple[str, str, str]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for item in ranked_facts[:8]:
            source = item["fact"]
            for rel, target in fact_repo.get_related_facts(source.id):
                edge = (source.title, target.title, rel.relationship_type)
                if target.id not in selected_fact_ids or edge in seen_edges:
                    continue
                seen_edges.add(edge)
                relationships.append(edge)
                if len(relationships) >= MAX_RETRIEVED_RELATIONSHIPS:
                    break
            if len(relationships) >= MAX_RETRIEVED_RELATIONSHIPS:
                break

        element_scores: dict[str, dict[str, Any]] = {}

        def add_element(element: Any, score: float):
            bucket = element_scores.setdefault(element.id, {"element": element, "score": 0.0})
            bucket["score"] += score

        for category in intent.element_categories[:4]:
            category_enum = _enum_or_none(ComponentCategory, category)
            if category_enum is None:
                continue
            for element in project_repo.list_design_elements(component_category=category_enum, limit=150):
                score = 2.5 + _score_overlap(
                    element.title,
                    element.design_question or "",
                    element.selected_approach or "",
                    keywords=keyword_tokens,
                )
                add_element(element, score)

        for element in project_repo.list_design_elements(limit=250):
            overlap = _score_overlap(
                element.title,
                element.design_question or "",
                element.selected_approach or "",
                keywords=keyword_tokens,
            )
            if overlap > 0:
                add_element(element, overlap)

        ranked_elements = sorted(
            element_scores.values(),
            key=lambda item: (-item["score"], item["element"].title),
        )[:MAX_RETRIEVED_ELEMENTS]

        project_scores: dict[str, dict[str, Any]] = {}

        def add_project(project: Any, score: float):
            bucket = project_scores.setdefault(project.id, {"project": project, "score": 0.0})
            bucket["score"] += score

        scoped_projects = list(project_repo.list_projects(domain=intent.domain, limit=80))
        fallback_projects = []
        if not scoped_projects:
            fallback_projects = list(project_repo.list_projects(limit=120))
        for project in scoped_projects or fallback_projects:
            score = _score_overlap(
                project.title,
                project.description or "",
                project.objective or "",
                project.constraints or "",
                " ".join(fact.title for fact in project.supporting_facts),
                " ".join(link.element.title for link in project.element_links),
                keywords=keyword_tokens,
            )
            if score > 0 or project.domain == intent.domain:
                add_project(project, score + (1.0 if project.domain == intent.domain else 0.0))

        ranked_projects = sorted(
            project_scores.values(),
            key=lambda item: (-item["score"], item["project"].title),
        )[:MAX_RETRIEVED_PROJECTS]

        facts = [
            RetrievedFact(
                id=item["fact"].id,
                title=item["fact"].title,
                domain=getattr(item["fact"].domain, "value", item["fact"].domain),
                category=item["fact"].category or "misc",
                detail_level=getattr(item["fact"].detail_level, "value", item["fact"].detail_level),
                content=_safe_preview(item["fact"].content or item["fact"].extended_content or "", 180),
                confidence_score=float(item["fact"].confidence_score or 0.0),
                tags=[tag.name for tag in item["fact"].tags[:5]],
            )
            for item in ranked_facts
        ]
        elements = [
            RetrievedElement(
                id=item["element"].id,
                title=item["element"].title,
                component_category=getattr(item["element"].component_category, "value", item["element"].component_category),
                design_question=_safe_preview(item["element"].design_question or "", 120),
                selected_approach=_safe_preview(item["element"].selected_approach or "", 160),
                supporting_fact_titles=[fact.title for fact in item["element"].supporting_facts[:4]],
                used_in_projects=[link.project.title for link in item["element"].project_links[:4]],
            )
            for item in ranked_elements
        ]
        projects = [
            RetrievedProject(
                id=item["project"].id,
                title=item["project"].title,
                domain=getattr(item["project"].domain, "value", item["project"].domain),
                description=_safe_preview(item["project"].description or "", 180),
                objective=_safe_preview(item["project"].objective or "", 140),
                constraints=_safe_preview(item["project"].constraints or "", 120),
                supporting_fact_titles=[fact.title for fact in item["project"].supporting_facts[:5]],
                design_element_titles=[link.element.title for link in item["project"].element_links[:5]],
            )
            for item in ranked_projects
        ]
        return RetrievedContext(
            intent=intent,
            facts=facts,
            elements=elements,
            projects=projects,
            relationships=relationships,
            retrieval_terms=retrieval_terms,
        )
    finally:
        if own_session and session is not None:
            session.close()


def _format_retrieved_context(retrieved: RetrievedContext) -> str:
    """Render the retrieved FactDB slice into a compact prompt block."""
    lines = [
        "=== PROJECT INTENT ===",
        f"Title hint: {retrieved.intent.title_hint}",
        f"Domain: {retrieved.intent.domain}",
        f"Problem: {retrieved.intent.problem_statement}",
        f"Objective: {retrieved.intent.objective}",
        f"Constraints: {retrieved.intent.constraints}",
        f"Retrieval terms: {', '.join(retrieved.retrieval_terms)}",
        "",
        "=== RETRIEVED FACTS (reuse these first) ===",
    ]

    if retrieved.facts:
        for fact in retrieved.facts:
            tag_suffix = f" | tags: {', '.join(fact.tags)}" if fact.tags else ""
            lines.append(
                f"- {fact.title} [{fact.domain}/{fact.category}, {fact.detail_level}, conf {fact.confidence_score:.2f}]"
            )
            lines.append(f"  {fact.content}{tag_suffix}")
    else:
        lines.append("- No matching facts found")

    lines.append("\n=== RETRIEVED DESIGN ELEMENTS (prefer reuse) ===")
    if retrieved.elements:
        for element in retrieved.elements:
            lines.append(f"- {element.title} [{element.component_category}]")
            if element.design_question:
                lines.append(f"  question: {element.design_question}")
            if element.selected_approach:
                lines.append(f"  approach: {element.selected_approach}")
            if element.supporting_fact_titles:
                lines.append(f"  supported by: {', '.join(element.supporting_fact_titles)}")
            if element.used_in_projects:
                lines.append(f"  used in: {', '.join(element.used_in_projects)}")
    else:
        lines.append("- No matching design elements found")

    lines.append("\n=== SIMILAR EXISTING PROJECTS (differentiate from these) ===")
    if retrieved.projects:
        for project in retrieved.projects:
            lines.append(f"- {project.title} [{project.domain}]")
            lines.append(f"  {project.description}")
            if project.objective:
                lines.append(f"  objective: {project.objective}")
            if project.design_element_titles:
                lines.append(f"  elements: {', '.join(project.design_element_titles)}")
            if project.supporting_fact_titles:
                lines.append(f"  facts: {', '.join(project.supporting_fact_titles)}")
    else:
        lines.append("- No close project matches found")

    lines.append("\n=== RELATIONSHIPS AMONG RETRIEVED FACTS ===")
    if retrieved.relationships:
        for source, target, rel_type in retrieved.relationships:
            lines.append(f"- {source} --[{rel_type}]--> {target}")
    else:
        lines.append("- No direct retrieved relationships found")
    return "\n".join(lines)


def build_generation_prompt(retrieved: RetrievedContext) -> str:
    """Build the final project-generation prompt from the retrieved context."""
    retrieved_block = _format_retrieved_context(retrieved)
    return f"""You are a senior embedded-systems / mechatronics engineer designing projects for FactDB.

You already have a compact project intent plus a retrieved FactDB context slice.
Use the retrieved facts and design elements first. Only create new facts or elements when the retrieved context does not cover a necessary concept.

Differentiate the new project from the similar existing projects shown below.
For new facts, connect them to retrieved facts using depends_on or supports relationships.

{retrieved_block}

PROJECT DESIGN RULES
1. Reuse retrieved design elements wherever possible.
2. Prefer retrieved facts in supporting_fact_titles.
3. Domain must be one of: mechanical, electrical, civil, software, chemical, aerospace, materials, systems, general.
4. Must use at least 4 design elements, include element_interactions, and provide complete integration_code.
5. integration_code must be runnable Arduino C++ or MicroPython, not pseudocode.
6. Keep the project distinct from the similar existing projects listed above.

Respond with ONLY one valid JSON object (no markdown, no prose):
{{
  "new_facts": [
    {{
      "id": "<UUID v4>",
      "title": "<unique title>",
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

def find_gh_executable() -> str:
    """Return a usable GitHub CLI executable path or raise a clear error."""
    gh_path = shutil.which("gh")
    if gh_path:
        return gh_path

    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "")) / "GitHub CLI" / "gh.exe",
            Path(os.environ.get("LocalAppData", "")) / "Programs" / "GitHub CLI" / "gh.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

    raise FileNotFoundError(
        "GitHub CLI executable 'gh' was not found. Install GitHub CLI or add it to PATH."
    )


def find_copilot_executable() -> str | None:
    """Return a usable standalone Copilot CLI path, or None if unavailable."""
    copilot_path = shutil.which("copilot")
    if copilot_path:
        lower = copilot_path.lower()
        # Ignore VS Code's bootstrap shim; it prompts interactively to install.
        if "github.copilot-chat" not in lower and not lower.endswith("copilot.bat"):
            return copilot_path

    if os.name == "nt":
        # Check a known WinGet install location first to avoid shell shims.
        winget_path = (
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Microsoft"
            / "WinGet"
            / "Packages"
            / "GitHub.Copilot_Microsoft.Winget.Source_8wekyb3d8bbwe"
            / "copilot.exe"
        )
        if winget_path.is_file():
            return str(winget_path)

    if copilot_path:
        return copilot_path

    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", "")) / "GitHub Copilot" / "copilot.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def get_gh_auth_token() -> str | None:
    """Return GitHub CLI auth token if available."""
    try:
        result = subprocess.run(
            [find_gh_executable(), "auth", "token"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            cwd=str(REPO_ROOT),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    token = (result.stdout or "").strip()
    return token or None

def _extract_preamble(text: str) -> str:
    """Return the text that appears before the first JSON object in *text*.

    This captures any reasoning, status, or explanation the model emits
    before the JSON envelope begins.
    """
    # Strip markdown fences first (same as extract_json does)
    stripped = re.sub(r"```(?:json)?\s*", "", text)
    stripped = re.sub(r"```", "", stripped)
    start = stripped.find("{")
    if start <= 0:
        return ""
    return stripped[:start].strip()


def call_copilot(prompt: str, model: str, timeout: int = 300, verbose: bool = False) -> str:
    """Invoke Copilot CLI non-interactively and return raw stdout.

    Verbose mode (``--verbose`` / ``-v``):
    - Logs the executable and model being used.
    - Streams **stderr** live (Copilot CLI status/progress lines).
    - Streams **stdout** live so any reasoning or preamble text the model
      emits before the JSON block is visible in real time.
    - Prints elapsed time every 5 s.

    Quiet mode (default):
    - Prints an elapsed-time ticker every 15 s so the terminal is never
      completely silent during a long Copilot call.
    - After the response arrives, prints a one-line summary of any
      reasoning preamble the model included before the JSON block.
    """
    copilot_exe = find_copilot_executable()
    if copilot_exe:
        cmd = [copilot_exe, "-p", prompt, "--allow-all", "--no-ask-user", "--autopilot"]
    else:
        cmd = [find_gh_executable(), "copilot", "-p", prompt, "--allow-all", "--no-ask-user", "--autopilot"]
    if model:
        cmd += ["--model", model]

    env = os.environ.copy()
    token = get_gh_auth_token()
    if token:
        env.setdefault("GH_TOKEN", token)
        env.setdefault("GITHUB_TOKEN", token)
        env.setdefault("COPILOT_GITHUB_TOKEN", token)

    if verbose:
        exe_name = os.path.basename(cmd[0])
        model_hint = f" --model {model}" if model else ""
        click.echo(click.style(
            f"  ▶ Invoking: {exe_name}{model_hint}  (timeout {timeout}s)",
            fg="bright_blue",
        ))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT),
        env=env,
    )

    # ── Background thread: stream stderr live ─────────────────────────────
    stderr_lines: list[str] = []

    def _stream_stderr():
        assert proc.stderr is not None
        for raw_line in proc.stderr:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            stderr_lines.append(line)
            if line:
                # Always show stderr: the CLI writes its own status here
                # (e.g. "Connecting…", "Using model…"). In non-verbose mode
                # show it dimmed; in verbose mode show it labelled.
                if verbose:
                    click.echo(click.style(f"    copilot> {line}", dim=True))
                else:
                    click.echo(click.style(f"  {line}", dim=True))

    # ── Background thread: stream stdout, display preamble lines live ──────
    stdout_chunks: list[bytes] = []
    # Track whether we have seen the start of the JSON block yet
    _json_started = threading.Event()

    def _stream_stdout():
        assert proc.stdout is not None
        buf = b""
        for chunk in iter(lambda: proc.stdout.read(256), b""):
            stdout_chunks.append(chunk)
            if not _json_started.is_set():
                buf += chunk
                text_so_far = buf.decode("utf-8", errors="replace")
                # Flush complete lines that appear before the JSON block
                while "\n" in text_so_far:
                    line, text_so_far = text_so_far.split("\n", 1)
                    stripped_line = line.strip()
                    if stripped_line.startswith("{"):
                        _json_started.set()
                        break
                    if stripped_line:
                        # Always show reasoning text — this is the model thinking
                        click.echo(click.style(f"  💬 {line}", fg="bright_white"))
                buf = text_so_far.encode("utf-8")

    stderr_thread = threading.Thread(target=_stream_stderr, daemon=True)
    stdout_thread = threading.Thread(target=_stream_stdout, daemon=True)
    stderr_thread.start()
    stdout_thread.start()

    # ── Main thread: elapsed-time ticker (works in both verbose and quiet) ─
    start = time.monotonic()
    deadline = start + timeout
    tick_interval = 5 if verbose else 15

    timed_out = False
    POLL_INTERVAL = 0.25
    next_tick = start + tick_interval
    try:
        while True:
            retcode = proc.poll()
            now = time.monotonic()
            if retcode is not None:
                break
            if now >= deadline:
                proc.kill()
                timed_out = True
                break
            if now >= next_tick:
                elapsed = int(now - start)
                click.echo(click.style(
                    f"  ⏳ Waiting for Copilot… {elapsed}s elapsed",
                    dim=True,
                ))
                next_tick += tick_interval
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        proc.kill()
        raise

    elapsed_total = int(time.monotonic() - start)
    stderr_thread.join(timeout=5)
    stdout_thread.join(timeout=5)

    if timed_out:
        raise subprocess.TimeoutExpired(cmd, timeout)

    # Drain any remaining stdout not yet read by the thread
    assert proc.stdout is not None
    stdout_chunks.append(proc.stdout.read())
    stdout_text = b"".join(stdout_chunks).decode("utf-8", errors="replace")
    stderr_text = "\n".join(stderr_lines)

    if verbose:
        click.echo(click.style(
            f"  ✓ Copilot responded in {elapsed_total}s — "
            f"{len(stdout_text):,} chars stdout",
            dim=True,
        ))
    else:
        click.echo(click.style(f"  ✓ Copilot responded in {elapsed_total}s", dim=True))

    if proc.returncode != 0:
        raise RuntimeError(
            f"copilot invocation exited {proc.returncode}:\n{stderr_text[:1000]}"
        )
    return stdout_text


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

    intent_prompt = build_intent_prompt(ctx)
    if verbose:
        click.echo(click.style(f"  Intent prompt length: {len(intent_prompt):,} chars", dim=True))

    if dry_run:
        click.echo(click.style("  [dry-run] Intent prompt preview (first 800 chars):", fg="cyan"))
        click.echo(intent_prompt[:800] + "\n…")
        click.echo(click.style("  [dry-run] Retrieval and final generation occur after live intent generation.", fg="cyan"))
        return summary

    click.echo(click.style("  Generating project intent…", dim=True))
    intent, _intent_prompt, intent_error = generate_project_intent(ctx, model, timeout, verbose=verbose)
    if intent_error:
        summary["errors"].append(f"intent generation failed: {intent_error}")
        return summary
    if intent is None:
        summary["errors"].append("intent generation returned no intent")
        return summary

    click.echo(
        click.style(
            f"  Intent: {intent.title_hint} | domain {intent.domain} | keywords {', '.join(intent.keywords[:5])}",
            dim=True,
        )
    )

    click.echo(click.style("  Retrieving relevant FactDB context…", dim=True))
    retrieved = retrieve_factdb_context(intent)
    prompt = build_generation_prompt(retrieved)
    if verbose:
        click.echo(
            click.style(
                f"  Retrieved {len(retrieved.facts)} facts, {len(retrieved.elements)} elements, "
                f"{len(retrieved.projects)} projects, {len(retrieved.relationships)} relationships",
                dim=True,
            )
        )
        click.echo(click.style(f"  Final prompt length: {len(prompt):,} chars", dim=True))

    click.echo(click.style("  Generating project from retrieved context…", dim=True))
    try:
        raw = call_copilot(prompt, model, timeout, verbose=verbose)
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

    Uses a two-stage workflow: generate a compact project intent first, then
    retrieve only the relevant FactDB facts, elements, projects, and graph
    edges before asking Copilot for the full project envelope.

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
            "║   FactDB Copilot Seeder  (retrieval + convergence)   ║\n"
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
    completed_iterations = 0
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
            completed_iterations += 1

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
            f"  Iterations:        {completed_iterations}\n"
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
