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
from factdb.json_store import DEFAULT_FACTS_DIR, JsonFactStore
from factdb.models import DetailLevel, EngineeringDomain, FactStatus, RelationshipType
from factdb.repository import FactRepository
from factdb.reasoning import ReasoningEngine
from factdb.search import FactSearch
from factdb.verification import VerificationWorkflow


def _make_session(db_url: str | None = None):
    factory = get_session_factory(db_url)
    return factory()


def _make_repo(session, facts_dir: str | None = None, *, with_json_store: bool = True) -> FactRepository:
    """Return a FactRepository, optionally wired to a JsonFactStore."""
    json_store = None
    if with_json_store:
        json_store = JsonFactStore(facts_dir or DEFAULT_FACTS_DIR)
    return FactRepository(session, json_store=json_store)


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
@click.option(
    "--facts-dir",
    envvar="FACTDB_FACTS_DIR",
    default=None,
    help="Root directory for JSON fact files (default: data/facts/ next to project).",
)
@click.pass_context
def cli(ctx, db, facts_dir):
    """FactDB — Engineering fact database and reasoning engine."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db
    ctx.obj["facts_dir"] = facts_dir


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
# seed-software
# ---------------------------------------------------------------------------


@cli.command("seed-software")
@click.pass_context
def seed_software_cmd(ctx):
    """Seed the database with software functions, transforms, and benchmark tests."""
    from factdb.software_seeder import seed_software

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        result = seed_software(session)
        session.commit()
        click.echo(
            f"Software artifacts seeded: {result['artifacts_created']} created, "
            f"{result['artifacts_skipped']} skipped, "
            f"{result['benchmarks_created']} benchmark tests created."
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
        repo = _make_repo(session, ctx.obj.get("facts_dir"))
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
        if repo.json_store is not None:
            path = repo.json_store.fact_path(fact.to_dict())
            click.echo(f"JSON file written: {path}")
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
# export-json
# ---------------------------------------------------------------------------


@cli.command("export-json")
@click.option(
    "--output-dir",
    default=None,
    help="Root directory for JSON files (default: data/facts/ next to project).",
)
@click.option("--domain", default=None, help="Filter by domain.")
@click.option("--status", default=None, help="Filter by lifecycle status.")
@click.pass_context
def export_json_cmd(ctx, output_dir, domain, status):
    """Export all facts to a folder tree of JSON files.

    Each fact is written to:

        {output-dir}/{domain}/{category}/{fact-id}.json

    The resulting tree is human-readable, diff-friendly, and can be edited
    directly then re-imported with the ``import-json`` command.
    """
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = FactRepository(session)
        domain_enum = EngineeringDomain(domain) if domain else None
        status_enum = FactStatus(status) if status else None
        facts = repo.list_all(domain=domain_enum, status=status_enum, limit=10000)

        store = JsonFactStore(output_dir or ctx.obj.get("facts_dir") or DEFAULT_FACTS_DIR)
        written = 0
        for fact in facts:
            store.write_fact(fact.to_dict())
            written += 1

        click.echo(f"Exported {written} fact(s) to {store.base_dir}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# import-json
# ---------------------------------------------------------------------------


@cli.command("import-json")
@click.option(
    "--input-dir",
    default=None,
    help="Root directory of JSON fact files (default: data/facts/ next to project).",
)
@click.option("--by", default="import", show_default=True, help="Identity for the import operation.")
@click.option("--dry-run", is_flag=True, help="Report what would be imported without writing.")
@click.pass_context
def import_json_cmd(ctx, input_dir, by, dry_run):
    """Import facts from a JSON folder tree into the database.

    Reads all ``*.json`` files found recursively under the input directory
    and upserts each fact — creating it if the ID is new, updating it if the
    fact already exists.

    This is the reverse of ``export-json`` and is the recommended workflow
    for making bulk edits: export → edit files → import.
    """
    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        store = JsonFactStore(input_dir or ctx.obj.get("facts_dir") or DEFAULT_FACTS_DIR)
        all_dicts = store.load_all()

        if not all_dicts:
            click.echo(f"No JSON fact files found under {store.base_dir}")
            return

        if dry_run:
            click.echo(f"[dry-run] Would import {len(all_dicts)} fact file(s) from {store.base_dir}")
            for d in all_dicts[:10]:
                click.echo(f"  • {d.get('id', '?')[:8]}  {d.get('title', '?')}")
            if len(all_dicts) > 10:
                click.echo(f"  … and {len(all_dicts) - 10} more")
            return

        repo = FactRepository(session)
        created = updated = errors = 0
        for d in all_dicts:
            try:
                _, was_created = repo.upsert_from_dict(d, imported_by=by)
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                click.echo(f"  Warning: skipped {d.get('id', '?')!r} — {exc}", err=True)
                errors += 1

        session.commit()
        click.echo(
            f"Import complete: {created} created, {updated} updated, {errors} skipped "
            f"(from {store.base_dir})"
        )
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


# ===========================================================================
# software  — sub-group for software artifact commands
# ===========================================================================


@cli.group("software")
@click.pass_context
def software_group(ctx):
    """Manage software functions, transforms, benchmarks, and project packages."""
    ctx.ensure_object(dict)


# ---------------------------------------------------------------------------
# software list
# ---------------------------------------------------------------------------


@software_group.command("list")
@click.option(
    "--type", "artifact_type", default=None,
    type=click.Choice(["function", "transform"]),
    help="Filter by artifact type.",
)
@click.option(
    "--language", default=None,
    type=click.Choice(["python", "lua", "arduino"]),
    help="Filter by programming language.",
)
@click.option("--limit", default=50, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def software_list_cmd(ctx, artifact_type, language, limit, as_json):
    """List software functions and transforms."""
    from factdb.software_models import ProgrammingLanguage, SoftwareArtifactType
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        type_enum = SoftwareArtifactType(artifact_type) if artifact_type else None
        lang_enum = ProgrammingLanguage(language) if language else None
        artifacts = repo.list_artifacts(
            artifact_type=type_enum, language=lang_enum, limit=limit
        )
        if not artifacts:
            click.echo("No software artifacts found.")
            return
        if as_json:
            click.echo(json.dumps([a.to_dict() for a in artifacts], indent=2))
        else:
            rows = [
                [
                    a.id[:8] + "…",
                    _val(a.artifact_type),
                    _val(a.language),
                    len(a.benchmark_tests),
                    (a.fact.title[:55] + "…") if len(a.fact.title) > 55 else a.fact.title,
                ]
                for a in artifacts
            ]
            click.echo(
                tabulate(
                    rows,
                    headers=["ID", "Type", "Language", "Benchmarks", "Title"],
                    tablefmt="simple",
                )
            )
            click.echo(f"\n{len(artifacts)} artifact(s) found.")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software show
# ---------------------------------------------------------------------------


@software_group.command("show")
@click.argument("fact_id")
@click.pass_context
def software_show_cmd(ctx, fact_id):
    """Show full details of a software function or transform (by fact ID or artifact ID)."""
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        # Accept either the artifact's own ID or the linked fact ID
        artifact = repo.get_artifact(fact_id) or repo.get_artifact_by_fact_id(fact_id)
        if artifact is None:
            click.echo(f"Software artifact not found: {fact_id!r}", err=True)
            sys.exit(1)

        fact = artifact.fact
        click.echo(f"\n{'='*70}")
        click.echo(f"  {fact.title}")
        click.echo(f"{'='*70}")
        click.echo(f"  Artifact ID : {artifact.id}")
        click.echo(f"  Fact ID     : {fact.id}")
        click.echo(f"  Type        : {_val(artifact.artifact_type)}")
        click.echo(f"  Language    : {_val(artifact.language)}"
                   + (f" {artifact.language_version}" if artifact.language_version else ""))
        click.echo(f"  Status      : {_val(fact.status)}")
        click.echo(f"  Tags        : {', '.join(t.name for t in fact.tags) or '—'}")
        if artifact.signature:
            click.echo(f"\n  Signature: {artifact.signature}")
        click.echo(f"\n  Description:\n    {fact.content}")
        if fact.extended_content:
            click.echo(f"\n  Extended:\n    {fact.extended_content}")
        click.echo(f"\n  Code:\n")
        for line in artifact.code.splitlines():
            click.echo(f"    {line}")
        pkgs = artifact.get_packages()
        if pkgs:
            click.echo(f"\n  Packages:")
            for p in pkgs:
                ver = p.get("version", "*")
                click.echo(f"    {p['name']}{ver}")
        benchmarks = artifact.benchmark_tests
        if benchmarks:
            click.echo(f"\n  Benchmark tests ({len(benchmarks)}):")
            for bt in benchmarks:
                click.echo(f"    [{bt.id[:8]}…] {bt.name}")
        click.echo(f"{'='*70}\n")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software add-function
# ---------------------------------------------------------------------------


@software_group.command("add-function")
@click.option("--title", prompt=True, help="Human-readable title.")
@click.option("--content", prompt=True, help="Concise description of the function.")
@click.option("--code", prompt=True, help="Full source code.")
@click.option("--signature", default="", prompt=True, help="Function signature string.")
@click.option(
    "--language", default="python", prompt=True,
    type=click.Choice(["python", "lua", "arduino"]),
)
@click.option("--language-version", "language_version", default="", prompt=True,
              help="Language version, e.g. '3.11'.")
@click.option("--category", default="", prompt=True)
@click.option("--tags", default="", prompt=True, help="Comma-separated tags.")
@click.option("--by", default=None, help="Author identity.")
@click.pass_context
def software_add_function_cmd(
    ctx, title, content, code, signature, language, language_version,
    category, tags, by
):
    """Add a new software function artifact."""
    from factdb.software_models import ProgrammingLanguage, SoftwareArtifactType
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        artifact = repo.create_artifact(
            title=title,
            content=content,
            artifact_type=SoftwareArtifactType.FUNCTION,
            code=code,
            language=ProgrammingLanguage(language),
            language_version=language_version or None,
            signature=signature or None,
            category=category or None,
            tags=tag_list,
            created_by=by,
        )
        session.commit()
        click.echo(f"Created function artifact {artifact.id!r} (fact: {artifact.fact_id!r}): {title!r}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software add-transform
# ---------------------------------------------------------------------------


@software_group.command("add-transform")
@click.option("--title", prompt=True, help="Human-readable title.")
@click.option("--content", prompt=True, help="Concise description of the transform.")
@click.option("--code", prompt=True, help="Full source code.")
@click.option("--signature", default="", prompt=True, help="Function signature string.")
@click.option(
    "--language", default="python", prompt=True,
    type=click.Choice(["python", "lua", "arduino"]),
)
@click.option("--language-version", "language_version", default="", prompt=True,
              help="Language version, e.g. '3.11'.")
@click.option("--category", default="", prompt=True)
@click.option("--tags", default="", prompt=True, help="Comma-separated tags.")
@click.option("--by", default=None, help="Author identity.")
@click.pass_context
def software_add_transform_cmd(
    ctx, title, content, code, signature, language, language_version,
    category, tags, by
):
    """Add a new software transform artifact."""
    from factdb.software_models import ProgrammingLanguage, SoftwareArtifactType
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        artifact = repo.create_artifact(
            title=title,
            content=content,
            artifact_type=SoftwareArtifactType.TRANSFORM,
            code=code,
            language=ProgrammingLanguage(language),
            language_version=language_version or None,
            signature=signature or None,
            category=category or None,
            tags=tag_list,
            created_by=by,
        )
        session.commit()
        click.echo(f"Created transform artifact {artifact.id!r} (fact: {artifact.fact_id!r}): {title!r}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software add-benchmark
# ---------------------------------------------------------------------------


@software_group.command("add-benchmark")
@click.argument("artifact_id")
@click.option("--name", prompt=True, help="Short unique name for this test.")
@click.option("--test-code", "test_code", prompt=True,
              help="Runnable test code. Assign outcome to 'result'.")
@click.option("--description", default="", prompt=True)
@click.option("--expected", default="", help="Expected value of 'result' (JSON).")
@click.option("--tolerance", default=None, type=float,
              help="Absolute tolerance for float comparisons.")
@click.pass_context
def software_add_benchmark_cmd(ctx, artifact_id, name, test_code, description, expected, tolerance):
    """Add a benchmark test to a software artifact."""
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        expected_val = json.loads(expected) if expected else None
        test = repo.add_benchmark_test(
            artifact_id=artifact_id,
            name=name,
            test_code=test_code,
            description=description or None,
            expected_output=expected_val,
            tolerance=tolerance,
        )
        session.commit()
        click.echo(f"Added benchmark test {test.id!r}: {name!r}")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software run-benchmark
# ---------------------------------------------------------------------------


@software_group.command("run-benchmark")
@click.argument("artifact_id")
@click.option("--test-id", "test_id", default=None, help="Run only a specific test by ID.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def software_run_benchmark_cmd(ctx, artifact_id, test_id, as_json):
    """Run benchmark tests for a software artifact.

    Only Python artifacts are currently supported for execution.
    The test code should assign the value under test to a variable
    named 'result'.
    """
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        try:
            results = repo.run_benchmark(artifact_id, test_id=test_id)
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if not results:
            click.echo("No benchmark tests found.")
            return

        if as_json:
            click.echo(json.dumps(results, indent=2, default=str))
        else:
            passed = sum(1 for r in results if r["passed"])
            total = len(results)
            click.echo(f"\nBenchmark results: {passed}/{total} passed\n")
            rows = [
                [
                    "✓" if r["passed"] else "✗",
                    r["name"],
                    f"{r['elapsed_ms']:.2f} ms" if r["elapsed_ms"] is not None else "—",
                    str(r["result"]) if r["result"] is not None else "—",
                    r["error"] or "",
                ]
                for r in results
            ]
            click.echo(
                tabulate(
                    rows,
                    headers=["", "Test", "Time", "Result", "Error"],
                    tablefmt="simple",
                )
            )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software add-package
# ---------------------------------------------------------------------------


@software_group.command("add-package")
@click.argument("project_id")
@click.option("--name", "package_name", prompt=True, help="Package name, e.g. 'numpy'.")
@click.option("--version", "package_version", default="", prompt=True,
              help="Version specifier, e.g. '>=1.24.0'.")
@click.option(
    "--language", default="python",
    type=click.Choice(["python", "lua", "arduino"]),
    help="Target language.",
)
@click.option("--notes", default=None, help="Optional note.")
@click.pass_context
def software_add_package_cmd(ctx, project_id, package_name, package_version, language, notes):
    """Declare a package dependency for a project."""
    from factdb.software_models import ProgrammingLanguage
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        pkg = repo.add_project_package(
            project_id=project_id,
            package_name=package_name,
            package_version=package_version or None,
            language=ProgrammingLanguage(language),
            notes=notes,
        )
        session.commit()
        click.echo(f"Added package {pkg.package_name!r} to project {project_id!r}")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# software requirements
# ---------------------------------------------------------------------------


@software_group.command("requirements")
@click.argument("project_id")
@click.option("--output", "-o", default="-", help="Output file path (- for stdout).")
@click.pass_context
def software_requirements_cmd(ctx, project_id, output):
    """Generate a requirements.txt for a project's Python package dependencies."""
    from factdb.software_repository import SoftwareRepository

    reset_engine()
    init_db(ctx.obj.get("db"))
    session = _make_session(ctx.obj.get("db"))
    try:
        repo = SoftwareRepository(session)
        try:
            content = repo.generate_requirements_txt(project_id)
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        if not content:
            click.echo("No Python packages declared for this project.")
            return

        if output == "-":
            click.echo(content)
        else:
            with open(output, "w") as fh:
                fh.write(content)
            click.echo(f"requirements.txt written to {output!r}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# web — launch the web UI
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# deps-chart  — standalone HTML dependency chart
# ---------------------------------------------------------------------------


@cli.command("deps-chart")
@click.option(
    "--output", "-o",
    default="deps_chart.html",
    show_default=True,
    help="Output HTML file path.",
)
@click.pass_context
def deps_chart_cmd(ctx, output):
    """Generate a standalone interactive dependency chart (HTML/D3.js).

    Writes a self-contained HTML file that visualises all facts, design
    elements, and projects as a force-directed graph.  Open the file in any
    modern browser — no server required.
    """
    db_url = ctx.obj.get("db")
    session_factory = get_session_factory(db_url)
    session = session_factory()

    try:
        from factdb.models import Fact, FactRelationship
        from factdb.project_models import DesignElement, Project
        from factdb.project_repository import ProjectRepository

        facts = (
            session.query(Fact)
            .filter(Fact.is_active.is_(True))
            .order_by(Fact.domain, Fact.title)
            .all()
        )
        relationships = session.query(FactRelationship).all()
        repo = ProjectRepository(session)
        elements = repo.list_design_elements(limit=1000)
        projects = repo.list_projects(limit=500)

        fact_id_set: set[str] = set()
        element_id_set: set[str] = set()
        nodes: list[dict] = []
        edges: list[dict] = []

        for f in facts:
            nodes.append({
                "id": f.id, "label": f.title, "type": "fact",
                "group": f.domain, "status": f.status,
            })
            fact_id_set.add(f.id)

        for el in elements:
            nodes.append({
                "id": el.id, "label": el.title, "type": "element",
                "group": el.component_category,
            })
            element_id_set.add(el.id)
            for f in el.supporting_facts:
                if f.id in fact_id_set:
                    edges.append({"source": el.id, "target": f.id, "type": "uses_fact", "weight": 1.0})

        for proj in projects:
            nodes.append({
                "id": proj.id, "label": proj.title, "type": "project",
                "group": proj.domain, "status": proj.status,
            })
            for el in proj.elements:
                if el.id in element_id_set:
                    edges.append({"source": proj.id, "target": el.id, "type": "uses_element", "weight": 1.0})
            for f in proj.supporting_facts:
                if f.id in fact_id_set:
                    edges.append({"source": proj.id, "target": f.id, "type": "uses_fact", "weight": 1.0})

        for rel in relationships:
            if rel.source_fact_id in fact_id_set and rel.target_fact_id in fact_id_set:
                edges.append({
                    "source": rel.source_fact_id,
                    "target": rel.target_fact_id,
                    "type": rel.relationship_type,
                    "weight": rel.weight or 1.0,
                })

        graph_json = json.dumps({"nodes": nodes, "edges": edges})
        stats = {
            "facts": len(facts),
            "elements": len(elements),
            "projects": len(projects),
            "edges": len(edges),
        }

    finally:
        session.close()

    # Build standalone HTML (D3.js loaded from CDN)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FactDB Dependency Chart</title>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:14px;background:#f5f7fa;color:#1a1f2e}}
header{{background:#fff;border-bottom:1px solid #dde1e9;padding:0 24px;height:52px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:100;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
header .brand{{font-weight:700;font-size:18px;color:#3b6ef0}}
.toolbar{{background:#fff;border-bottom:1px solid #dde1e9;padding:10px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:16px}}
.toolbar label{{display:flex;align-items:center;gap:6px;cursor:pointer}}
.toolbar input[type=text]{{border:1px solid #dde1e9;border-radius:6px;padding:5px 10px;font-size:13px;min-width:180px}}
.btn{{background:#3b6ef0;color:#fff;border:none;border-radius:6px;padding:6px 14px;font-size:13px;cursor:pointer;font-weight:500}}
.btn:hover{{background:#2a56d6}}
.btn-outline{{background:transparent;border:1px solid #dde1e9;color:#1a1f2e}}
.btn-outline:hover{{background:#f5f7fa}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;padding:12px 24px;background:#fff;border-bottom:1px solid #dde1e9}}
.stat{{display:flex;align-items:center;gap:8px;font-size:13px}}
#canvas-wrap{{position:relative;overflow:hidden;background:#fafbff;height:calc(100vh - 180px)}}
#chart-svg{{width:100%;height:100%}}
#tt{{position:absolute;pointer-events:none;display:none;background:rgba(26,31,46,.9);color:#fff;font-size:12px;padding:8px 12px;border-radius:6px;max-width:260px;line-height:1.5;box-shadow:0 4px 12px rgba(0,0,0,.25);z-index:10}}
footer{{padding:10px 24px;font-size:12px;color:#6b7280;background:#fff;border-top:1px solid #dde1e9;display:flex;flex-wrap:wrap;gap:16px;align-items:center}}
footer span{{display:flex;align-items:center;gap:6px}}
</style>
</head>
<body>
<header>
  <span class="brand">FactDB</span>
  <span style="color:#6b7280;font-size:13px;">Dependency Chart</span>
</header>
<div class="stats">
  <div class="stat"><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill="#3b6ef0"/></svg><strong>{stats["facts"]}</strong> Facts</div>
  <div class="stat"><svg width="12" height="12"><polygon points="6,1 11,6 6,11 1,6" fill="#16a34a"/></svg><strong>{stats["elements"]}</strong> Design Elements</div>
  <div class="stat"><svg width="12" height="12"><rect x="1" y="2" width="10" height="8" rx="2" fill="#d97706"/></svg><strong>{stats["projects"]}</strong> Projects</div>
  <div class="stat" style="color:#6b7280"><strong>{stats["edges"]}</strong> Edges</div>
</div>
<div class="toolbar">
  <label><input type="checkbox" id="tf" checked> Facts</label>
  <label><input type="checkbox" id="te" checked> Design Elements</label>
  <label><input type="checkbox" id="tp" checked> Projects</label>
  <input type="text" id="search" placeholder="Highlight by name…">
  <button class="btn btn-outline" id="reset">Reset view</button>
</div>
<div id="canvas-wrap">
  <svg id="chart-svg"></svg>
  <div id="tt"></div>
</div>
<footer>
  <strong style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Legend</strong>
  <span><svg width="16" height="16"><circle cx="8" cy="8" r="6" fill="#3b6ef0"/></svg>Fact</span>
  <span><svg width="16" height="16"><polygon points="8,2 14,8 8,14 2,8" fill="#16a34a"/></svg>Design Element</span>
  <span><svg width="16" height="16"><rect x="2" y="3" width="12" height="10" rx="2" fill="#d97706"/></svg>Project</span>
  <span><svg width="24" height="12"><line x1="0" y1="6" x2="24" y2="6" stroke="#dc2626" stroke-width="1.5"/></svg>depends_on</span>
  <span><svg width="24" height="12"><line x1="0" y1="6" x2="24" y2="6" stroke="#059669" stroke-width="1.5" stroke-dasharray="5,4"/></svg>supports</span>
  <span><svg width="24" height="12"><line x1="0" y1="6" x2="24" y2="6" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="2,3"/></svg>uses element</span>
  <span><svg width="24" height="12"><line x1="0" y1="6" x2="24" y2="6" stroke="#0891b2" stroke-width="1"/></svg>uses fact</span>
</footer>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
(function(){{
const RAW={graph_json};
const nodeMap=new Map(RAW.nodes.map(n=>[n.id,n]));
const NODE_R={{fact:7,element:9,project:10}};
const NODE_COLOR={{fact:"#3b6ef0",element:"#16a34a",project:"#d97706"}};
const EDGE_COLOR={{depends_on:"#dc2626",supports:"#059669",uses_element:"#7c3aed",uses_fact:"#0891b2"}};
const EDGE_DASH={{depends_on:null,supports:"5,4",uses_element:"2,3",uses_fact:null}};
const EDGE_OP={{depends_on:.75,supports:.65,uses_element:.55,uses_fact:.4}};

const wrap=document.getElementById("canvas-wrap");
const W=wrap.clientWidth||900,H=wrap.clientHeight||600;
const svg=d3.select("#chart-svg").attr("width",W).attr("height",H);
const g=svg.append("g");
const zoom=d3.zoom().scaleExtent([.05,4]).on("zoom",e=>g.attr("transform",e.transform));
svg.call(zoom);

const defs=svg.append("defs");
Object.entries(EDGE_COLOR).forEach(([t,c])=>{{
  defs.append("marker").attr("id","a-"+t).attr("viewBox","0 -4 8 8").attr("refX",14).attr("refY",0)
    .attr("markerWidth",6).attr("markerHeight",6).attr("orient","auto")
    .append("path").attr("d","M0,-4L8,0L0,4").attr("fill",c);
}});

const simNodes=RAW.nodes.map(n=>({{...n}}));
const simEdges=RAW.edges.filter(e=>nodeMap.has(e.source)&&nodeMap.has(e.target)).map(e=>({{...e}}));
const sim=d3.forceSimulation(simNodes)
  .force("link",d3.forceLink(simEdges).id(d=>d.id).distance(d=>d.type==="uses_element"?80:d.type==="uses_fact"?70:60).strength(.3))
  .force("charge",d3.forceManyBody().strength(-120).distanceMax(400))
  .force("center",d3.forceCenter(W/2,H/2))
  .force("collide",d3.forceCollide(d=>NODE_R[d.type]+6))
  .alphaDecay(.025);

const el=g.append("g").selectAll("line").data(simEdges).join("line")
  .attr("stroke",d=>EDGE_COLOR[d.type]||"#aaa")
  .attr("stroke-width",d=>d.type==="depends_on"?1.5:1)
  .attr("stroke-dasharray",d=>EDGE_DASH[d.type]||null)
  .attr("stroke-opacity",d=>EDGE_OP[d.type]||.5)
  .attr("marker-end",d=>`url(#a-${{d.type}})`);

const nd=g.append("g").selectAll("g").data(simNodes,d=>d.id).join(en=>{{
  const ng=en.append("g").style("cursor","pointer");
  ng.each(function(d){{
    const s=d3.select(this),r=NODE_R[d.type];
    if(d.type==="fact") s.append("circle").attr("r",r);
    else if(d.type==="element"){{const q=r*1.4;s.append("polygon").attr("points",`0,${{-q}} ${{q}},0 0,${{q}} ${{-q}},0`);}}
    else{{const w=r*2.6,h=r*2;s.append("rect").attr("x",-w/2).attr("y",-h/2).attr("width",w).attr("height",h).attr("rx",3);}}
  }});
  ng.select("circle,polygon,rect")
    .attr("fill",d=>NODE_COLOR[d.type]).attr("fill-opacity",.85)
    .attr("stroke",d=>d3.color(NODE_COLOR[d.type]).darker(.6)).attr("stroke-width",1.2);
  ng.append("text").attr("dy",d=>NODE_R[d.type]+9).attr("text-anchor","middle")
    .attr("font-size","9px").attr("fill","#1a1f2e").attr("pointer-events","none")
    .text(d=>d.label.length>22?d.label.slice(0,21)+"…":d.label);
  ng.call(d3.drag()
    .on("start",(ev,d)=>{{if(!ev.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y;}})
    .on("drag", (ev,d)=>{{d.fx=ev.x;d.fy=ev.y;}})
    .on("end",  (ev,d)=>{{if(!ev.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}}));
  const tt=document.getElementById("tt");
  ng.on("mouseover",(ev,d)=>{{
    tt.innerHTML=`<strong>${{d.label}}</strong><br>Type: ${{d.type}}${{d.group?"<br>Group: "+d.group:""}}${{d.status?"<br>Status: "+d.status:""}}`;
    tt.style.display="block";mv(ev);
  }}).on("mousemove",ev=>mv(ev)).on("mouseout",()=>tt.style.display="none");
  ng.on("click",(ev,d)=>{{if(d.url)window.location.href=d.url;}});
  return ng;
}});

function mv(ev){{
  const tt=document.getElementById("tt"),r=wrap.getBoundingClientRect();
  let x=ev.clientX-r.left+14,y=ev.clientY-r.top-28;
  if(x+270>W)x=x-270;if(y<0)y=0;
  tt.style.left=x+"px";tt.style.top=y+"px";
}}

sim.on("tick",()=>{{
  el.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  nd.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
}});
sim.on("end",()=>{{
  const xs=simNodes.map(n=>n.x),ys=simNodes.map(n=>n.y);
  const xm=Math.min(...xs),xM=Math.max(...xs),ym=Math.min(...ys),yM=Math.max(...ys);
  const s=Math.min((W-80)/(xM-xm||1),(H-80)/(yM-ym||1),1);
  svg.call(zoom.transform,d3.zoomIdentity.translate(W/2-s*(xm+xM)/2,H/2-s*(ym+yM)/2).scale(s));
}});

let sf=true,se=true,sp=true;
function applyVis(){{
  const shown=new Set(simNodes.filter(n=>(n.type==="fact"&&sf)||(n.type==="element"&&se)||(n.type==="project"&&sp)).map(n=>n.id));
  nd.style("display",d=>shown.has(d.id)?null:"none");
  el.style("display",d=>{{
    const si=typeof d.source==="object"?d.source.id:d.source,ti=typeof d.target==="object"?d.target.id:d.target;
    return(shown.has(si)&&shown.has(ti))?null:"none";
  }});
}}
document.getElementById("tf").addEventListener("change",e=>{{sf=e.target.checked;applyVis();}});
document.getElementById("te").addEventListener("change",e=>{{se=e.target.checked;applyVis();}});
document.getElementById("tp").addEventListener("change",e=>{{sp=e.target.checked;applyVis();}});
document.getElementById("search").addEventListener("input",e=>{{
  const q=e.target.value.trim().toLowerCase();
  nd.select("circle,polygon,rect").attr("fill-opacity",d=>!q ? .85 : d.label.toLowerCase().includes(q)?1:.12);
  nd.select("text").attr("fill-opacity",d=>!q?1:d.label.toLowerCase().includes(q)?1:.15);
}});
document.getElementById("reset").addEventListener("click",()=>svg.transition().duration(500).call(zoom.transform,d3.zoomIdentity));
}})();
</script>
</body>
</html>"""

    output_path = os.path.abspath(output)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    click.echo(f"Dependency chart written to: {output_path}")
    click.echo(f"  {stats['facts']} facts · {stats['elements']} elements · {stats['projects']} projects · {stats['edges']} edges")


@cli.command("web")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--port", default=5000, show_default=True, type=int, help="Port to listen on.")
@click.option("--debug", is_flag=True, default=False, help="Enable Flask debug mode (auto-reload).")
@click.pass_context
def web_cmd(ctx, host, port, debug):
    """Launch the FactDB web UI (projects, elements, facts, review)."""
    try:
        from factdb.web.app import create_app
    except ImportError:
        click.echo(
            "Flask is required for the web UI.  Install it with:\n"
            "  pip install flask",
            err=True,
        )
        sys.exit(1)

    db_url = ctx.obj.get("db")
    app = create_app(db_url=db_url)
    click.echo(f"FactDB web UI → http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)


# ---------------------------------------------------------------------------
# seed-copilot
# ---------------------------------------------------------------------------


@cli.command("seed-copilot")
@click.option(
    "--count", "-n",
    default=0,
    show_default=True,
    help="Number of projects to generate (0 = infinite).",
)
@click.option(
    "--pause",
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
    help="Preview prompt without invoking Copilot or writing files.",
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
@click.option(
    "--projects-per-request",
    default=1,
    show_default=True,
    help="How many projects Copilot should return in one generation response.",
)
@click.option(
    "--single-request",
    is_flag=True,
    default=False,
    help="Use local intent so each iteration uses only one Copilot generation call.",
)
@click.option(
    "--convergence-only",
    is_flag=True,
    default=False,
    help="Print historical convergence report and exit (no seeding).",
)
@click.pass_context
def seed_copilot_cmd(ctx, count, pause, model, seed_every, dry_run, verbose,
                     timeout, projects_per_request, single_request, convergence_only):
    """
    Continuously prompt GitHub Copilot CLI to design new FactDB projects.

    Provides Copilot with the FULL knowledge map (facts grouped by domain,
    element capability index, relationship graph, coverage gaps) so it can
    reuse existing building blocks and target knowledge gaps intelligently.

    Tracks convergence metrics per iteration in data/convergence.jsonl.
    The convergence score measures DB saturation on a 0–1 scale:
    reuse rate, novelty decay, domain/category coverage, graph density.

    Requires: ``gh copilot`` CLI installed and authenticated.

    Examples::

        factdb seed-copilot                    # run forever
        factdb seed-copilot --count 5          # generate 5 projects then stop
        factdb seed-copilot --dry-run          # preview prompts only
        factdb seed-copilot --model gpt-5.2 --count 10
        factdb seed-copilot --projects-per-request 3 --single-request
        factdb seed-copilot --convergence-only # show convergence report
    """
    import importlib.util
    import pathlib
    import sys as _sys

    seeder_path = (
        pathlib.Path(__file__).parent.parent / "scripts" / "copilot_seeder.py"
    )
    spec = importlib.util.spec_from_file_location("copilot_seeder", seeder_path)
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec so @dataclass resolves __module__
    _sys.modules.setdefault("copilot_seeder", mod)
    spec.loader.exec_module(mod)

    args = []
    if count:
        args += ["--count", str(count)]
    if pause != 5:
        args += ["--pause", str(pause)]
    if model:
        args += ["--model", model]
    if seed_every != 1:
        args += ["--seed-every", str(seed_every)]
    if timeout != 300:
        args += ["--timeout", str(timeout)]
    if projects_per_request != 1:
        args += ["--projects-per-request", str(projects_per_request)]
    if dry_run:
        args.append("--dry-run")
    if verbose:
        args.append("--verbose")
    if single_request:
        args.append("--single-request")
    if convergence_only:
        args.append("--convergence-only")

    mod.main.main(args, standalone_mode=False)


if __name__ == "__main__":
    cli()
