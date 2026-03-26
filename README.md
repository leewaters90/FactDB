# FactDB

A structured, searchable database of engineering facts — designed to bolster
small AI models' ability to plan and execute complex engineering tasks through
a built-in reasoning architecture.

## Overview

FactDB organises engineering knowledge into **discrete, verifiable facts** with:

* **Layered detail** — facts carry a `detail_level` (`fundamental` → `expert`),
  allowing an AI planner to retrieve the appropriate depth for its context window.
* **Rich classification** — domain → category → subcategory taxonomy.
* **Verification workflow** — DRAFT → PENDING_REVIEW → VERIFIED lifecycle
  with full audit trail.
* **Change management** — every edit creates a version snapshot; the complete
  history is retained.
* **Fact relationships** — a directed graph connecting facts via semantic edges
  (`depends_on`, `supports`, `derived_from`, `contradicts`, `prerequisite`,
  `example_of`, `generalises`).
* **Reasoning engine** — backward chaining (prerequisite collection), forward
  chaining (consequence derivation), conflict detection, decision tree
  construction, and expert-system rule evaluation.

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt
pip install -e .

# 2. Initialise the database
factdb init-db

# 3. Load curated engineering facts
factdb seed

# 4. Load project and design-element data
factdb seed-projects

# 5. Launch the web UI
factdb web
# → open http://127.0.0.1:5000/ in your browser

# 6. Search (CLI)
factdb search "entropy"
factdb search --domain electrical --level fundamental
factdb search --tag thermodynamics

# 7. Browse (CLI)
factdb list --domain mechanical
factdb show <fact-id>

# 8. Explore relationships and prerequisites
factdb related <fact-id>
factdb prereqs <fact-id>

# 9. Export for AI ingestion
factdb export --domain mechanical --output mechanical_facts.json

# 10. Verification workflow
factdb verify <fact-id> --action submit --by alice
factdb verify <fact-id> --action approve --by bob --notes "Verified against reference"
```

The database path defaults to `data/factdb.sqlite`. Override via the
`FACTDB_DATABASE_URL` environment variable (any SQLAlchemy connection string):

```bash
export FACTDB_DATABASE_URL="sqlite:////path/to/custom.sqlite"
```

---

## Data Model

```
EngineeringDomain
└── Fact
    ├── title, content, extended_content   # layered detail
    ├── formula, units                     # engineering precision
    ├── domain, category, subcategory      # taxonomy
    ├── detail_level                       # fundamental / intermediate / advanced / expert
    ├── confidence_score                   # 0.0-1.0
    ├── status                             # draft / pending_review / verified / deprecated
    ├── version                            # current version number
    ├── Tags  (many-to-many)
    ├── FactVersions  (immutable audit snapshots)
    ├── FactVerifications  (verification events)
    └── FactRelationships  (outgoing directed graph edges)
```

### Engineering Domains

| Value | Description |
|-------|-------------|
| `mechanical` | Thermodynamics, mechanics of materials, dynamics |
| `electrical` | Circuit theory, electronics, power systems |
| `civil` | Structural, geotechnical, transportation |
| `software` | Algorithms, architecture, systems |
| `chemical` | Thermodynamics, reaction engineering, transport |
| `aerospace` | Propulsion, aerodynamics, orbital mechanics |
| `materials` | Selection, properties, failure analysis |
| `systems` | Control theory, signal processing, reliability |
| `general` | Cross-domain fundamentals |

### Relationship Types

| Type | Semantics |
|------|-----------|
| `depends_on` | Source *requires* target to be true/applicable |
| `supports` | Source provides evidence for target |
| `contradicts` | Source and target cannot both be true |
| `derived_from` | Source is derived/calculated from target |
| `prerequisite` | Target must be understood before source |
| `example_of` | Source is a concrete example of target |
| `generalises` | Source is a generalisation of target |

---

## Verification and Change Management

```
DRAFT --> PENDING_REVIEW --> VERIFIED
               |
               v
            DRAFT  (rejected or revision requested)
```

Each transition is recorded as a `FactVerification` row.  Every edit to a fact
generates a `FactVersion` snapshot so nothing is ever lost.

```python
from factdb import init_db, FactRepository, VerificationWorkflow
from factdb.database import get_session_factory

init_db()
session = get_session_factory()()

repo = FactRepository(session)
wf   = VerificationWorkflow(session)

fact = repo.create(
    title="Fourier's Law of Heat Conduction",
    content="q = -k gradient(T)",
    domain="mechanical",
    category="heat transfer",
    detail_level="intermediate",
    formula="q = -k * dT/dx",
    units="W/m^2",
    source="Incropera, Fundamentals of Heat and Mass Transfer",
    tags=["heat-transfer", "conduction", "thermodynamics"],
    created_by="engineer@example.com",
)
session.commit()

wf.submit_for_review(fact.id, submitted_by="engineer@example.com")
wf.approve(fact.id, verified_by="lead@example.com", notes="Correct and well-sourced")
session.commit()
```

---

## Reasoning Engine

### Backward Chaining — Collect Prerequisites

```python
from factdb import ReasoningEngine

engine = ReasoningEngine(session)
result = engine.collect_prerequisites(carnot_fact_id)

print(result.summary())
# Goal: Carnot Efficiency
#   Depth      : 1
#   Chain      : Carnot Efficiency -> First Law of Thermodynamics
#   Achievable : yes
```

### Forward Chaining — Derive Consequences

```python
derived = engine.derive_consequences([first_law_id, second_law_id])
for fact in derived:
    print(fact.title)
