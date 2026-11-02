from __future__ import annotations

from sqlalchemy import event
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


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """Применяется к каждому новому соединению SQLite."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")       # api и bot пишут в одну базу
    cur.execute("PRAGMA synchronous=NORMAL")     # быстрее записи, с WAL безопасно
    cur.execute("PRAGMA temp_store=MEMORY")      # временные данные в RAM
    cur.execute("PRAGMA busy_timeout=5000")      # ждать блокировку, а не падать
    cur.execute("PRAGMA cache_size=-8000")       # ~8 МБ кеш страниц
    cur.close()


async def init_db() -> None:
    """Создать таблицы и засеять дефолты (звонки + конфиг)."""
    # Импорт моделей обязателен до create_all, чтобы они зарегистрировались.
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Индексы под частые выборки (по дню недели, дате исключений, статусу задач).
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_lesson_weekday ON lesson(weekday)"
        )
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_exception_date ON exception(date)"
        )
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_task_done ON task(done)"
        )

    from .seed import seed_defaults

    async with async_session() as session:
        await seed_defaults(session)
