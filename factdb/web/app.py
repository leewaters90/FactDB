"""
FactDB web UI — Flask application.

Provides a read/browse/review interface for Projects, DesignElements,
and their fact dependencies.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timezone

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import Session

from factdb.database import get_session_factory, init_db
from factdb.models import EngineeringDomain, Fact, FactRelationship
from factdb.project_models import ComponentCategory, DesignElement, Project, ProjectStatus
from factdb.project_repository import ProjectRepository


def _parse_date(value: str | None) -> datetime | None:
    """Parse an ISO date string (YYYY-MM-DD) into a UTC-aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def create_app(db_url: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("FACTDB_SECRET_KEY", "factdb-dev-secret")

    resolved_url = db_url or os.environ.get("FACTDB_DATABASE_URL", "sqlite:///data/factdb.sqlite")

    # Ensure the database is initialised (no-op if tables already exist).
    init_db(resolved_url)
    session_factory = get_session_factory(resolved_url)

    def get_session() -> Session:
        return session_factory()

    # -----------------------------------------------------------------------
    # Context processor — inject enum lists for templates
    # -----------------------------------------------------------------------

    @app.context_processor
    def inject_globals():
        return {
            "ProjectStatus": ProjectStatus,
            "ComponentCategory": ComponentCategory,
            "EngineeringDomain": EngineeringDomain,
        }

    # -----------------------------------------------------------------------
    # Index — redirect to projects list
    # -----------------------------------------------------------------------

    @app.get("/")
    def index():
        return redirect(url_for("projects_list"))

    # -----------------------------------------------------------------------
    # Projects
    # -----------------------------------------------------------------------

    @app.get("/projects")
    def projects_list():
        session = get_session()
        try:
            repo = ProjectRepository(session)
            status_filter = request.args.get("status") or None
            domain_filter = request.args.get("domain") or None
            created_after_str = request.args.get("created_after") or None
            created_before_str = request.args.get("created_before") or None

            status_enum = ProjectStatus(status_filter) if status_filter else None
            created_after = _parse_date(created_after_str)
            created_before = _parse_date(created_before_str)

            projects = repo.list_projects(
                status=status_enum,
                domain=domain_filter,
                created_after=created_after,
                created_before=created_before,
                limit=200,
            )

            return render_template(
                "web/projects.html",
                projects=projects,
                status_filter=status_filter,
                domain_filter=domain_filter,
                created_after=created_after_str or "",
                created_before=created_before_str or "",
                statuses=[s.value for s in ProjectStatus],
                domains=[d.value for d in EngineeringDomain],
            )
        finally:
            session.close()

    @app.get("/projects/<project_id>")
    def project_detail(project_id: str):
        session = get_session()
        try:
            repo = ProjectRepository(session)
            project = repo.get_project(project_id)
            if project is None:
                abort(404)

            # Build dependency graph data for rendering
            elements = project.elements
            interactions = project.get_element_interactions()

            return render_template(
                "web/project_detail.html",
                project=project,
                elements=elements,
                interactions=interactions,
            )
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Design Elements
    # -----------------------------------------------------------------------

    @app.get("/elements")
    def elements_list():
        session = get_session()
        try:
            repo = ProjectRepository(session)
            category_filter = request.args.get("category") or None
            created_after_str = request.args.get("created_after") or None
            created_before_str = request.args.get("created_before") or None

            category_enum = ComponentCategory(category_filter) if category_filter else None
            created_after = _parse_date(created_after_str)
            created_before = _parse_date(created_before_str)

            elements = repo.list_design_elements(
                component_category=category_enum,
                created_after=created_after,
                created_before=created_before,
                limit=500,
            )

            return render_template(
                "web/elements.html",
                elements=elements,
                category_filter=category_filter,
                created_after=created_after_str or "",
                created_before=created_before_str or "",
                categories=[c.value for c in ComponentCategory],
            )
        finally:
            session.close()

    @app.get("/elements/<element_id>")
    def element_detail(element_id: str):
        session = get_session()
        try:
            repo = ProjectRepository(session)
            element = repo.get_design_element(element_id)
            if element is None:
                abort(404)
            projects = repo.get_projects_using_element(element_id)
            return render_template(
                "web/element_detail.html",
                element=element,
                projects=projects,
            )
        finally:
            session.close()

    @app.post("/elements/<element_id>/review")
    def element_review(element_id: str):
        """Submit or update verification notes for a design element."""
        session = get_session()
        try:
            repo = ProjectRepository(session)
            element = repo.get_design_element(element_id)
            if element is None:
                abort(404)

            notes = request.form.get("verification_notes", "").strip()
            element.verification_notes = notes or None
            session.commit()
            flash("Review notes saved.", "success")
        finally:
            session.close()
        return redirect(url_for("element_detail", element_id=element_id))

    # -----------------------------------------------------------------------
    # Facts
    # -----------------------------------------------------------------------

    @app.get("/facts")
    def facts_list():
        session = get_session()
        try:
            domain_filter = request.args.get("domain") or None
            q = request.args.get("q", "").strip()

            stmt = session.query(Fact).filter(Fact.is_active.is_(True))
            if domain_filter:
                stmt = stmt.filter(Fact.domain == domain_filter)
            if q:
                stmt = stmt.filter(Fact.title.ilike(f"%{q}%"))
            facts = stmt.order_by(Fact.domain, Fact.title).limit(300).all()

            return render_template(
                "web/facts.html",
                facts=facts,
                domain_filter=domain_filter,
                q=q,
                domains=[d.value for d in EngineeringDomain],
            )
        finally:
            session.close()

    @app.get("/facts/<fact_id>")
    def fact_detail(fact_id: str):
        session = get_session()
        try:
            fact = session.get(Fact, fact_id)
            if fact is None:
                abort(404)
            outgoing = (
                session.query(FactRelationship)
                .filter(FactRelationship.source_fact_id == fact_id)
                .all()
            )
            incoming = (
                session.query(FactRelationship)
                .filter(FactRelationship.target_fact_id == fact_id)
                .all()
            )
            return render_template(
                "web/fact_detail.html",
                fact=fact,
                outgoing=outgoing,
                incoming=incoming,
            )
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Dependency Chart
    # -----------------------------------------------------------------------

    @app.get("/chart")
    def dependency_chart():
        session = get_session()
        try:
            # --- Fetch all active facts and their relationships ---
            facts = (
                session.query(Fact)
                .filter(Fact.is_active.is_(True))
                .order_by(Fact.domain, Fact.title)
                .all()
            )
            relationships = session.query(FactRelationship).all()

            # --- Fetch design elements and projects ---
            repo = ProjectRepository(session)
            elements = repo.list_design_elements(limit=1000)
            projects = repo.list_projects(limit=500)

            # --- Build graph nodes ---
            nodes = []
            fact_id_set: set[str] = set()
            element_id_set: set[str] = set()

            for fact in facts:
                nodes.append({
                    "id": fact.id,
                    "label": fact.title,
                    "type": "fact",
                    "group": fact.domain,
                    "status": fact.status,
                    "url": url_for("fact_detail", fact_id=fact.id),
                })
                fact_id_set.add(fact.id)

            for el in elements:
                nodes.append({
                    "id": el.id,
                    "label": el.title,
                    "type": "element",
                    "group": el.component_category,
                    "url": url_for("element_detail", element_id=el.id),
                })
                element_id_set.add(el.id)

            for proj in projects:
                nodes.append({
                    "id": proj.id,
                    "label": proj.title,
                    "type": "project",
                    "group": proj.domain,
                    "status": proj.status,
                    "url": url_for("project_detail", project_id=proj.id),
                })

            # --- Build graph edges ---
            edges = []

            # Fact → Fact relationships
            for rel in relationships:
                if rel.source_fact_id in fact_id_set and rel.target_fact_id in fact_id_set:
                    edges.append({
                        "source": rel.source_fact_id,
                        "target": rel.target_fact_id,
                        "type": rel.relationship_type,
                        "weight": rel.weight or 1.0,
                    })

            # Element → Fact (supporting facts)
            for el in elements:
                for fact in el.supporting_facts:
                    if fact.id in fact_id_set:
                        edges.append({
                            "source": el.id,
                            "target": fact.id,
                            "type": "uses_fact",
                            "weight": 1.0,
                        })

            # Project → Element
            for proj in projects:
                for el in proj.elements:
                    if el.id in element_id_set:
                        edges.append({
                            "source": proj.id,
                            "target": el.id,
                            "type": "uses_element",
                            "weight": 1.0,
                        })
                # Project → Fact (direct supporting facts)
                for fact in proj.supporting_facts:
                    if fact.id in fact_id_set:
                        edges.append({
                            "source": proj.id,
                            "target": fact.id,
                            "type": "uses_fact",
                            "weight": 1.0,
                        })

            graph = {"nodes": nodes, "edges": edges}
            stats = {
                "facts": len(facts),
                "elements": len(elements),
                "projects": len(projects),
                "edges": len(edges),
            }

            return render_template("web/chart.html", graph=graph, stats=stats)
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Convergence Chart
    # -----------------------------------------------------------------------

    @app.get("/convergence")
    def convergence_chart():
        session = get_session()
        try:
            facts = (
                session.query(Fact)
                .filter(Fact.is_active.is_(True))
                .order_by(Fact.created_at)
                .all()
            )
            repo = ProjectRepository(session)
            elements = repo.list_design_elements(limit=2000)
            projects = repo.list_projects(limit=2000)

            def _bucket(dt) -> str:
                if dt is None:
                    return "unknown"
                return dt.strftime("%Y-%m-%d")

            # Collect all dates
            all_dates: set[str] = set()
            fact_counts: dict[str, int] = defaultdict(int)
            element_counts: dict[str, int] = defaultdict(int)
            project_counts: dict[str, int] = defaultdict(int)

            for f in facts:
                d = _bucket(f.created_at)
                fact_counts[d] += 1
                all_dates.add(d)
            for e in elements:
                d = _bucket(e.created_at)
                element_counts[d] += 1
                all_dates.add(d)
            for p in projects:
                d = _bucket(p.created_at)
                project_counts[d] += 1
                all_dates.add(d)

            all_dates.discard("unknown")
            sorted_dates = sorted(all_dates)

            # Build cumulative series
            cum_facts, cum_elements, cum_projects = [], [], []
            cf = ce = cp = 0
            for d in sorted_dates:
                cf += fact_counts.get(d, 0)
                ce += element_counts.get(d, 0)
                cp += project_counts.get(d, 0)
                cum_facts.append(cf)
                cum_elements.append(ce)
                cum_projects.append(cp)

            # Daily counts series
            daily_facts    = [fact_counts.get(d, 0)    for d in sorted_dates]
            daily_elements = [element_counts.get(d, 0) for d in sorted_dates]
            daily_projects = [project_counts.get(d, 0) for d in sorted_dates]

            chart_data = {
                "labels": sorted_dates,
                "cumulative": {
                    "facts":    cum_facts,
                    "elements": cum_elements,
                    "projects": cum_projects,
                },
                "daily": {
                    "facts":    daily_facts,
                    "elements": daily_elements,
                    "projects": daily_projects,
                },
            }
            stats = {
                "facts":    len(facts),
                "elements": len(elements),
                "projects": len(projects),
                "days":     len(sorted_dates),
            }

            return render_template("web/convergence.html", chart_data=chart_data, stats=stats)
        finally:
            session.close()

    return app
