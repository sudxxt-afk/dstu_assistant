from __future__ import annotations

from typing import AsyncIterator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import async_session


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


async def require_token(x_api_token: str = Header(default="")) -> None:
    if not settings.api_token or x_api_token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий X-API-Token",
        )
