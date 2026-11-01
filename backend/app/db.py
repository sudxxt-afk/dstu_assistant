from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Создать таблицы и засеять дефолты (звонки + конфиг)."""
    # Импорт моделей обязателен до create_all, чтобы они зарегистрировались.
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        # WAL — чтобы api и bot могли писать в одну базу из разных контейнеров.
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.run_sync(Base.metadata.create_all)

    from .seed import seed_defaults

    async with async_session() as session:
        await seed_defaults(session)
