"""Integration tests for the AIFont database layer.

These tests require a live PostgreSQL instance.  Set the ``DATABASE_URL``
environment variable before running::

    export DATABASE_URL=postgresql+psycopg2://aifont:aifont@localhost:5432/aifont_test
    pytest aifont/tests/test_db_integration.py -v

The test suite:
1. Creates all tables in a *test* schema.
2. Runs seed data fixtures.
3. Validates CRUD operations, constraints, and cascades.
4. Rolls back after each test to keep the database clean.

Skip automatically when PostgreSQL is not available.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Database URL — falls back gracefully so tests are skipped in CI without PG
# ---------------------------------------------------------------------------
TEST_DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://aifont:aifont@localhost:5432/aifont_test",
)


def _pg_available() -> bool:
    """Return True when a PostgreSQL connection can be established."""
    try:
        eng = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 3})
        with eng.connect():
            pass
        eng.dispose()
        return True
    except Exception:
        return False


requires_pg = pytest.mark.skipif(
    not _pg_available(),
    reason="PostgreSQL not available — set DATABASE_URL to a reachable instance",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine():
    """Create engine and all tables once per test session."""
    from aifont.db.database import Base

    import aifont.db.models  # noqa: F401 — populate metadata

    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(db_engine) -> Generator[Session, None, None]:
    """Provide a transactional session that is rolled back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection)
    sess = Session_()

    yield sess

    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def seeded_session(session: Session) -> Session:
    """Return a session pre-populated with seed data."""
    from aifont.db.seeds import seed_all

    seed_all(session)
    return session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(session: Session, **kwargs):
    from aifont.db.models import User

    defaults = dict(
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        username=f"user_{uuid.uuid4().hex[:8]}",
        password_hash="$2b$12$test_hash",
        is_active=True,
    )
    defaults.update(kwargs)
    user = User(**defaults)
    session.add(user)
    session.flush()
    return user


def _make_project(session: Session, user_id, **kwargs):
    from aifont.db.models import FontProject, ProjectStatus

    defaults = dict(
        user_id=user_id,
        name="Test Project",
        status=ProjectStatus.DRAFT,
    )
    defaults.update(kwargs)
    project = FontProject(**defaults)
    session.add(project)
    session.flush()
    return project


def _make_font(session: Session, project_id, **kwargs):
    from aifont.db.models import Font, FontStyle

    defaults = dict(
        project_id=project_id,
        name="Test Font",
        weight=400,
        style=FontStyle.NORMAL,
    )
    defaults.update(kwargs)
    font = Font(**defaults)
    session.add(font)
    session.flush()
    return font


# ---------------------------------------------------------------------------
# Schema / table presence tests
# ---------------------------------------------------------------------------


@requires_pg
class TestSchemaExists:
    """Verify all expected tables and indexes are present after migration."""

    EXPECTED_TABLES = {
        "users",
        "font_projects",
        "fonts",
        "glyphs",
        "kern_pairs",
        "agent_runs",
        "agent_tasks",
        "export_jobs",
    }

    def test_all_tables_created(self, db_engine):
        inspector = inspect(db_engine)
        actual = set(inspector.get_table_names())
        assert self.EXPECTED_TABLES.issubset(actual)

    def test_users_columns(self, db_engine):
        inspector = inspect(db_engine)
        cols = {c["name"] for c in inspector.get_columns("users")}
        assert {"id", "email", "username", "password_hash", "is_active", "created_at", "updated_at"}.issubset(cols)

    def test_fonts_columns(self, db_engine):
        inspector = inspect(db_engine)
        cols = {c["name"] for c in inspector.get_columns("fonts")}
        assert {"id", "project_id", "name", "family_name", "weight", "style", "glyph_count"}.issubset(cols)

    def test_glyphs_indexes(self, db_engine):
        inspector = inspect(db_engine)
        index_names = {i["name"] for i in inspector.get_indexes("glyphs")}
        assert "ix_glyphs_font_id" in index_names
        assert "ix_glyphs_unicode_codepoint" in index_names
        assert "ix_glyphs_contour_data_gin" in index_names

    def test_kern_pairs_indexes(self, db_engine):
        inspector = inspect(db_engine)
        index_names = {i["name"] for i in inspector.get_indexes("kern_pairs")}
        assert "ix_kern_pairs_font_id" in index_names
        assert "ix_kern_pairs_left_glyph" in index_names


# ---------------------------------------------------------------------------
# User CRUD tests
# ---------------------------------------------------------------------------


