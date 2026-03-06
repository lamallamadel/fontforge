"""SQLAlchemy ORM models for AIFont.

Schema overview
---------------
User            — registered accounts
FontProject     — a user's font design project
Font            — a specific font file / version inside a project
Glyph           — individual glyph within a font
KernPair        — kerning pair stored for a font
AgentRun        — one full AI-agent pipeline execution
AgentTask       — a single agent's work within a run
ExportJob       — a font-export operation

All primary keys are UUIDs generated server-side by PostgreSQL so that rows
can be created off-line and synced later without collision.
"""

import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from aifont.db.database import Base

# ---------------------------------------------------------------------------
# Enum types — stored as PostgreSQL native ENUMs
# ---------------------------------------------------------------------------


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class FontStyle(str, enum.Enum):
    NORMAL = "normal"
    ITALIC = "italic"
    OBLIQUE = "oblique"


class FontFileFormat(str, enum.Enum):
    OTF = "otf"
    TTF = "ttf"
    WOFF2 = "woff2"
    UFO = "ufo"
    SFD = "sfd"


class AgentRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, enum.Enum):
    DESIGN = "design"
    STYLE = "style"
    METRICS = "metrics"
    QA = "qa"
    EXPORT = "export"
    ORCHESTRATOR = "orchestrator"


class AgentTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExportFormat(str, enum.Enum):
    OTF = "otf"
    TTF = "ttf"
    WOFF2 = "woff2"
    VARIABLE = "variable"


class ExportTargetUse(str, enum.Enum):
    WEB = "web"
    PRINT = "print"
    APP = "app"


class ExportJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Mixin: auto-managed timestamps
# ---------------------------------------------------------------------------


class TimestampMixin:
    """Add ``created_at`` / ``updated_at`` columns to a model."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(TimestampMixin, Base):
    """Registered AIFont user account."""

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email = Column(String(254), unique=True, nullable=False)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")

    # Relationships
    projects = relationship("FontProject", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="ck_users_username_min_len"),
        CheckConstraint("email ~* '^[^@]+@[^@]+\\.[^@]+$'", name="ck_users_email_format"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


class FontProject(TimestampMixin, Base):
    """A user's font design project — container for one or more font versions."""

    __tablename__ = "font_projects"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        Enum(ProjectStatus, name="project_status_enum"),
        nullable=False,
        server_default=ProjectStatus.DRAFT.value,
    )

    # Relationships
    user = relationship("User", back_populates="projects")
    fonts = relationship("Font", back_populates="project", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_font_projects_user_id", "user_id"),
        Index("ix_font_projects_status", "status"),
        CheckConstraint("char_length(name) >= 1", name="ck_font_projects_name_not_empty"),
    )

    def __repr__(self) -> str:
        return f"<FontProject id={self.id} name={self.name!r}>"