```

### Expert System — Rule Applicability

```python
result = engine.evaluate_applicability(
    fact_id=carnot_id,
    context_fact_ids=[first_law_id, second_law_id]
)
print(result["applicable"])   # True / False
print(result["reason"])       # human-readable explanation
```

### Decision Tree

```python
tree = engine.build_decision_tree(root_fact_id, max_depth=4)
print(tree.as_dict())         # JSON-serialisable nested structure
```

### Conflict Detection

```python
conflicts = engine.detect_conflicts([fact_a_id, fact_b_id, fact_c_id])
for a, b in conflicts:
    print(f"CONFLICT: {a.title!r} vs {b.title!r}")
```

---

## Search API

```python
from factdb import FactSearch, EngineeringDomain, DetailLevel, FactStatus

search = FactSearch(session)

# Keyword search (title + content + extended_content)
results = search.search(query="heat transfer")

# Structured filters
results = search.search(
    domain=EngineeringDomain.MECHANICAL,
    detail_level=DetailLevel.FUNDAMENTAL,
    status=FactStatus.VERIFIED,
    min_confidence=0.9,
)

# Tag-based search
results = search.search(tags=["thermodynamics", "efficiency"])

# Tag-similarity suggestions
related = search.suggest_related_by_tags(fact_id)
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `factdb init-db` | Create database schema |
| `factdb seed` | Load curated engineering facts |
| `factdb seed-projects` | Load sample projects and design elements |
| `factdb list` | List facts with optional filters |
| `factdb search [QUERY]` | Full-text + structured search |
| `factdb show FACT_ID` | Full detail view of one fact |
| `factdb add` | Interactively add a new fact |
| `factdb verify FACT_ID` | Submit / approve / reject / revise |
| `factdb history FACT_ID` | Show version history |
| `factdb related FACT_ID` | Show outgoing relationships |
| `factdb prereqs FACT_ID` | Backward-chain prerequisite tree |
| `factdb export` | Export verified facts as JSON |
| `factdb web` | Launch the web UI (projects, elements, facts, review) |

---

## Web UI

`factdb web` launches a browser-based interface for exploring the knowledge
base and reviewing design decisions:

| Page | URL | Description |
|------|-----|-------------|
| Projects | `/projects` | Browse all projects; filter by status and domain |
| Project detail | `/projects/<id>` | Elements, interactions graph, supporting facts, integration code |
| Design Elements | `/elements` | Browse reusable design elements; filter by category |
| Element detail | `/elements/<id>` | Approach, alternatives, supporting facts, review form |
| Facts | `/facts` | Search and filter engineering facts |
| Fact detail | `/facts/<id>` | Full fact with formula, relationships, and verification history |

### Starting the web server

```bash
# Default: http://127.0.0.1:5000/
factdb web

# Custom host / port
factdb web --host 0.0.0.0 --port 8080

# Debug mode (auto-reloads on code changes)
factdb web --debug

# Against a specific database
factdb --db sqlite:////path/to/factdb.sqlite web
```

### Reviewing design elements

Each **Design Element** detail page (`/elements/<id>`) includes a **Review
Notes** form.  Submit free-text notes to record your assessment — these are
saved as `verification_notes` on the element and surfaced in the project view
with a ✓ indicator.

---

## Project Structure

```
factdb/
├── __init__.py          Public API
├── __main__.py          Entry point (python -m factdb)
├── models.py            SQLAlchemy ORM models and enumerations
├── database.py          Engine / session management
├── repository.py        CRUD + versioning operations
├── search.py            Keyword + structured search
├── verification.py      Verification lifecycle workflow
├── reasoning.py         Backward/forward chaining, decision trees
├── seeder.py            Seed-data loader (engineering facts)
├── project_models.py    Project / DesignElement ORM models
├── project_repository.py  Project + element CRUD
├── project_seeder.py    Seed-data loader (projects & elements)
├── software_models.py   SoftwareArtifact / BenchmarkTest models
├── software_repository.py  Software artifact CRUD + benchmark runner
├── software_seeder.py   Seed-data loader (software artifacts)
└── web/                 Flask web UI
    ├── app.py           Application factory + route handlers
    ├── static/
    │   └── style.css    UI stylesheet
    └── templates/web/
        ├── base.html          Shared layout (nav, flash messages)
        ├── projects.html      Projects list with filters
        ├── project_detail.html  Elements, interaction graph, facts
        ├── elements.html      Design elements list
        ├── element_detail.html  Element detail + review form
        ├── facts.html         Facts list with search
        └── fact_detail.html   Fact with relationships + verifications

tests/
├── conftest.py          Shared pytest fixtures (in-memory SQLite)
├── test_repository.py   CRUD, versioning, relationships
├── test_search.py       Search filters and full-text
├── test_verification.py Lifecycle workflow
├── test_reasoning.py    Backward/forward chaining, conflict detection
└── test_seeder.py       Seed data integrity

data/
└── factdb.sqlite        Default database (created on first run)
```

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Extending the Knowledge Base

Add new engineering domains or facts by editing `factdb/seed_data.py` and
running `factdb seed` again (idempotent — existing facts are skipped).

To contribute programmatically:

```python
repo.create(
    title="...",
    content="...",
    domain=EngineeringDomain.CIVIL,
    detail_level=DetailLevel.ADVANCED,
    tags=["buckling", "columns"],
    created_by="you",
)
session.commit()
```
