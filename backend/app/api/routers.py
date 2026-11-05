from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models as m
from ..schedule_logic import (
    WEEKDAY_RU,
    get_config,
    invalidate_cache,
    resolve_day,
    resolve_week,
    week_number,
    week_parity,
)
from . import schemas as s
from ..config import settings
from .deps import get_session, require_token

# Публичный роутер логина — без X-API-Token.
auth_router = APIRouter()


@auth_router.post("/auth/login")
async def login(body: s.LoginIn):
    if settings.panel_password and body.password == settings.panel_password:
        return {"token": settings.api_token}
    raise HTTPException(status_code=401, detail="Неверный пароль")


router = APIRouter(dependencies=[Depends(require_token)])


# ---------------- Config ----------------
@router.get("/config", response_model=s.ConfigOut)
async def get_config(db: AsyncSession = Depends(get_session)):
    cfg = await db.get(m.Config, 1)
    if not cfg:
        raise HTTPException(404, "Конфиг не инициализирован")
    return cfg


@router.put("/config", response_model=s.ConfigOut)
async def put_config(body: s.ConfigIn, db: AsyncSession = Depends(get_session)):
    cfg = await db.get(m.Config, 1)
    if not cfg:
        cfg = m.Config(id=1)
        db.add(cfg)
    for k, v in body.model_dump().items():
        setattr(cfg, k, v)
    await db.commit()
    invalidate_cache()
    return cfg


# ---------------- Bells ----------------
@router.get("/bells", response_model=list[s.BellIn])
async def get_bells(db: AsyncSession = Depends(get_session)):
    rows = (
        await db.execute(select(m.BellSchedule).order_by(m.BellSchedule.pair_number))
    ).scalars().all()
    return rows


@router.put("/bells", response_model=list[s.BellIn])
async def put_bells(body: list[s.BellIn], db: AsyncSession = Depends(get_session)):
    await db.execute(delete(m.BellSchedule))
    for b in body:
        db.add(m.BellSchedule(**b.model_dump()))
    await db.commit()
    invalidate_cache()
    return body


# ---------------- Subjects ----------------
@router.get("/subjects", response_model=list[s.SubjectOut])
async def list_subjects(db: AsyncSession = Depends(get_session)):
    return (await db.execute(select(m.Subject).order_by(m.Subject.name))).scalars().all()