class Font(TimestampMixin, Base):
    """A specific font file / version inside a :class:`FontProject`."""

    __tablename__ = "fonts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("font_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    family_name = Column(String(255))
    weight = Column(Integer, server_default="400")
    style = Column(
        Enum(FontStyle, name="font_style_enum"),
        nullable=False,
        server_default=FontStyle.NORMAL.value,
    )
    file_path = Column(Text)
    file_format = Column(Enum(FontFileFormat, name="font_file_format_enum"))
    glyph_count = Column(Integer, server_default="0")
    unicode_coverage = Column(JSONB)  # e.g. {"ranges": [[0x0020, 0x007F]]}
    metadata_ = Column("metadata", JSONB)  # arbitrary font metadata

    # Relationships
    project = relationship("FontProject", back_populates="fonts")
    glyphs = relationship("Glyph", back_populates="font", cascade="all, delete-orphan")
    kern_pairs = relationship("KernPair", back_populates="font", cascade="all, delete-orphan")
    export_jobs = relationship("ExportJob", back_populates="font", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_fonts_project_id", "project_id"),
        Index("ix_fonts_family_name", "family_name"),
        CheckConstraint("weight >= 100 AND weight <= 900", name="ck_fonts_weight_range"),
        CheckConstraint("glyph_count >= 0", name="ck_fonts_glyph_count_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Font id={self.id} name={self.name!r} weight={self.weight}>"


class Glyph(TimestampMixin, Base):
    """An individual glyph within a :class:`Font`."""

    __tablename__ = "glyphs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    font_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fonts.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    unicode_codepoint = Column(Integer)  # NULL for non-encoded glyphs
    advance_width = Column(Integer, server_default="0")
    left_bearing = Column(Integer, server_default="0")
    right_bearing = Column(Integer, server_default="0")
    contour_data = Column(JSONB)  # serialised Bézier path data
    svg_data = Column(Text)  # raw SVG path (<path d="..."/>)

    # Relationships
    font = relationship("Font", back_populates="glyphs")

    __table_args__ = (
        UniqueConstraint("font_id", "name", name="uq_glyphs_font_name"),
        UniqueConstraint(
            "font_id",
            "unicode_codepoint",
            name="uq_glyphs_font_codepoint",
        ),
        Index("ix_glyphs_font_id", "font_id"),
        Index("ix_glyphs_unicode_codepoint", "unicode_codepoint"),
        # GIN index on JSONB for fast path queries
        Index(
            "ix_glyphs_contour_data_gin",
            "contour_data",
            postgresql_using="gin",
        ),
        CheckConstraint("advance_width >= 0", name="ck_glyphs_advance_width_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Glyph id={self.id} name={self.name!r} cp={self.unicode_codepoint}>"


class KernPair(TimestampMixin, Base):
    """A kerning pair (left glyph, right glyph) and its adjustment value."""

    __tablename__ = "kern_pairs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    font_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fonts.id", ondelete="CASCADE"),
        nullable=False,
    )
    left_glyph_name = Column(String(255), nullable=False)
    right_glyph_name = Column(String(255), nullable=False)
    value = Column(Integer, nullable=False, server_default="0")

    # Relationships
    font = relationship("Font", back_populates="kern_pairs")

    __table_args__ = (
        UniqueConstraint(
            "font_id",
            "left_glyph_name",
            "right_glyph_name",
            name="uq_kern_pairs_font_left_right",
        ),
        Index("ix_kern_pairs_font_id", "font_id"),
        Index("ix_kern_pairs_left_glyph", "font_id", "left_glyph_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<KernPair id={self.id} "
            f"{self.left_glyph_name!r}+{self.right_glyph_name!r}={self.value}>"
        )


class AgentRun(TimestampMixin, Base):
    """One full AI-agent pipeline execution triggered by a user prompt."""

    __tablename__ = "agent_runs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("font_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    prompt = Column(Text, nullable=False)
    status = Column(
        Enum(AgentRunStatus, name="agent_run_status_enum"),
        nullable=False,
        server_default=AgentRunStatus.PENDING.value,
    )
    result_font_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fonts.id", ondelete="SET NULL"),
    )
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    project = relationship("FontProject", back_populates="agent_runs")
    tasks = relationship("AgentTask", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agent_runs_project_id", "project_id"),
        Index("ix_agent_runs_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id} status={self.status}>"


class AgentTask(TimestampMixin, Base):
    """A single agent's work within an :class:`AgentRun`."""

    __tablename__ = "agent_tasks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_type = Column(
        Enum(AgentType, name="agent_type_enum"),
        nullable=False,
    )
    status = Column(
        Enum(AgentTaskStatus, name="agent_task_status_enum"),
        nullable=False,
        server_default=AgentTaskStatus.PENDING.value,
    )
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    confidence_score = Column(Float)
    error_message = Column(Text)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    run = relationship("AgentRun", back_populates="tasks")

    __table_args__ = (
        Index("ix_agent_tasks_run_id", "run_id"),
        Index("ix_agent_tasks_agent_type", "agent_type"),
        Index("ix_agent_tasks_status", "status"),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)",
            name="ck_agent_tasks_confidence_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<AgentTask id={self.id} type={self.agent_type} status={self.status}>"


class ExportJob(TimestampMixin, Base):
    """A font export operation — tracks format conversion and delivery."""

    __tablename__ = "export_jobs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    font_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fonts.id", ondelete="CASCADE"),
        nullable=False,
    )
    format = Column(
        Enum(ExportFormat, name="export_format_enum"),
        nullable=False,
    )
    target_use = Column(
        Enum(ExportTargetUse, name="export_target_use_enum"),
        nullable=False,
        server_default=ExportTargetUse.WEB.value,
    )
    output_path = Column(Text)
    status = Column(
        Enum(ExportJobStatus, name="export_job_status_enum"),
        nullable=False,
        server_default=ExportJobStatus.PENDING.value,
    )
    options = Column(JSONB)  # format-specific options (hinting, subsetting, …)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    font = relationship("Font", back_populates="export_jobs")

    __table_args__ = (
        Index("ix_export_jobs_font_id", "font_id"),
        Index("ix_export_jobs_status", "status"),
        Index("ix_export_jobs_format", "format"),
    )

    def __repr__(self) -> str:
        return f"<ExportJob id={self.id} format={self.format} status={self.status}>"
