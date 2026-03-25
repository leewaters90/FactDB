"""
FactDB command-line interface.

Usage examples::

    python -m factdb.cli init-db
    python -m factdb.cli seed
    python -m factdb.cli search "entropy"
    python -m factdb.cli list --domain mechanical --level fundamental
    python -m factdb.cli show <fact-id>
    python -m factdb.cli add
    python -m factdb.cli verify <fact-id> --action approve --by reviewer1
    python -m factdb.cli history <fact-id>
    python -m factdb.cli related <fact-id>
    python -m factdb.cli prereqs <fact-id>
"""

from __future__ import annotations

import json
import os
import sys

import click
from tabulate import tabulate

from factdb.database import get_session_factory, init_db, reset_engine
from factdb.models import DetailLevel, EngineeringDomain, FactStatus, RelationshipType
from factdb.repository import FactRepository
from factdb.reasoning import ReasoningEngine
from factdb.search import FactSearch
from factdb.verification import VerificationWorkflow


def _make_session(db_url: str | None = None):
    factory = get_session_factory(db_url)
    return factory()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--db",
    envvar="FACTDB_DATABASE_URL",
    default=None,
    help="SQLAlchemy database URL (overrides FACTDB_DATABASE_URL env var).",
)
@click.pass_context
def cli(ctx, db):
    """FactDB — Engineering fact database and reasoning engine."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


# ---------------------------------------------------------------------------
# init-db
# ---------------------------------------------------------------------------


@cli.command("init-db")
@click.pass_context
def init_db_cmd(ctx):
    """Initialise the database schema (creates tables if they don't exist)."""
    reset_engine()
    engine = init_db(ctx.obj.get("db"))
    click.echo(f"Database initialised: {engine.url}")


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def seed(ctx):
    """Seed the database with curated engineering facts."""
    from factdb.seeder import seed as do_seed

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        result = do_seed(session)
        click.echo(
            f"Seeded: {result['created']} facts created, "
            f"{result['skipped']} skipped, "
            f"{result['relationships']} relationships created."
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# seed-devices
# ---------------------------------------------------------------------------


@cli.command("seed-devices")
@click.pass_context
def seed_devices_cmd(ctx):
    """Seed the database with device-domain engineering facts."""
    from factdb.device_seeder import seed_devices

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        result = seed_devices(session)
        click.echo(
            f"Device facts seeded: {result['created']} created, "
            f"{result['skipped']} skipped, "
            f"{result['relationships']} relationships created."
        )
    finally:
        session.close()

# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("query", required=False, default=None)
@click.option("--domain", default=None, help="Engineering domain filter.")
@click.option("--category", default=None, help="Category filter.")
@click.option("--level", default=None, help="Detail level filter.")
@click.option("--status", default=None, help="Status filter.")
@click.option("--tag", "tags", multiple=True, help="Tag filter (repeatable).")
@click.option("--limit", default=20, show_default=True, help="Max results.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--record-usage", "record_usage", is_flag=True, default=False, help="Record usage for returned facts.")
@click.option("--by", default=None, help="Identity to record in usage log.")
@click.pass_context
def search(ctx, query, domain, category, level, status, tags, limit, as_json, record_usage, by):
    """Search facts by keyword and/or filters."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        searcher = FactSearch(session)
        domain_enum = EngineeringDomain(domain) if domain else None
        level_enum = DetailLevel(level) if level else None
        status_enum = FactStatus(status) if status else None

        results = searcher.search(
            query=query,
            domain=domain_enum,
            category=category,
            detail_level=level_enum,
            status=status_enum,
            tags=list(tags) if tags else None,
            limit=limit,
            record_usage=record_usage,
            usage_by=by,
        )

        if record_usage:
            session.commit()

        if as_json:
            click.echo(json.dumps([f.to_dict() for f in results], indent=2))
        else:
            _print_facts_table(results)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@cli.command("list")
@click.option("--domain", default=None)
@click.option("--status", default=None)
@click.option("--level", default=None)
@click.option("--limit", default=50, show_default=True)
@click.pass_context
def list_facts(ctx, domain, status, level, limit):
    """List facts with optional filters."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        domain_enum = EngineeringDomain(domain) if domain else None
        level_enum = DetailLevel(level) if level else None
        status_enum = FactStatus(status) if status else None

        facts = repo.list_all(
            domain=domain_enum,
            status=status_enum,
            detail_level=level_enum,
            limit=limit,
        )
        _print_facts_table(facts)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("fact_id")
@click.pass_context
def show(ctx, fact_id):
    """Show full details of a fact."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        fact = repo.get(fact_id)
        if fact is None:
            click.echo(f"Fact not found: {fact_id!r}", err=True)
            sys.exit(1)

        click.echo(f"\n{'='*70}")
        click.echo(f"  {fact.title}")
        click.echo(f"{'='*70}")
        click.echo(f"  ID          : {fact.id}")
        click.echo(f"  Domain      : {_val(fact.domain)}")
        click.echo(f"  Category    : {fact.category or '—'} / {fact.subcategory or '—'}")
        click.echo(f"  Detail Level: {_val(fact.detail_level)}")
        click.echo(f"  Status      : {_val(fact.status)}  (v{fact.version})")
        click.echo(f"  Confidence  : {fact.confidence_score:.2f}")
        click.echo(f"  Tags        : {', '.join(t.name for t in fact.tags) or '—'}")
        click.echo(f"\n  Content:\n    {fact.content}")
        if fact.formula:
            click.echo(f"\n  Formula: {fact.formula}")
        if fact.units:
            click.echo(f"  Units  : {fact.units}")
        if fact.extended_content:
            click.echo(f"\n  Extended:\n    {fact.extended_content}")
        if fact.source:
            click.echo(f"\n  Source: {fact.source}")
        click.echo(f"{'='*70}\n")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# most-used
# ---------------------------------------------------------------------------


@cli.command("most-used")
@click.option("--limit", default=20, show_default=True, help="Number of facts to show.")
@click.option("--min-count", default=1, show_default=True, help="Minimum use count.")
@click.option("--domain", default=None, help="Filter by engineering domain.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def most_used_cmd(ctx, limit, min_count, domain, as_json):
    """List most-used facts, ordered by use count descending.

    Highlights high-value facts for prioritised verification and maintenance.
    """
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        domain_enum = EngineeringDomain(domain) if domain else None
        facts = repo.list_most_used(limit=limit, min_use_count=min_count, domain=domain_enum)

        if not facts:
            click.echo("No facts with recorded usage yet.")
            return

        if as_json:
            click.echo(json.dumps([f.to_dict() for f in facts], indent=2))
        else:
            rows = [
                [
                    f.id[:8],
                    f.use_count,
                    f.last_used_at.strftime("%Y-%m-%d %H:%M") if f.last_used_at else "—",
                    _val(f.status),
                    (f.title[:55] + "…") if len(f.title) > 55 else f.title,
                ]
                for f in facts
            ]
            click.echo(
                tabulate(
                    rows,
                    headers=["ID", "Uses", "Last Used", "Status", "Title"],
                    tablefmt="simple",
                )
            )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# add  (interactive)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--title", prompt=True)
@click.option("--content", prompt=True)
@click.option(
    "--domain",
    prompt=True,
    default="general",
    type=click.Choice([d.value for d in EngineeringDomain]),
)
@click.option("--category", prompt=True, default="")
@click.option("--subcategory", prompt=True, default="")
@click.option(
    "--level",
    prompt=True,
    default="fundamental",
    type=click.Choice([l.value for l in DetailLevel]),
)
@click.option("--source", prompt=True, default="")
@click.option("--tags", prompt=True, default="", help="Comma-separated tags.")
@click.option("--by", default=None, help="Author identity.")
@click.pass_context
def add(ctx, title, content, domain, category, subcategory, level, source, tags, by):
    """Add a new fact to the database (interactive)."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        fact = repo.create(
            title=title,
            content=content,
            domain=EngineeringDomain(domain),
            category=category or None,
            subcategory=subcategory or None,
            detail_level=DetailLevel(level),
            source=source or None,
            tags=tag_list,
            created_by=by,
        )
        session.commit()
        click.echo(f"Created fact {fact.id!r}: {fact.title!r}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("fact_id")
@click.option(
    "--action",
    type=click.Choice(["submit", "approve", "reject", "revise"]),
    required=True,
)
@click.option("--by", required=True, help="Reviewer identity.")
@click.option("--notes", default=None, help="Review notes.")
@click.pass_context
def verify(ctx, fact_id, action, by, notes):
    """Manage the verification lifecycle of a fact."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        workflow = VerificationWorkflow(session)
        if action == "submit":
            fact = workflow.submit_for_review(fact_id, submitted_by=by)
            session.commit()
            click.echo(f"Submitted {fact.id!r} for review.")
        elif action == "approve":
            rec = workflow.approve(fact_id, verified_by=by, notes=notes)
            session.commit()
            click.echo(f"Approved {fact_id!r} (verification id: {rec.id!r})")
        elif action == "reject":
            rec = workflow.reject(fact_id, verified_by=by, notes=notes)
            session.commit()
            click.echo(f"Rejected {fact_id!r} (verification id: {rec.id!r})")
        elif action == "revise":
            rec = workflow.request_revision(fact_id, verified_by=by, notes=notes)
            session.commit()
            click.echo(f"Revision requested for {fact_id!r}.")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("fact_id")
@click.pass_context
def history(ctx, fact_id):
    """Show the version history of a fact."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        versions = repo.get_history(fact_id)
        if not versions:
            click.echo("No version history found.")
            return
        rows = [
            [
                v.version,
                v.changed_at.strftime("%Y-%m-%d %H:%M") if v.changed_at else "—",
                v.changed_by or "—",
                (v.change_reason or "")[:60],
                _val(v.status),
            ]
            for v in versions
        ]
        click.echo(
            tabulate(rows, headers=["Ver", "Changed At", "By", "Reason", "Status"])
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# related
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("fact_id")
@click.option("--rel-type", default=None, help="Filter by relationship type.")
@click.pass_context
def related(ctx, fact_id, rel_type):
    """Show facts related to the given fact."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        rel_enum = RelationshipType(rel_type) if rel_type else None
        pairs = repo.get_related_facts(fact_id, relationship_type=rel_enum)
        if not pairs:
            click.echo("No related facts found.")
            return
        rows = [
            [_val(rel.relationship_type), f"{rel.weight:.1f}", fact.title, _val(fact.status)]
            for rel, fact in pairs
        ]
        click.echo(
            tabulate(rows, headers=["Relationship", "Weight", "Title", "Status"])
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# prereqs (backward chaining)
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("fact_id")
@click.option("--depth", default=10, show_default=True, help="Max traversal depth.")
@click.pass_context
def prereqs(ctx, fact_id, depth):
    """Show prerequisite chain for a fact (backward chaining)."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        engine = ReasoningEngine(session)
        result = engine.collect_prerequisites(fact_id, max_depth=depth)
        click.echo(result.summary())
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--domain", default=None, help="Filter by domain.")
@click.option("--status", default="verified", show_default=True)
@click.option("--output", "-o", default="-", help="Output file path (- for stdout).")
@click.pass_context
def export(ctx, domain, status, output):
    """Export facts to JSON (for AI model ingestion)."""
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        domain_enum = EngineeringDomain(domain) if domain else None
        status_enum = FactStatus(status) if status else None
        facts = repo.list_all(domain=domain_enum, status=status_enum, limit=10000)
        data = [f.to_dict() for f in facts]
        payload = json.dumps(data, indent=2)
        if output == "-":
            click.echo(payload)
        else:
            with open(output, "w") as fh:
                fh.write(payload)
            click.echo(f"Exported {len(data)} facts to {output!r}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _val(v) -> str:
    """Return the .value of an enum or the string itself."""
    return v.value if hasattr(v, "value") else str(v)


def _print_facts_table(facts) -> None:
    if not facts:
        click.echo("No facts found.")
        return
    rows = [
        [
            f.id[:8] + "…",
            _val(f.domain),
            _val(f.detail_level),
            _val(f.status),
            f"{f.confidence_score:.2f}",
            f.title[:60],
        ]
        for f in facts
    ]
    click.echo(
        tabulate(
            rows,
            headers=["ID", "Domain", "Level", "Status", "Conf.", "Title"],
        )
    )
    click.echo(f"\n{len(facts)} fact(s) found.")


# ---------------------------------------------------------------------------
# seed-projects
# ---------------------------------------------------------------------------


@cli.command("seed-projects")
@click.pass_context
def seed_projects_cmd(ctx):
    """Seed shared DesignElements and mechatronics project designs."""
    from factdb.project_seeder import seed_projects

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        result = seed_projects(session)
        click.echo(
            f"DesignElements: {result['elements_created']} created, "
            f"{result['elements_skipped']} skipped."
        )
        click.echo(
            f"Projects: {result['projects_created']} created, "
            f"{result['projects_skipped']} skipped."
        )
        click.echo(f"Project-element links: {result['links_created']} processed.")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# list-projects
# ---------------------------------------------------------------------------


@cli.command("list-projects")
@click.option("--status", default=None, help="Filter by project status.")
@click.option("--domain", default=None, help="Filter by engineering domain.")
@click.option("--limit", default=50, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_projects_cmd(ctx, status, domain, limit, as_json):
    """List mechatronics projects."""
    from factdb.project_models import ProjectStatus
    from factdb.project_repository import ProjectRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = ProjectRepository(session)
        status_enum = ProjectStatus(status) if status else None
        projects = repo.list_projects(status=status_enum, domain=domain, limit=limit)
        if not projects:
            click.echo("No projects found.")
            return
        if as_json:
            click.echo(json.dumps([p.to_dict() for p in projects], indent=2))
        else:
            rows = [
                [
                    p.id[:8] + "…",
                    _val(p.domain),
                    _val(p.status),
                    len(p.element_links),
                    p.title[:60],
                ]
                for p in projects
            ]
            click.echo(tabulate(rows, headers=["ID", "Domain", "Status", "Elements", "Title"]))
            click.echo(f"\n{len(projects)} project(s) found.")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# show-project
# ---------------------------------------------------------------------------


@cli.command("show-project")
@click.argument("project_title")
@click.pass_context
def show_project_cmd(ctx, project_title):
    """Show full details of a project including its design elements."""
    from factdb.project_repository import ProjectRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = ProjectRepository(session)
        project = repo.get_project_by_title(project_title)
        if project is None:
            click.echo(f"Project not found: {project_title!r}", err=True)
            sys.exit(1)
        click.echo(f"\n{'='*70}")
        click.echo(f"  {project.title}")
        click.echo(f"{'='*70}")
        click.echo(f"  Status  : {_val(project.status)}")
        click.echo(f"  Domain  : {_val(project.domain)}")
        click.echo(f"  Objective: {project.objective or '—'}")
        click.echo(f"  Constraints: {project.constraints or '—'}")
        click.echo(f"\n  Description:\n    {project.description}")
        click.echo(f"\n  Design Elements ({len(project.element_links)}):")
        for link in project.element_links:
            el = link.element
            note = f"  [{link.usage_notes}]" if link.usage_notes else ""
            click.echo(f"    [{_val(el.component_category):14}] {el.title}{note}")
        click.echo(f"{'='*70}\n")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# list-elements
# ---------------------------------------------------------------------------


@cli.command("list-elements")
@click.option("--category", default=None, help="Filter by component category.")
@click.option("--limit", default=100, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_elements_cmd(ctx, category, limit, as_json):
    """List shared design elements."""
    from factdb.project_models import ComponentCategory
    from factdb.project_repository import ProjectRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = ProjectRepository(session)
        cat_enum = ComponentCategory(category) if category else None
        elements = repo.list_design_elements(component_category=cat_enum, limit=limit)
        if not elements:
            click.echo("No design elements found.")
            return
        if as_json:
            click.echo(json.dumps([e.to_dict() for e in elements], indent=2))
        else:
            rows = [
                [
                    e.id[:8] + "…",
                    _val(e.component_category),
                    len(e.project_links),
                    e.title[:60],
                ]
                for e in elements
            ]
            click.echo(tabulate(rows, headers=["ID", "Category", "Projects", "Title"]))
            click.echo(f"\n{len(elements)} element(s) found.")
    finally:
        session.close()


if __name__ == "__main__":
    cli()
