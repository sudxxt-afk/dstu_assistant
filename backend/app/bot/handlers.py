from __future__ import annotations

import asyncio
import datetime as dt
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import media
from .. import notion
from ..config import settings
from ..dateparse import parse_due
from ..db import async_session
from ..models import Attachment, LectureNote, Subject, Task
from ..schedule_logic import (
    get_config,
    resolve_day,
    resolve_week,
    week_number,
    week_parity,
)
from ..timeutil import at, now_local, today_local
from . import keyboards as kb
from .render import render_day, render_week

router = Router()

DASHBOARD_TEXT = "🎓 <b>DSTU Assistant</b>\nВыбирай 👇"


class Capture(StatesGroup):
    active = State()


class AddTask(StatesGroup):
    waiting = State()


# ---------------- helpers ----------------
async def _respond(cb: CallbackQuery, text: str, markup, toast: str | None = None) -> None:
    """Параллельно отвечает на нажатие (убирает «часики») и правит сообщение.
    Два запроса к Telegram идут одновременно -> вдвое быстрее по ощущениям."""

    async def _do_edit():
        try:
            await cb.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass  # "message is not modified" и т.п.

    async def _do_answer():
        try:
            await cb.answer(toast) if toast else await cb.answer()
        except TelegramBadRequest:
            pass

    # Оба в корутины-обёртки: передавать сырой cb.answer() в gather нельзя
    # (aiogram-объект нехешируемый -> TypeError в gather).
    await asyncio.gather(_do_edit(), _do_answer())


async def _day_text(date: dt.date) -> str:
    async with async_session() as db:
        cfg = await get_config(db)
        lessons = await resolve_day(db, date)
        wk = week_number(date, cfg) if cfg else None
        par = week_parity(date, cfg) if cfg else None
    return render_day(date, lessons, wk, par)


async def _week_text(base: dt.date) -> str:
    monday = base - dt.timedelta(days=base.isoweekday() - 1)
    async with async_session() as db:
        cfg = await get_config(db)
        wk = week_number(monday, cfg) if cfg else 0
        days = await resolve_week(db, monday)
    return render_week(days, wk)


