"""Shared FastAPI dependency functions."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aifont.api.auth import get_current_user
from aifont.api.database import get_db
from aifont.api.models import User

# Typed aliases for cleaner function signatures
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