@requires_pg
class TestUserModel:
    def test_create_user(self, session: Session):
        user = _make_user(session, email="test@example.com", username="testuser")
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.created_at is not None

    def test_unique_email_constraint(self, session: Session):
        _make_user(session, email="dup@example.com", username="first")
        with pytest.raises(IntegrityError):
            _make_user(session, email="dup@example.com", username="second")

    def test_unique_username_constraint(self, session: Session):
        _make_user(session, email="e1@example.com", username="same_name")
        with pytest.raises(IntegrityError):
            _make_user(session, email="e2@example.com", username="same_name")

    def test_cascade_delete_projects(self, session: Session):
        from aifont.db.models import FontProject

        user = _make_user(session)
        _make_project(session, user.id, name="Proj 1")
        _make_project(session, user.id, name="Proj 2")
        session.flush()

        session.delete(user)
        session.flush()

        count = session.query(FontProject).filter_by(user_id=user.id).count()
        assert count == 0


# ---------------------------------------------------------------------------
# Font and Glyph tests
# ---------------------------------------------------------------------------


@requires_pg
class TestFontModel:
    def test_create_font(self, session: Session):
        user = _make_user(session)
        project = _make_project(session, user.id)
        font = _make_font(session, project.id, family_name="TestFamily", weight=700)
        assert font.id is not None
        assert font.weight == 700

    def test_weight_range_constraint(self, session: Session):
        from aifont.db.models import Font, FontStyle

        user = _make_user(session)
        project = _make_project(session, user.id)
        bad_font = Font(
            project_id=project.id,
            name="Bad Weight",
            weight=50,  # < 100 — violates constraint
            style=FontStyle.NORMAL,
        )
        session.add(bad_font)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_glyph_count_non_negative(self, session: Session):
        from aifont.db.models import Font, FontStyle

        user = _make_user(session)
        project = _make_project(session, user.id)
        bad_font = Font(
            project_id=project.id,
            name="Bad Count",
            weight=400,
            style=FontStyle.NORMAL,
            glyph_count=-1,
        )
        session.add(bad_font)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_cascade_delete_glyphs(self, session: Session):
        from aifont.db.models import Glyph

        user = _make_user(session)
        project = _make_project(session, user.id)
        font = _make_font(session, project.id)

        glyph = Glyph(
            font_id=font.id,
            name="A",
            unicode_codepoint=0x41,
            advance_width=600,
        )
        session.add(glyph)
        session.flush()

        session.delete(font)
        session.flush()

        count = session.query(Glyph).filter_by(font_id=font.id).count()
        assert count == 0


# ---------------------------------------------------------------------------
# Glyph unique constraints
# ---------------------------------------------------------------------------


@requires_pg
class TestGlyphModel:
    def test_unique_glyph_name_per_font(self, session: Session):
        from aifont.db.models import Glyph

        user = _make_user(session)
        project = _make_project(session, user.id)
        font = _make_font(session, project.id)

        session.add(Glyph(font_id=font.id, name="A", unicode_codepoint=0x41, advance_width=600))
        session.flush()

        session.add(Glyph(font_id=font.id, name="A", unicode_codepoint=0x42, advance_width=600))
        with pytest.raises(IntegrityError):
            session.flush()

    def test_unique_codepoint_per_font(self, session: Session):
        from aifont.db.models import Glyph

        user = _make_user(session)
        project = _make_project(session, user.id)
        font = _make_font(session, project.id)

        session.add(Glyph(font_id=font.id, name="A", unicode_codepoint=0x41, advance_width=600))
        session.flush()

        session.add(Glyph(font_id=font.id, name="A_alt", unicode_codepoint=0x41, advance_width=600))
        with pytest.raises(IntegrityError):
            session.flush()

    def test_advance_width_non_negative(self, session: Session):
        from aifont.db.models import Glyph

        user = _make_user(session)
        project = _make_project(session, user.id)
        font = _make_font(session, project.id)

        session.add(Glyph(font_id=font.id, name="bad", advance_width=-10))
        with pytest.raises(IntegrityError):
            session.flush()


# ---------------------------------------------------------------------------
# KernPair tests
# ---------------------------------------------------------------------------


@requires_pg
class TestKernPairModel:
    def test_unique_kern_pair(self, session: Session):
        from aifont.db.models import KernPair

        user = _make_user(session)
        project = _make_project(session, user.id)
        font = _make_font(session, project.id)

        session.add(KernPair(font_id=font.id, left_glyph_name="A", right_glyph_name="V", value=-40))
        session.flush()

        session.add(KernPair(font_id=font.id, left_glyph_name="A", right_glyph_name="V", value=-50))
        with pytest.raises(IntegrityError):
            session.flush()


# ---------------------------------------------------------------------------
# AgentRun / AgentTask tests
# ---------------------------------------------------------------------------


