"""Initial AIFont database schema.

Creates all core tables with constraints, foreign keys, and optimised indexes.

Tables
------
- users
- font_projects
- fonts
- glyphs
- kern_pairs
- agent_runs
- agent_tasks
- export_jobs

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enum types
    # ------------------------------------------------------------------
    project_status_enum = postgresql.ENUM(
        "draft",
        "in_progress",
        "completed",
        "archived",
        name="project_status_enum",
        create_type=False,
    )
    font_style_enum = postgresql.ENUM(
        "normal",
        "italic",
        "oblique",
        name="font_style_enum",
        create_type=False,
    )
    font_file_format_enum = postgresql.ENUM(
        "otf",
        "ttf",
        "woff2",
        "ufo",
        "sfd",
        name="font_file_format_enum",
        create_type=False,
    )
    agent_run_status_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="agent_run_status_enum",
        create_type=False,
    )
    agent_type_enum = postgresql.ENUM(
        "design",
        "style",
        "metrics",
        "qa",
        "export",
        "orchestrator",
        name="agent_type_enum",
        create_type=False,
    )
    agent_task_status_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        "skipped",
        name="agent_task_status_enum",
        create_type=False,
    )
    export_format_enum = postgresql.ENUM(
        "otf",
        "ttf",
        "woff2",
        "variable",
        name="export_format_enum",
        create_type=False,
    )
    export_target_use_enum = postgresql.ENUM(
        "web",
        "print",
        "app",
        name="export_target_use_enum",
        create_type=False,
    )
    export_job_status_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="export_job_status_enum",
        create_type=False,
    )

    # Create ENUMs before the tables that reference them
    for enum_type in (
        project_status_enum,
        font_style_enum,
        font_file_format_enum,
        agent_run_status_enum,
        agent_type_enum,
        agent_task_status_enum,
        export_format_enum,
        export_target_use_enum,
        export_job_status_enum,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(username) >= 3", name="ck_users_username_min_len"),
        sa.CheckConstraint(
            "email ~* '^[^@]+@[^@]+\\.[^@]+$'", name="ck_users_email_format"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    # ------------------------------------------------------------------
    # font_projects
    # ------------------------------------------------------------------
    op.create_table(
        "font_projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "status",
            project_status_enum,
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(name) >= 1", name="ck_font_projects_name_not_empty"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_font_projects_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_font_projects_user_id", "font_projects", ["user_id"], unique=False
    )
    op.create_index(
        "ix_font_projects_status", "font_projects", ["status"], unique=False
    )

    # ------------------------------------------------------------------
    # fonts
    # ------------------------------------------------------------------
    op.create_table(
        "fonts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("family_name", sa.String(length=255)),
        sa.Column("weight", sa.Integer(), server_default="400"),
        sa.Column(
            "style",
            font_style_enum,
            server_default="normal",
            nullable=False,
        ),
        sa.Column("file_path", sa.Text()),
        sa.Column("file_format", font_file_format_enum),
        sa.Column("glyph_count", sa.Integer(), server_default="0"),
        sa.Column("unicode_coverage", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "weight >= 100 AND weight <= 900", name="ck_fonts_weight_range"
        ),
        sa.CheckConstraint(
            "glyph_count >= 0", name="ck_fonts_glyph_count_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["font_projects.id"],
            name="fk_fonts_project_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fonts_project_id", "fonts", ["project_id"], unique=False)
    op.create_index("ix_fonts_family_name", "fonts", ["family_name"], unique=False)

    # ------------------------------------------------------------------
    # glyphs
    # ------------------------------------------------------------------
    op.create_table(
        "glyphs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "font_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unicode_codepoint", sa.Integer()),
        sa.Column("advance_width", sa.Integer(), server_default="0"),
        sa.Column("left_bearing", sa.Integer(), server_default="0"),
        sa.Column("right_bearing", sa.Integer(), server_default="0"),
        sa.Column("contour_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("svg_data", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "advance_width >= 0", name="ck_glyphs_advance_width_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["font_id"],
            ["fonts.id"],
            name="fk_glyphs_font_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("font_id", "name", name="uq_glyphs_font_name"),
        sa.UniqueConstraint(
            "font_id", "unicode_codepoint", name="uq_glyphs_font_codepoint"
        ),
    )
    op.create_index("ix_glyphs_font_id", "glyphs", ["font_id"], unique=False)
    op.create_index(
        "ix_glyphs_unicode_codepoint",
        "glyphs",
        ["unicode_codepoint"],
        unique=False,
    )
    op.create_index(
        "ix_glyphs_contour_data_gin",
        "glyphs",
        ["contour_data"],
        unique=False,
        postgresql_using="gin",
    )

    # ------------------------------------------------------------------
    # kern_pairs
    # ------------------------------------------------------------------
    op.create_table(
        "kern_pairs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "font_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("left_glyph_name", sa.String(length=255), nullable=False),
        sa.Column("right_glyph_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["font_id"],
            ["fonts.id"],
            name="fk_kern_pairs_font_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "font_id",
            "left_glyph_name",
            "right_glyph_name",
            name="uq_kern_pairs_font_left_right",
        ),
    )
    op.create_index("ix_kern_pairs_font_id", "kern_pairs", ["font_id"], unique=False)
    op.create_index(
        "ix_kern_pairs_left_glyph",
        "kern_pairs",
        ["font_id", "left_glyph_name"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # agent_runs
    # ------------------------------------------------------------------
    op.create_table(
        "agent_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "status",
            agent_run_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("result_font_id", postgresql.UUID(as_uuid=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["font_projects.id"],
            name="fk_agent_runs_project_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["result_font_id"],
            ["fonts.id"],
            name="fk_agent_runs_result_font_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_project_id", "agent_runs", ["project_id"], unique=False)
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"], unique=False)

    # ------------------------------------------------------------------
    # agent_tasks
    # ------------------------------------------------------------------
    op.create_table(
        "agent_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("agent_type", agent_type_enum, nullable=False),
        sa.Column(
            "status",
            agent_task_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("error_message", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)",
            name="ck_agent_tasks_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["agent_runs.id"],
            name="fk_agent_tasks_run_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tasks_run_id", "agent_tasks", ["run_id"], unique=False)
    op.create_index(
        "ix_agent_tasks_agent_type", "agent_tasks", ["agent_type"], unique=False
    )
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"], unique=False)

    # ------------------------------------------------------------------
    # export_jobs
    # ------------------------------------------------------------------
    op.create_table(
        "export_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "font_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("format", export_format_enum, nullable=False),
        sa.Column(
            "target_use",
            export_target_use_enum,
            server_default="web",
            nullable=False,
        ),
        sa.Column("output_path", sa.Text()),
        sa.Column(
            "status",
            export_job_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["font_id"],
            ["fonts.id"],
            name="fk_export_jobs_font_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_font_id", "export_jobs", ["font_id"], unique=False)
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"], unique=False)
    op.create_index("ix_export_jobs_format", "export_jobs", ["format"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("export_jobs")
    op.drop_table("agent_tasks")
    op.drop_table("agent_runs")
    op.drop_table("kern_pairs")
    op.drop_table("glyphs")
    op.drop_table("fonts")
    op.drop_table("font_projects")
    op.drop_table("users")

    # Drop PostgreSQL enum types
    for enum_name in (
        "export_job_status_enum",
        "export_target_use_enum",
        "export_format_enum",
        "agent_task_status_enum",
        "agent_type_enum",
        "agent_run_status_enum",
        "font_file_format_enum",
        "font_style_enum",
        "project_status_enum",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
