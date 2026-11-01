from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BellSchedule, Config

# Типовое расписание звонков (пары по 1:30). Отредактируешь под ДГТУ.
DEFAULT_BELLS = [
    (1, "08:00", "09:30"),
    (2, "09:40", "11:10"),
    (3, "11:20", "12:50"),
    (4, "13:20", "14:50"),
    (5, "15:00", "16:30"),
    (6, "16:40", "18:10"),
    (7, "18:15", "19:45"),
    (8, "19:50", "21:20"),
]


async def seed_defaults(session: AsyncSession) -> None:
    # Конфиг
    cfg = await session.get(Config, 1)
    if cfg is None:
        today = dt.date.today()
        # Разумные дефолты осеннего семестра; поменяешь через API/веб.
        start = dt.date(today.year, 9, 1)
        if today.month < 9:  # весенний семестр
            start = dt.date(today.year, 2, 9)
        session.add(
            Config(
                id=1,
                semester_start=start,
                semester_end=start + dt.timedelta(weeks=18),
                week1_is_odd=True,
                reminder_minutes=10,
                morning_brief_time="07:30",
            )
        )

    # Звонки
    existing = (await session.execute(select(BellSchedule.pair_number))).scalars().all()
    if not existing:
        for num, start_t, end_t in DEFAULT_BELLS:
            session.add(
                BellSchedule(pair_number=num, start_time=start_t, end_time=end_t)
            )

    await session.commit()