async def _next_text() -> str:
    now = now_local()
    today = now.date()
    async with async_session() as db:
        for i in range(7):
            date = today + dt.timedelta(days=i)
            for ls in await resolve_day(db, date):
                if not ls.start_time:
                    continue
                start = at(date, ls.start_time)
                if start > now:
                    mins = int((start - now).total_seconds() // 60)
                    when = (
                        f"через {mins} мин"
                        if date == today and mins < 180
                        else start.strftime("%d.%m в %H:%M")
                    )
                    room = f"\n{ls.room}" if ls.room else ""
                    teacher = f"\n{ls.teacher}" if ls.teacher else ""
                    return (
                        f"⏭ <b>Следующая пара</b> ({when})\n\n"
                        f"<b>{ls.pair_number}) {ls.subject_name}</b>{room}{teacher}"
                    )
    return "⏭ Впереди пар нет 🎉"


def _ro(uid: int | None) -> bool:
    """Пользователь «только для чтения» (одногруппник), не владелец."""
    return uid != settings.allowed_user_id and uid in settings.readonly_ids


def _dash_text(uid: int | None) -> str:
    if _ro(uid):
        return "🎓 <b>DSTU Assistant</b>\nРасписание группы У632 👇"
    return DASHBOARD_TEXT


# ---------------- /start ----------------
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    await message.answer(_dash_text(uid), reply_markup=kb.dashboard(_ro(uid)))


# ---------------- навигация (редактируем то же сообщение) ----------------
@router.callback_query(F.data == "nav:today")
async def nav_today(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(cb, await _day_text(today_local()), kb.dashboard(_ro(cb.from_user.id)))


@router.callback_query(F.data == "nav:tomorrow")
async def nav_tomorrow(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(
        cb,
        await _day_text(today_local() + dt.timedelta(days=1)),
        kb.dashboard(_ro(cb.from_user.id)),
    )


@router.callback_query(F.data == "nav:week")
async def nav_week(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(cb, await _week_text(today_local()), kb.dashboard(_ro(cb.from_user.id)))


@router.callback_query(F.data == "nav:next")
async def nav_next(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(cb, await _next_text(), kb.dashboard(_ro(cb.from_user.id)))


@router.callback_query(F.data == "menu:home")
async def go_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(cb, _dash_text(cb.from_user.id), kb.dashboard(_ro(cb.from_user.id)))


# ---------------- Лекция ----------------
def _capture_status(name: str, ntext: int, nfiles: int) -> str:
    return (
        f"✍️ Записываю: <b>{name}</b>\n\n"
        f"Текстов: {ntext} · вложений: {nfiles}\n\n"
        f"Шли текст, фото и файлы. Потом — «Готово»."
    )


@router.callback_query(F.data == "menu:lecture")
async def menu_lecture(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    async with async_session() as db:
        subjects = (
            await db.execute(select(Subject).order_by(Subject.name))
        ).scalars().all()
    if not subjects:
        await _respond(cb, "Нет предметов для записи.", kb.back_kb())
    else:
        await _respond(cb, "✍️ По какому предмету записать лекцию?", kb.subjects_kb(subjects, "lec"))


@router.callback_query(F.data.startswith("lec:"))
async def pick_subject(cb: CallbackQuery, state: FSMContext):
    sid = int(cb.data.split(":")[1])
    today = today_local()
    now = now_local()
    async with async_session() as db:
        subj = await db.get(Subject, sid)
        pair = None
        for ls in await resolve_day(db, today):
            if ls.subject_id == sid and ls.start_time:
                if at(today, ls.start_time) <= now <= at(today, ls.end_time):
                    pair = ls.pair_number
                    break
    await state.set_state(Capture.active)
    await state.update_data(
        subject_id=sid,
        subject_name=subj.name,
        date=today.isoformat(),
        pair=pair,
        texts=[],
        attach_rels=[],
        attach_db=[],
        msg_id=cb.message.message_id,
        chat_id=cb.message.chat.id,
    )
    await _respond(cb, _capture_status(subj.name, 0, 0), kb.capture_kb())


async def _refresh_capture(bot, data: dict) -> None:
    try:
        await bot.edit_message_text(
            _capture_status(data["subject_name"], len(data["texts"]), len(data["attach_rels"])),
            chat_id=data["chat_id"],
            message_id=data["msg_id"],
            reply_markup=kb.capture_kb(),
        )
    except TelegramBadRequest:
        pass


@router.message(Capture.active, F.photo)
async def cap_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    fname = f"{data['date']}_{now_local():%H%M%S}.jpg"
    dest = media.media_dir(data["subject_name"]) / fname
    await message.bot.download(message.photo[-1], destination=dest)
    data["attach_rels"].append(fname)
    data["attach_db"].append({"kind": "photo", "file_path": str(dest), "orig": fname})
    if message.caption:
        data["texts"].append(message.caption.strip())
    await state.update_data(**data)
    await _refresh_capture(message.bot, data)


@router.message(Capture.active, F.document)
async def cap_document(message: Message, state: FSMContext):
    data = await state.get_data()
    orig = message.document.file_name or "file"
    fname = f"{data['date']}_{now_local():%H%M%S}_{orig}"
    dest = media.media_dir(data["subject_name"]) / fname
    await message.bot.download(message.document, destination=dest)
    data["attach_rels"].append(fname)
    data["attach_db"].append({"kind": "document", "file_path": str(dest), "orig": orig})
    if message.caption:
        data["texts"].append(message.caption.strip())
    await state.update_data(**data)
    await _refresh_capture(message.bot, data)


@router.message(Capture.active, F.text)
async def cap_text(message: Message, state: FSMContext):
    data = await state.get_data()
    data["texts"].append(message.text.strip())
    await state.update_data(**data)
    await _refresh_capture(message.bot, data)


@router.callback_query(F.data == "cap:done")
async def cap_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("texts") and not data.get("attach_rels"):
        await cb.answer("Пусто — нечего сохранять", show_alert=True)
        return
    date = dt.date.fromisoformat(data["date"])
    content = "\n\n".join(data["texts"])
    async with async_session() as db:
        note = LectureNote(
            subject_id=data["subject_id"],
            date=date,
            pair_number=data.get("pair"),
            content_md=content,
        )
        db.add(note)
        await db.flush()
        note_id = note.id
        for a in data["attach_db"]:
            db.add(
                Attachment(
                    note_id=note_id,
                    kind=a["kind"],
                    file_path=a["file_path"],
                    original_name=a["orig"],
                )
            )
        await db.commit()
    asyncio.create_task(notion.sync_lecture(note_id))
    await state.clear()
    n_att = len(data["attach_rels"])
    extra = f" · вложений: {n_att}" if n_att else ""
    await _respond(
        cb,
        f"💾 Лекция по <b>{data['subject_name']}</b> сохранена{extra}.\n"
        f"Открыть и дополнить можно в веб-панели → Лекции.",
        kb.back_kb(),
        toast="Сохранено",
    )


@router.callback_query(F.data == "cap:cancel")
async def cap_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(cb, DASHBOARD_TEXT, kb.dashboard(), toast="Отменено")


# ---------------- Задачи ----------------
async def _tasks() -> list:
    async with async_session() as db:
        q = (
            select(Task)
            .options(selectinload(Task.subject))
            .where(Task.done == False)  # noqa: E712
            .order_by(
                Task.priority.desc(),
                Task.due_date.is_(None),
                Task.due_date,
                Task.created_at,
            )
        )
        return (await db.execute(q)).scalars().all()


def _tasks_header(tasks: list) -> str:
    if not tasks:
        return "✅ <b>Задачи</b>\n\nПусто — красота."
    today = today_local()
    overdue = sum(1 for t in tasks if t.due_date and t.due_date < today)
    due_today = sum(1 for t in tasks if t.due_date == today)
    parts = []
    if overdue:
        parts.append(f"🔴 просрочено: {overdue}")
    if due_today:
        parts.append(f"📌 сегодня: {due_today}")
    parts.append(f"всего: {len(tasks)}")
    return "✅ <b>Активные задачи</b>\n" + " · ".join(parts)


@router.callback_query(F.data == "menu:tasks")
async def menu_tasks(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    tasks = await _tasks()
    await _respond(cb, _tasks_header(tasks), kb.tasks_kb(tasks))


@router.callback_query(F.data.startswith("task:toggle:"))
async def task_toggle(cb: CallbackQuery):
    tid = int(cb.data.split(":")[2])
    async with async_session() as db:
        t = await db.get(Task, tid)
        if t:
            t.done = not t.done
            await db.commit()
    tasks = await _tasks()
    await _respond(cb, _tasks_header(tasks), kb.tasks_kb(tasks), toast="Готово")


@router.callback_query(F.data.startswith("task:del:"))
async def task_del(cb: CallbackQuery):
    tid = int(cb.data.split(":")[2])
    async with async_session() as db:
        t = await db.get(Task, tid)
        if t:
            await db.delete(t)
            await db.commit()
    tasks = await _tasks()
    await _respond(cb, _tasks_header(tasks), kb.tasks_kb(tasks), toast="Удалено")


@router.callback_query(F.data.startswith("task:prio:"))
async def task_prio(cb: CallbackQuery):
    tid = int(cb.data.split(":")[2])
    async with async_session() as db:
        t = await db.get(Task, tid)
        if t:
            t.priority = 0 if t.priority else 1
            await db.commit()
    tasks = await _tasks()
    await _respond(cb, _tasks_header(tasks), kb.tasks_kb(tasks), toast="Готово")


@router.callback_query(F.data == "task:add")
async def task_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddTask.waiting)
    await state.update_data(msg_id=cb.message.message_id, chat_id=cb.message.chat.id)
    await _respond(
        cb,
        "➕ Напиши задачу. Можно добавить:\n"
        "• <b>срок</b> через «|» — <code>завтра</code>, <code>20.11</code>, "
        "<code>пн</code>, <code>+3</code>, <code>2026-11-20</code>\n"
        "• <b>!</b> в начале — пометить важной\n"
        "• <b>@Предмет</b> — привязать к предмету\n\n"
        "<code>!Сдать лабу @Физика | пятница</code>",
        kb.back_kb(),
    )


@router.message(AddTask.waiting, F.text)
async def task_save(message: Message, state: FSMContext):
    raw = message.text.strip()
    title, _, due_raw = raw.partition("|")
    title = title.strip()

    priority = 0
    if title.startswith("!"):
        priority = 1
        title = title[1:].strip()

    # @Предмет (в любом месте заголовка)
    subject_id = None
    subj_warn = ""
    m = re.search(r"@(\S+)", title)
    if m:
        name = m.group(1)
        title = (title[: m.start()] + title[m.end() :]).strip()
        async with async_session() as db:
            subs = (await db.execute(select(Subject))).scalars().all()
        low = name.lower()
        match = next(
            (su for su in subs if su.name.lower() == low or su.name.lower().startswith(low)),
            None,
        )
        if match:
            subject_id = match.id
        else:
            subj_warn = f"\n⚠️ Предмет «{name}» не найден — задача без привязки."

    if not title:
        await message.answer("Пустой текст задачи. Попробуй ещё раз.")
        return

    due = None
    if due_raw.strip():
        try:
            due = parse_due(due_raw, today_local())
        except ValueError:
            await message.answer(
                "Не понял срок. Примеры: завтра, 20.11, пн, +3, 2026-11-20."
            )
            return
    async with async_session() as db:
        db.add(
            Task(title=title, due_date=due, priority=priority, subject_id=subject_id)
        )
        await db.commit()
    if subj_warn:
        await message.answer(subj_warn.strip())
    data = await state.get_data()
    await state.clear()
    tasks = await _tasks()
    try:
        await message.bot.edit_message_text(
            _tasks_header(tasks),
            chat_id=data["chat_id"],
            message_id=data["msg_id"],
            reply_markup=kb.tasks_kb(tasks),
        )
    except TelegramBadRequest:
        pass


# ---------------- Настройки ----------------
@router.callback_query(F.data == "menu:settings")
async def menu_settings(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    today = today_local()
    async with async_session() as db:
        cfg = await get_config(db)
    parity = {"odd": "нечётная", "even": "чётная"}[week_parity(today, cfg)]
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"Семестр: {cfg.semester_start:%d.%m.%Y} — {cfg.semester_end:%d.%m.%Y}\n"
        f"Сейчас: неделя {week_number(today, cfg)}, {parity}\n"
        f"Напоминание: за {cfg.reminder_minutes} мин до пары\n"
        f"Утренний бриф: {cfg.morning_brief_time}\n"
        "Вечерняя рассылка: 20:00 (на завтра)"
    )
    await _respond(cb, text, kb.back_kb())


# ---------------- фолбэк (регистрируется последним) ----------------
@router.message(F.text)
async def fallback(message: Message, state: FSMContext):
    await message.answer(DASHBOARD_TEXT, reply_markup=kb.dashboard())
