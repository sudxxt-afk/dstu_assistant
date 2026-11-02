from __future__ import annotations

import datetime as dt
import time
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


# ---------------- Кеш редко меняющихся данных (конфиг, звонки) ----------------
_CACHE_TTL = 60.0  # сек; изменения через API подхватятся не позже чем за минуту
_cfg_cache: dict = {"obj": None, "ts": -1e9}
_bells_cache: dict = {"data": None, "ts": -1e9}


async def get_config(session: AsyncSession) -> Config | None:
    now = time.monotonic()
    if _cfg_cache["obj"] is None or now - _cfg_cache["ts"] > _CACHE_TTL:
        _cfg_cache["obj"] = await session.get(Config, 1)
        _cfg_cache["ts"] = now
    return _cfg_cache["obj"]


async def get_bells(session: AsyncSession) -> dict[int, tuple[str, str]]:
    now = time.monotonic()
    if _bells_cache["data"] is None or now - _bells_cache["ts"] > _CACHE_TTL:
        rows = (await session.execute(select(BellSchedule))).scalars().all()
        _bells_cache["data"] = {b.pair_number: (b.start_time, b.end_time) for b in rows}
        _bells_cache["ts"] = now
    return _bells_cache["data"]


def invalidate_cache() -> None:
    _cfg_cache["ts"] = -1e9
    _bells_cache["ts"] = -1e9


# ---------------- Неделя / чётность ----------------
def _week_index(date: dt.date, cfg: Config) -> int:
    """Индекс учебной недели (0-based), выровненный по понедельнику."""
    start_monday = cfg.semester_start - dt.timedelta(
        days=cfg.semester_start.isoweekday() - 1
    )
    date_monday = date - dt.timedelta(days=date.isoweekday() - 1)
    return (date_monday - start_monday).days // 7


def week_parity(date: dt.date, cfg: Config) -> str:
    same_as_first = _week_index(date, cfg) % 2 == 0
    first_is_odd = cfg.week1_is_odd
    is_odd = first_is_odd if same_as_first else (not first_is_odd)
    return "odd" if is_odd else "even"


def week_number(date: dt.date, cfg: Config) -> int:
    return _week_index(date, cfg) + 1


# ---------------- Сборка дня (чистая функция) ----------------
def _build_day(
    bells: dict[int, tuple[str, str]],
    lessons: list[Lesson],
    exceptions: list[Exc],
    subjects_map: dict[int, Subject] | None = None,
) -> list[ResolvedLesson]:
    resolved: dict[int, ResolvedLesson] = {}
    for ls in lessons:
        st, en = bells.get(ls.pair_number, (None, None))
        resolved[ls.id] = ResolvedLesson(
            subject_id=ls.subject_id,
            subject_name=ls.subject.name,
            type=ls.type,
            pair_number=ls.pair_number,
            start_time=st,
            end_time=en,
            room=ls.room,
            teacher=ls.teacher_override or ls.subject.teacher,
        )

    added: list[ResolvedLesson] = []
    for ex in exceptions:
        if ex.kind == "cancel" and ex.lesson_id in resolved:
            resolved.pop(ex.lesson_id, None)
        elif ex.kind == "move" and ex.lesson_id in resolved:
            r = resolved[ex.lesson_id]
            if ex.new_pair_number is not None:
                r.pair_number = ex.new_pair_number
                r.start_time, r.end_time = bells.get(ex.new_pair_number, (None, None))
            if ex.new_room is not None:
                r.room = ex.new_room
            r.status = "moved"
            r.note = ex.note
        elif ex.kind == "add" and ex.subject_id is not None:
            subj = (subjects_map or {}).get(ex.subject_id)
            pair = ex.new_pair_number or 1
            st, en = bells.get(pair, (None, None))
            added.append(
                ResolvedLesson(
                    subject_id=ex.subject_id,
                    subject_name=subj.name if subj else "?",
                    type=ex.type or "пара",
                    pair_number=pair,
                    start_time=st,
                    end_time=en,
                    room=ex.new_room,
                    teacher=subj.teacher if subj else None,
                    status="added",
                    note=ex.note,
                )
            )

    result = list(resolved.values()) + added
    result.sort(key=lambda r: r.pair_number)
    return result


async def _subjects_map_if_needed(
    session: AsyncSession, exceptions: list[Exc]
) -> dict[int, Subject] | None:
    if not any(e.kind == "add" for e in exceptions):
        return None
    rows = (await session.execute(select(Subject))).scalars().all()
    return {s.id: s for s in rows}


# ---------------- Публичные функции ----------------
async def resolve_day(session: AsyncSession, date: dt.date) -> list[ResolvedLesson]:
    cfg = await get_config(session)
    if cfg is None:
        return []
    bells = await get_bells(session)
    parity = week_parity(date, cfg)
    weekday = date.isoweekday()

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
    exceptions = (
        (await session.execute(select(Exc).where(Exc.date == date))).scalars().all()
    )
    subjects_map = await _subjects_map_if_needed(session, exceptions)
    return _build_day(bells, lessons, exceptions, subjects_map)


async def resolve_week(
    session: AsyncSession, monday: dt.date, days: int = 6
) -> list[tuple[dt.date, list[ResolvedLesson]]]:
    """Всю неделю одним заходом: 2 запроса вместо ~4 на каждый день."""
    cfg = await get_config(session)
    if cfg is None:
        return []
    bells = await get_bells(session)
    week_dates = [monday + dt.timedelta(days=i) for i in range(days)]

    all_lessons = (
        (
            await session.execute(
                select(Lesson).options(selectinload(Lesson.subject))
            )
        )
        .scalars()
        .all()
    )
    by_weekday: dict[int, list[Lesson]] = {}
    for ls in all_lessons:
        by_weekday.setdefault(ls.weekday, []).append(ls)

    exceptions = (
        (
            await session.execute(
                select(Exc)
                .where(Exc.date >= week_dates[0])
                .where(Exc.date <= week_dates[-1])
            )
        )
        .scalars()
        .all()
    )
    ex_by_date: dict[dt.date, list[Exc]] = {}
    for e in exceptions:
        ex_by_date.setdefault(e.date, []).append(e)
    subjects_map = await _subjects_map_if_needed(session, exceptions)

    out = []
    for d in week_dates:
        parity = week_parity(d, cfg)
        day_lessons = [
            ls
            for ls in by_weekday.get(d.isoweekday(), [])
            if ls.parity in ("every", parity)
        ]
        out.append((d, _build_day(bells, day_lessons, ex_by_date.get(d, []), subjects_map)))
    return out
