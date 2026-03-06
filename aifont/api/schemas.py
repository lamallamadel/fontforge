"""Pydantic schemas for request validation and response serialisation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# ------------------------------------------------------------------ #
# Auth                                                                 #
# ------------------------------------------------------------------ #


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


# ------------------------------------------------------------------ #
# Font                                                                 #
# ------------------------------------------------------------------ #


class FontCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    family: str | None = Field(None, max_length=256)
    style: str | None = Field(None, max_length=128)
    version: str | None = Field(None, max_length=64)
    description: str | None = Field(None, max_length=4096)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class FontUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    family: str | None = Field(None, max_length=256)
    style: str | None = Field(None, max_length=128)
    version: str | None = Field(None, max_length=64)
    description: str | None = Field(None, max_length=4096)


class FontRead(BaseModel):
    id: uuid.UUID
    name: str
    family: str | None
    style: str | None
    version: str | None
    description: str | None
    file_path: str | None
    glyph_count: int | None
    created_at: datetime
    updated_at: datetime
    owner_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class FontList(BaseModel):
    items: list[FontRead]
    total: int
    page: int
    page_size: int


# ------------------------------------------------------------------ #
# Generation                                                           #
# ------------------------------------------------------------------ #


class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2048)
    font_id: uuid.UUID | None = None
    style_hints: dict | None = None


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


# ------------------------------------------------------------------ #
# Agent                                                                #
# ------------------------------------------------------------------ #


class AgentRunRequest(BaseModel):
    agent: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1, max_length=4096)
    font_id: uuid.UUID | None = None
    parameters: dict | None = None

    @field_validator("agent")
    @classmethod
    def _agent_valid(cls, v: str) -> str:
        allowed = {"design", "style", "metrics", "qa", "export", "orchestrator"}
        if v not in allowed:
            raise ValueError(f"agent must be one of: {', '.join(sorted(allowed))}")
        return v


class AgentRunResponse(BaseModel):
    task_id: str
    agent: str
    status: str


# ------------------------------------------------------------------ #
# Analysis                                                             #
# ------------------------------------------------------------------ #


class AnalysisResultRead(BaseModel):
    id: uuid.UUID
    font_id: uuid.UUID
    task_id: str | None
    status: str
    result: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
