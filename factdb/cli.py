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
@click.pass_context
def search(ctx, query, domain, category, level, status, tags, limit, as_json):
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
        )

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


if __name__ == "__main__":
    cli()
