from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import BellSchedule, Config, Exception as Exc, Lesson, Subject

WEEKDAY_RU = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье",
}


@dataclass
class ResolvedLesson:
    subject_id: int
    subject_name: str
    type: str
    pair_number: int
    start_time: str | None
    end_time: str | None
    room: str | None
    teacher: str | None
    status: str = "normal"  # normal / moved / added
    note: str | None = None


def _week_index(date: dt.date, cfg: Config) -> int:
    """Индекс учебной недели (0-based), выровненный по понедельнику.
    Чтобы чётность и номер были одинаковы для всех дней одной недели (Пн–Вс),
    даже если семестр начался в середине недели."""
    start_monday = cfg.semester_start - dt.timedelta(
        days=cfg.semester_start.isoweekday() - 1
    )
    date_monday = date - dt.timedelta(days=date.isoweekday() - 1)
    return (date_monday - start_monday).days // 7


def week_parity(date: dt.date, cfg: Config) -> str:
    """Вернёт 'odd' или 'even' для заданной даты относительно начала семестра."""
    same_as_first = _week_index(date, cfg) % 2 == 0
    first_is_odd = cfg.week1_is_odd
    is_odd = first_is_odd if same_as_first else (not first_is_odd)
    return "odd" if is_odd else "even"


def week_number(date: dt.date, cfg: Config) -> int:
    """Номер учебной недели (1-based)."""
    return _week_index(date, cfg) + 1


async def resolve_day(session: AsyncSession, date: dt.date) -> list[ResolvedLesson]:
    cfg = await session.get(Config, 1)
    if cfg is None:
        return []

    parity = week_parity(date, cfg)
    weekday = date.isoweekday()

    # Звонки
    bells = {
        b.pair_number: (b.start_time, b.end_time)
        for b in (await session.execute(select(BellSchedule))).scalars()
    }

    # Шаблоны пар на этот день недели и чётность
    lessons = (
        (
            await session.execute(
                select(Lesson)
                .options(selectinload(Lesson.subject))
                .where(Lesson.weekday == weekday)
                .where(Lesson.parity.in_(["every", parity]))
            )
        )
        .scalars()
        .all()
    )

    resolved: dict[int, ResolvedLesson] = {}
    for ls in lessons:
        resolved[ls.id] = ResolvedLesson(
            subject_id=ls.subject_id,
            subject_name=ls.subject.name,
            type=ls.type,
            pair_number=ls.pair_number,
            start_time=bells.get(ls.pair_number, (None, None))[0],
            end_time=bells.get(ls.pair_number, (None, None))[1],
            room=ls.room,
            teacher=ls.teacher_override or ls.subject.teacher,
        )

    # Исключения на дату
    exceptions = (
        (await session.execute(select(Exc).where(Exc.date == date))).scalars().all()
    )
    added: list[ResolvedLesson] = []
    for ex in exceptions:
        if ex.kind == "cancel" and ex.lesson_id in resolved:
            resolved.pop(ex.lesson_id, None)
        elif ex.kind == "move" and ex.lesson_id in resolved:
            r = resolved[ex.lesson_id]
            if ex.new_pair_number is not None:
                r.pair_number = ex.new_pair_number
                r.start_time, r.end_time = bells.get(
                    ex.new_pair_number, (None, None)
                )
            if ex.new_room is not None:
                r.room = ex.new_room
            r.status = "moved"
            r.note = ex.note
        elif ex.kind == "add" and ex.subject_id is not None:
            subj = await session.get(Subject, ex.subject_id)
            pair = ex.new_pair_number or 1
            added.append(
                ResolvedLesson(
                    subject_id=ex.subject_id,
                    subject_name=subj.name if subj else "?",
                    type=ex.type or "пара",
                    pair_number=pair,
                    start_time=bells.get(pair, (None, None))[0],
                    end_time=bells.get(pair, (None, None))[1],
                    room=ex.new_room,
                    teacher=subj.teacher if subj else None,
                    status="added",
                    note=ex.note,
                )
            )

    result = list(resolved.values()) + added
    result.sort(key=lambda r: r.pair_number)
    return result