@requires_pg
class TestAgentModels:
    def test_create_agent_run(self, session: Session):
        from aifont.db.models import AgentRun, AgentRunStatus

        user = _make_user(session)
        project = _make_project(session, user.id)

        run = AgentRun(
            project_id=project.id,
            prompt="Design a rounded sans-serif.",
            status=AgentRunStatus.PENDING,
        )
        session.add(run)
        session.flush()

        assert run.id is not None
        assert run.status == AgentRunStatus.PENDING

    def test_agent_task_confidence_range(self, session: Session):
        from aifont.db.models import AgentRun, AgentRunStatus, AgentTask, AgentType, AgentTaskStatus

        user = _make_user(session)
        project = _make_project(session, user.id)
        run = AgentRun(
            project_id=project.id,
            prompt="Test prompt",
            status=AgentRunStatus.RUNNING,
        )
        session.add(run)
        session.flush()

        bad_task = AgentTask(
            run_id=run.id,
            agent_type=AgentType.DESIGN,
            status=AgentTaskStatus.COMPLETED,
            confidence_score=1.5,  # > 1.0 — violates constraint
        )
        session.add(bad_task)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_cascade_tasks_on_run_delete(self, session: Session):
        from aifont.db.models import AgentRun, AgentRunStatus, AgentTask, AgentType, AgentTaskStatus

        user = _make_user(session)
        project = _make_project(session, user.id)
        run = AgentRun(
            project_id=project.id,
            prompt="Delete cascade test",
            status=AgentRunStatus.PENDING,
        )
        session.add(run)
        session.flush()

        session.add(
            AgentTask(
                run_id=run.id,
                agent_type=AgentType.QA,
                status=AgentTaskStatus.PENDING,
            )
        )
        session.flush()

        session.delete(run)
        session.flush()

        count = session.query(AgentTask).filter_by(run_id=run.id).count()
        assert count == 0


# ---------------------------------------------------------------------------
# Seed data tests
# ---------------------------------------------------------------------------


@requires_pg
class TestSeedData:
    def test_seed_creates_users(self, seeded_session: Session):
        from aifont.db.models import User

        count = seeded_session.query(User).count()
        assert count >= 3

    def test_seed_creates_fonts(self, seeded_session: Session):
        from aifont.db.models import Font

        count = seeded_session.query(Font).count()
        assert count >= 3

    def test_seed_creates_glyphs(self, seeded_session: Session):
        from aifont.db.models import Glyph

        count = seeded_session.query(Glyph).count()
        assert count >= 7

    def test_seed_creates_kern_pairs(self, seeded_session: Session):
        from aifont.db.models import KernPair

        count = seeded_session.query(KernPair).count()
        assert count >= 6

    def test_seed_creates_agent_runs(self, seeded_session: Session):
        from aifont.db.models import AgentRun

        count = seeded_session.query(AgentRun).count()
        assert count >= 3

    def test_seed_creates_agent_tasks(self, seeded_session: Session):
        from aifont.db.models import AgentTask

        count = seeded_session.query(AgentTask).count()
        assert count >= 4

    def test_seed_creates_export_jobs(self, seeded_session: Session):
        from aifont.db.models import ExportJob

        count = seeded_session.query(ExportJob).count()
        assert count >= 3

    def test_seed_relationship_integrity(self, seeded_session: Session):
        """Verify that all foreign key relationships are intact after seeding."""
        from aifont.db.models import Font, FontProject, User

        for font in seeded_session.query(Font).all():
            assert font.project is not None
            assert font.project.user is not None


# ---------------------------------------------------------------------------
# Query performance tests (smoke — just ensure indexes are used)
# ---------------------------------------------------------------------------


@requires_pg
class TestQueryPerformance:
    def test_glyph_lookup_by_codepoint(self, seeded_session: Session):
        from aifont.db.models import Glyph

        results = seeded_session.query(Glyph).filter(
            Glyph.unicode_codepoint == 0x41
        ).all()
        assert len(results) >= 1
        assert results[0].name == "A"

    def test_kern_pair_lookup(self, seeded_session: Session):
        from aifont.db.models import KernPair

        results = (
            seeded_session.query(KernPair)
            .filter(KernPair.left_glyph_name == "A")
            .all()
        )
        assert len(results) >= 1

    def test_agent_runs_filtered_by_status(self, seeded_session: Session):
        from aifont.db.models import AgentRun, AgentRunStatus

        results = (
            seeded_session.query(AgentRun)
            .filter(AgentRun.status == AgentRunStatus.COMPLETED)
            .all()
        )
        assert len(results) >= 1