@router.post("/subjects", response_model=s.SubjectOut)
async def create_subject(body: s.SubjectIn, db: AsyncSession = Depends(get_session)):
    obj = m.Subject(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/subjects/{sid}", response_model=s.SubjectOut)
async def update_subject(
    sid: int, body: s.SubjectIn, db: AsyncSession = Depends(get_session)
):
    obj = await db.get(m.Subject, sid)
    if not obj:
        raise HTTPException(404, "Предмет не найден")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    return obj


@router.delete("/subjects/{sid}")
async def delete_subject(sid: int, db: AsyncSession = Depends(get_session)):
    obj = await db.get(m.Subject, sid)
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


# ---------------- Lessons ----------------
@router.get("/lessons", response_model=list[s.LessonOut])
async def list_lessons(
    weekday: int | None = None, db: AsyncSession = Depends(get_session)
):
    q = select(m.Lesson).order_by(m.Lesson.weekday, m.Lesson.pair_number)
    if weekday:
        q = q.where(m.Lesson.weekday == weekday)
    return (await db.execute(q)).scalars().all()


@router.post("/lessons", response_model=s.LessonOut)
async def create_lesson(body: s.LessonIn, db: AsyncSession = Depends(get_session)):
    obj = m.Lesson(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/lessons/{lid}", response_model=s.LessonOut)
async def update_lesson(
    lid: int, body: s.LessonIn, db: AsyncSession = Depends(get_session)
):
    obj = await db.get(m.Lesson, lid)
    if not obj:
        raise HTTPException(404, "Пара не найдена")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    return obj


@router.delete("/lessons/{lid}")
async def delete_lesson(lid: int, db: AsyncSession = Depends(get_session)):
    obj = await db.get(m.Lesson, lid)
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


# ---------------- Exceptions ----------------
@router.get("/exceptions", response_model=list[s.ExceptionOut])
async def list_exceptions(
    date: dt.date | None = None, db: AsyncSession = Depends(get_session)
):
    q = select(m.Exception)
    if date:
        q = q.where(m.Exception.date == date)
    return (await db.execute(q)).scalars().all()


@router.post("/exceptions", response_model=s.ExceptionOut)
async def create_exception(body: s.ExceptionIn, db: AsyncSession = Depends(get_session)):
    obj = m.Exception(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/exceptions/{eid}")
async def delete_exception(eid: int, db: AsyncSession = Depends(get_session)):
    obj = await db.get(m.Exception, eid)
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


# ---------------- Tasks ----------------
def _task_out(t: m.Task) -> s.TaskOut:
    return s.TaskOut(
        id=t.id,
        title=t.title,
        subject_id=t.subject_id,
        due_date=t.due_date,
        priority=t.priority,
        done=t.done,
        subject_name=t.subject.name if t.subject else None,
    )


async def _load_task(db: AsyncSession, tid: int) -> m.Task | None:
    q = select(m.Task).options(selectinload(m.Task.subject)).where(m.Task.id == tid)
    return (await db.execute(q)).scalar_one_or_none()


@router.get("/tasks", response_model=list[s.TaskOut])
async def list_tasks(
    include_done: bool = False, db: AsyncSession = Depends(get_session)
):
    # Важные вверху, затем по сроку (без срока — в конец), затем по дате создания.
    q = (
        select(m.Task)
        .options(selectinload(m.Task.subject))
        .order_by(
            m.Task.done,
            m.Task.priority.desc(),
            m.Task.due_date.is_(None),
            m.Task.due_date,
            m.Task.created_at,
        )
    )
    if not include_done:
        q = q.where(m.Task.done == False)  # noqa: E712
    return [_task_out(t) for t in (await db.execute(q)).scalars().all()]


@router.post("/tasks", response_model=s.TaskOut)
async def create_task(body: s.TaskIn, db: AsyncSession = Depends(get_session)):
    obj = m.Task(**body.model_dump())
    db.add(obj)
    await db.commit()
    return _task_out(await _load_task(db, obj.id))


@router.patch("/tasks/{tid}", response_model=s.TaskOut)
async def update_task(
    tid: int, body: s.TaskPatch, db: AsyncSession = Depends(get_session)
):
    obj = await db.get(m.Task, tid)
    if not obj:
        raise HTTPException(404, "Задача не найдена")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    return _task_out(await _load_task(db, tid))


@router.patch("/tasks/{tid}/toggle", response_model=s.TaskOut)
async def toggle_task(tid: int, db: AsyncSession = Depends(get_session)):
    obj = await db.get(m.Task, tid)
    if not obj:
        raise HTTPException(404, "Задача не найдена")
    obj.done = not obj.done
    await db.commit()
    return _task_out(await _load_task(db, tid))


@router.delete("/tasks/{tid}")
async def delete_task(tid: int, db: AsyncSession = Depends(get_session)):
    obj = await db.get(m.Task, tid)
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


# ---------------- Schedule ----------------
async def _day_payload(db: AsyncSession, date: dt.date) -> s.DayOut:
    cfg = await get_config(db)
    lessons = await resolve_day(db, date)
    return s.DayOut(
        date=date,
        weekday=WEEKDAY_RU[date.isoweekday()],
        week_number=week_number(date, cfg) if cfg else 0,
        parity=week_parity(date, cfg) if cfg else "odd",
        lessons=[s.ResolvedOut(**vars(x)) for x in lessons],
    )


@router.get("/schedule/day", response_model=s.DayOut)
async def schedule_day(
    date: dt.date | None = None, db: AsyncSession = Depends(get_session)
):
    return await _day_payload(db, date or dt.date.today())


@router.get("/schedule/week", response_model=list[s.DayOut])
async def schedule_week(
    date: dt.date | None = None, db: AsyncSession = Depends(get_session)
):
    base = date or dt.date.today()
    monday = base - dt.timedelta(days=base.isoweekday() - 1)
    cfg = await get_config(db)
    days = await resolve_week(db, monday, days=7)
    return [
        s.DayOut(
            date=d,
            weekday=WEEKDAY_RU[d.isoweekday()],
            week_number=week_number(d, cfg) if cfg else 0,
            parity=week_parity(d, cfg) if cfg else "odd",
            lessons=[s.ResolvedOut(**vars(x)) for x in lessons],
        )
        for d, lessons in days
    ]
