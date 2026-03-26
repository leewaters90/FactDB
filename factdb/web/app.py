"""
FactDB web UI — Flask application.

Provides a read/browse/review interface for Projects, DesignElements,
and their fact dependencies.
"""

from __future__ import annotations

import os

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import Session

from factdb.database import get_session_factory, init_db
from factdb.models import EngineeringDomain, Fact, FactRelationship
from factdb.project_models import ComponentCategory, DesignElement, Project, ProjectStatus
from factdb.project_repository import ProjectRepository


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

            status_enum = ProjectStatus(status_filter) if status_filter else None
            projects = repo.list_projects(status=status_enum, domain=domain_filter, limit=200)

            return render_template(
                "web/projects.html",
                projects=projects,
                status_filter=status_filter,
                domain_filter=domain_filter,
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
            category_enum = ComponentCategory(category_filter) if category_filter else None
            elements = repo.list_design_elements(component_category=category_enum, limit=500)

            return render_template(
                "web/elements.html",
                elements=elements,
                category_filter=category_filter,
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

    return app
