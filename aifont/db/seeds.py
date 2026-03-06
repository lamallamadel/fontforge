"""Seed data for development and integration testing.

Run directly::

    python -m aifont.db.seeds

Or call :func:`seed_all` from inside a test fixture.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from aifont.db.models import (
    AgentRun,
    AgentRunStatus,
    AgentTask,
    AgentTaskStatus,
    AgentType,
    ExportFormat,
    ExportJob,
    ExportJobStatus,
    ExportTargetUse,
    Font,
    FontFileFormat,
    FontProject,
    FontStyle,
    Glyph,
    KernPair,
    ProjectStatus,
    User,
)

# ---------------------------------------------------------------------------
# Individual seed helpers
# ---------------------------------------------------------------------------


def seed_users(session: Session) -> List[User]:
    """Create a small set of test users."""
    users = [
        User(
            email="alice@example.com",
            username="alice",
            password_hash="$2b$12$placeholder_hash_alice",
            is_active=True,
        ),
        User(
            email="bob@example.com",
            username="bob",
            password_hash="$2b$12$placeholder_hash_bob",
            is_active=True,
        ),
        User(
            email="inactive@example.com",
            username="carol",
            password_hash="$2b$12$placeholder_hash_carol",
            is_active=False,
        ),
    ]
    session.add_all(users)
    session.flush()
    return users


def seed_projects(session: Session, users: List[User]) -> List[FontProject]:
    """Create sample font projects for the seed users."""
    projects = [
        FontProject(
            user_id=users[0].id,
            name="Modern Sans-Serif",
            description="A clean geometric sans-serif typeface.",
            status=ProjectStatus.IN_PROGRESS,
        ),
        FontProject(
            user_id=users[0].id,
            name="Display Serif",
            description="High-contrast serif for large display sizes.",
            status=ProjectStatus.DRAFT,
        ),
        FontProject(
            user_id=users[1].id,
            name="Mono Code",
            description="Fixed-width font optimised for code editors.",
            status=ProjectStatus.COMPLETED,
        ),
    ]
    session.add_all(projects)
    session.flush()
    return projects


def seed_fonts(session: Session, projects: List[FontProject]) -> List[Font]:
    """Create sample font records."""
    fonts = [
        Font(
            project_id=projects[0].id,
            name="ModernSans Regular",
            family_name="ModernSans",
            weight=400,
            style=FontStyle.NORMAL,
            file_format=FontFileFormat.OTF,
            glyph_count=256,
            unicode_coverage={"ranges": [[0x0020, 0x007E], [0x00A0, 0x00FF]]},
            metadata_={"designer": "Alice", "version": "1.0.0"},
        ),
        Font(
            project_id=projects[0].id,
            name="ModernSans Bold",
            family_name="ModernSans",
            weight=700,
            style=FontStyle.NORMAL,
            file_format=FontFileFormat.OTF,
            glyph_count=256,
            unicode_coverage={"ranges": [[0x0020, 0x007E]]},
            metadata_={"designer": "Alice", "version": "1.0.0"},
        ),
        Font(
            project_id=projects[2].id,
            name="MonoCode Regular",
            family_name="MonoCode",
            weight=400,
            style=FontStyle.NORMAL,
            file_format=FontFileFormat.TTF,
            glyph_count=512,
            unicode_coverage={"ranges": [[0x0020, 0x007E], [0x2500, 0x257F]]},
            metadata_={"designer": "Bob", "version": "2.1.0"},
        ),
    ]
    session.add_all(fonts)
    session.flush()
    return fonts


def seed_glyphs(session: Session, fonts: List[Font]) -> List[Glyph]:
    """Create a small set of glyphs for the first font."""
    basic_latin = [
        (0x0041, "A", 600),
        (0x0042, "B", 600),
        (0x0043, "C", 580),
        (0x0061, "a", 560),
        (0x0062, "b", 560),
        (0x0063, "c", 520),
        (0x0020, "space", 200),
    ]
    glyphs: List[Glyph] = []
    for codepoint, name, width in basic_latin:
        glyphs.append(
            Glyph(
                font_id=fonts[0].id,
                name=name,
                unicode_codepoint=codepoint,
                advance_width=width,
                left_bearing=20,
                right_bearing=20,
                contour_data={"curves": []},
                svg_data=f'<path d="M 0 0" id="{name}"/>',
            )
        )
    session.add_all(glyphs)
    session.flush()
    return glyphs


def seed_kern_pairs(session: Session, fonts: List[Font]) -> List[KernPair]:
    """Seed common kerning pairs for the first font."""
    pairs = [
        ("A", "V", -40),
        ("A", "W", -30),
        ("T", "a", -50),
        ("T", "o", -50),
        ("V", "A", -40),
        ("W", "A", -30),
    ]
    kern_pairs: List[KernPair] = []
    for left, right, value in pairs:
        kern_pairs.append(
            KernPair(
                font_id=fonts[0].id,
                left_glyph_name=left,
                right_glyph_name=right,
                value=value,
            )
        )
    session.add_all(kern_pairs)
    session.flush()
    return kern_pairs


def seed_agent_runs(
    session: Session, projects: List[FontProject]
) -> List[AgentRun]:
    """Create sample agent run records."""
    runs = [
        AgentRun(
            project_id=projects[0].id,
            prompt="Create a modern geometric sans-serif typeface with clean lines.",
            status=AgentRunStatus.COMPLETED,
            completed_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
        AgentRun(
            project_id=projects[0].id,
            prompt="Make the spacing tighter and increase contrast.",
            status=AgentRunStatus.RUNNING,
        ),
        AgentRun(
            project_id=projects[1].id,
            prompt="Generate a high-contrast display serif.",
            status=AgentRunStatus.PENDING,
        ),
    ]
    session.add_all(runs)
    session.flush()
    return runs


def seed_agent_tasks(
    session: Session, runs: List[AgentRun]
) -> List[AgentTask]:
    """Create sample agent tasks for the first completed run."""
    tasks = [
        AgentTask(
            run_id=runs[0].id,
            agent_type=AgentType.DESIGN,
            status=AgentTaskStatus.COMPLETED,
            input_data={"prompt": "geometric sans-serif"},
            output_data={"glyphs_generated": 26},
            confidence_score=0.92,
        ),
        AgentTask(
            run_id=runs[0].id,
            agent_type=AgentType.METRICS,
            status=AgentTaskStatus.COMPLETED,
            input_data={"target": "balanced"},
            output_data={"kern_pairs_set": 18, "spacing_adjusted": True},
            confidence_score=0.88,
        ),
        AgentTask(
            run_id=runs[0].id,
            agent_type=AgentType.QA,
            status=AgentTaskStatus.COMPLETED,
            input_data={},
            output_data={"issues_found": 0, "checks_passed": 12},
            confidence_score=1.0,
        ),
        AgentTask(
            run_id=runs[0].id,
            agent_type=AgentType.EXPORT,
            status=AgentTaskStatus.COMPLETED,
            input_data={"formats": ["otf", "woff2"]},
            output_data={"files": ["ModernSans-Regular.otf", "ModernSans-Regular.woff2"]},
            confidence_score=1.0,
        ),
    ]
    session.add_all(tasks)
    session.flush()
    return tasks


def seed_export_jobs(
    session: Session, fonts: List[Font]
) -> List[ExportJob]:
    """Create sample export job records."""
    jobs = [
        ExportJob(
            font_id=fonts[0].id,
            format=ExportFormat.OTF,
            target_use=ExportTargetUse.PRINT,
            output_path="/exports/ModernSans-Regular.otf",
            status=ExportJobStatus.COMPLETED,
            options={"hinting": True},
            completed_at=datetime(2025, 1, 15, 12, 5, 0, tzinfo=timezone.utc),
        ),
        ExportJob(
            font_id=fonts[0].id,
            format=ExportFormat.WOFF2,
            target_use=ExportTargetUse.WEB,
            output_path="/exports/ModernSans-Regular.woff2",
            status=ExportJobStatus.COMPLETED,
            options={"subset": "latin"},
            completed_at=datetime(2025, 1, 15, 12, 6, 0, tzinfo=timezone.utc),
        ),
        ExportJob(
            font_id=fonts[2].id,
            format=ExportFormat.TTF,
            target_use=ExportTargetUse.APP,
            output_path="/exports/MonoCode-Regular.ttf",
            status=ExportJobStatus.PENDING,
            options={"autohint": True},
        ),
    ]
    session.add_all(jobs)
    session.flush()
    return jobs


# ---------------------------------------------------------------------------
# Master seed function
# ---------------------------------------------------------------------------


def seed_all(session: Session) -> None:
    """Populate the database with a full set of test data.

    Safe to call multiple times inside a transactional test — wrap in a
    rolled-back transaction to keep the database clean between tests.
    """
    users = seed_users(session)
    projects = seed_projects(session, users)
    fonts = seed_fonts(session, projects)
    seed_glyphs(session, fonts)
    seed_kern_pairs(session, fonts)
    runs = seed_agent_runs(session, projects)
    seed_agent_tasks(session, runs)
    seed_export_jobs(session, fonts)
    session.commit()
    print("✓ Database seeded successfully.")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from aifont.db.database import SessionLocal

    with SessionLocal() as session:
        seed_all(session)
