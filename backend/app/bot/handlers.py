from __future__ import annotations

import datetime as dt

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from .. import obsidian
from ..db import async_session
from ..models import Attachment, Config, LectureNote, Subject, Task
from ..schedule_logic import resolve_day, week_number, week_parity
from ..timeutil import at, now_local, today_local
from . import keyboards as kb
from .render import render_day

router = Router()

MENU_TEXTS = {
    kb.BTN_TODAY,
    kb.BTN_TOMORROW,
    kb.BTN_WEEK,
    kb.BTN_NEXT,
    kb.BTN_LECTURE,
    kb.BTN_TASKS,
    kb.BTN_SETTINGS,
}


class Capture(StatesGroup):
    active = State()


class AddTask(StatesGroup):
    waiting = State()


# ---------------- /start ----------------
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я ассистент по учёбе 🎓\nВыбирай кнопки снизу.",
        reply_markup=kb.main_menu(),
    )


# ---------------- Расписание ----------------
async def _send_day(message: Message, date: dt.date):
    async with async_session() as db:
        cfg = await db.get(Config, 1)
        lessons = await resolve_day(db, date)
        text = render_day(
            date,
            lessons,
            week_number(date, cfg) if cfg else None,
            week_parity(date, cfg) if cfg else None,
        )
    await message.answer(text, reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_TODAY)
async def on_today(message: Message, state: FSMContext):
    await state.clear()
    await _send_day(message, today_local())


@router.message(F.text == kb.BTN_TOMORROW)
async def on_tomorrow(message: Message, state: FSMContext):
    await state.clear()
    await _send_day(message, today_local() + dt.timedelta(days=1))


@router.message(F.text == kb.BTN_WEEK)
async def on_week(message: Message, state: FSMContext):
    await state.clear()
    base = today_local()
    monday = base - dt.timedelta(days=base.isoweekday() - 1)
    for i in range(7):
        await _send_day(message, monday + dt.timedelta(days=i))


@router.message(F.text == kb.BTN_NEXT)
async def on_next(message: Message, state: FSMContext):
    await state.clear()
    now = now_local()
    async with async_session() as db:
        # Сегодня — ищем пару, которая ещё не началась.
        today = now.date()
        for date in (today, today + dt.timedelta(days=1), today + dt.timedelta(days=2)):
            lessons = await resolve_day(db, date)
            for ls in lessons:
                if not ls.start_time:
                    continue
                start = at(date, ls.start_time)
                if start > now:
                    delta = start - now
                    mins = int(delta.total_seconds() // 60)
                    when = (
                        f"через {mins} мин"
                        if date == today and mins < 180
                        else start.strftime("%d.%m в %H:%M")
                    )
                    room = f", ауд. {ls.room}" if ls.room else ""
                    await message.answer(
                        f"⏭ Следующая пара {when}:\n\n"
                        f"<b>{ls.subject_name}</b> ({ls.type})\n"
                        f"🕐 {ls.start_time}–{ls.end_time}{room}",
                        reply_markup=kb.main_menu(),
                    )
                    return
    await message.answer("Впереди пар не нашёл 🤷", reply_markup=kb.main_menu())


# ---------------- Лекция (захват) ----------------
@router.message(F.text == kb.BTN_LECTURE)
async def on_lecture(message: Message, state: FSMContext):
    await state.clear()
    async with async_session() as db:
        subjects = (
            await db.execute(select(Subject).order_by(Subject.name))
        ).scalars().all()
    if not subjects:
        await message.answer(
            "Сначала добавь предметы (через веб/API). "
            "Пока их нет — записывать лекцию не к чему.",
            reply_markup=kb.main_menu(),
        )
        return
    await message.answer(
        "По какому предмету записать?", reply_markup=kb.subjects_kb(subjects, "lec")
    )


@router.callback_query(F.data.startswith("lec:"))
async def pick_subject(cb: CallbackQuery, state: FSMContext):
    subject_id = int(cb.data.split(":")[1])
    today = today_local()
    now = now_local()
    async with async_session() as db:
        subj = await db.get(Subject, subject_id)
        # Попробуем угадать номер текущей пары этого предмета.
        pair = None
        for ls in await resolve_day(db, today):
            if ls.subject_id == subject_id and ls.start_time:
                if at(today, ls.start_time) <= now <= at(today, ls.end_time):
                    pair = ls.pair_number
                    break
    await state.set_state(Capture.active)
    await state.update_data(
        subject_id=subject_id,
        subject_name=subj.name,
        date=today.isoformat(),
        pair=pair,
        texts=[],
        attach_rels=[],
        attach_db=[],
    )
    await cb.message.edit_text(
        f"✍️ Записываю по предмету <b>{subj.name}</b>.\n"
        f"Шли текст, фото и файлы — всё попадёт в заметку. "
        f"Когда закончишь — нажми «Готово».",
        reply_markup=kb.capture_done_kb(),
    )
    await cb.answer()


@router.message(Capture.active, F.photo)
async def capture_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    subject_name = data["subject_name"]
    fname = f"{data['date']}_{now_local():%H%M%S}.jpg"
    dest = obsidian.attachments_dir(subject_name) / fname
    await message.bot.download(message.photo[-1], destination=dest)
    data["attach_rels"].append(fname)
    data["attach_db"].append({"kind": "photo", "file_path": str(dest), "orig": fname})
    if message.caption:
        data["texts"].append(message.caption.strip())
    await state.update_data(**data)
    await message.answer("📎 Фото добавлено", reply_markup=kb.capture_done_kb())


@router.message(Capture.active, F.document)
async def capture_document(message: Message, state: FSMContext):
    data = await state.get_data()
    subject_name = data["subject_name"]
    orig = message.document.file_name or "file"
    fname = f"{data['date']}_{now_local():%H%M%S}_{orig}"
    dest = obsidian.attachments_dir(subject_name) / fname
    await message.bot.download(message.document, destination=dest)
    data["attach_rels"].append(fname)
    data["attach_db"].append(
        {"kind": "document", "file_path": str(dest), "orig": orig}
    )
    if message.caption:
        data["texts"].append(message.caption.strip())
    await state.update_data(**data)
    await message.answer(f"📎 Файл «{orig}» добавлен", reply_markup=kb.capture_done_kb())


@router.message(Capture.active, F.text)
async def capture_text(message: Message, state: FSMContext):
    data = await state.get_data()
    data["texts"].append(message.text.strip())
    await state.update_data(**data)
    await message.answer("✅ Записал", reply_markup=kb.capture_done_kb())


@router.callback_query(F.data == "cap:done")
async def capture_done(cb: CallbackQuery, state: FSMContext):
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
        for a in data["attach_db"]:
            db.add(
                Attachment(
                    note_id=note.id,
                    kind=a["kind"],
                    file_path=a["file_path"],
                    original_name=a["orig"],
                )
            )
        await db.commit()
    path = obsidian.append_lecture(
        data["subject_name"], date, data.get("pair"), content, data["attach_rels"]
    )
    await state.clear()
    await cb.message.edit_text(
        f"💾 Сохранил в Obsidian:\n<code>{path}</code>"
    )
    await cb.message.answer("Готово 👍", reply_markup=kb.main_menu())
    await cb.answer()


# ---------------- Задачи ----------------
async def _tasks_markup():
    async with async_session() as db:
        tasks = (
            await db.execute(select(Task).where(Task.done == False))  # noqa: E712
        ).scalars().all()
    return tasks


@router.message(F.text == kb.BTN_TASKS)
async def on_tasks(message: Message, state: FSMContext):
    await state.clear()
    tasks = await _tasks_markup()
    text = "📋 Активные задачи:" if tasks else "📋 Задач нет"
    await message.answer(text, reply_markup=kb.tasks_kb(tasks))


@router.callback_query(F.data.startswith("task:toggle:"))
async def task_toggle(cb: CallbackQuery):
    tid = int(cb.data.split(":")[2])
    async with async_session() as db:
        t = await db.get(Task, tid)
        if t:
            t.done = not t.done
            await db.commit()
    tasks = await _tasks_markup()
    await cb.message.edit_reply_markup(reply_markup=kb.tasks_kb(tasks))
    await cb.answer("Готово ✅")


@router.callback_query(F.data.startswith("task:del:"))
async def task_del(cb: CallbackQuery):
    tid = int(cb.data.split(":")[2])
    async with async_session() as db:
        t = await db.get(Task, tid)
        if t:
            await db.delete(t)
            await db.commit()
    tasks = await _tasks_markup()
    await cb.message.edit_reply_markup(reply_markup=kb.tasks_kb(tasks))
    await cb.answer("Удалено 🗑")


@router.callback_query(F.data == "task:add")
async def task_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddTask.waiting)
    await cb.message.answer(
        "Напиши задачу. Можно с дедлайном через «|»:\n"
        "<code>Сдать лабу по физике | 2026-11-20</code>"
    )
    await cb.answer()


@router.message(AddTask.waiting, F.text)
async def task_save(message: Message, state: FSMContext):
    raw = message.text.strip()
    title, _, due_raw = raw.partition("|")
    title = title.strip()
    due = None
    if due_raw.strip():
        try:
            due = dt.date.fromisoformat(due_raw.strip())
        except ValueError:
            await message.answer("Дата должна быть в формате ГГГГ-ММ-ДД. Попробуй ещё.")
            return
    async with async_session() as db:
        db.add(Task(title=title, due_date=due))
        await db.commit()
    await state.clear()
    tasks = await _tasks_markup()
    await message.answer("✅ Задача добавлена", reply_markup=kb.tasks_kb(tasks))


# ---------------- Настройки ----------------
@router.message(F.text == kb.BTN_SETTINGS)
async def on_settings(message: Message, state: FSMContext):
    await state.clear()
    today = today_local()
    async with async_session() as db:
        cfg = await db.get(Config, 1)
    if not cfg:
        await message.answer("Конфиг не найден.", reply_markup=kb.main_menu())
        return
    parity = {"odd": "нечётная", "even": "чётная"}[week_parity(today, cfg)]
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        f"Семестр: {cfg.semester_start:%d.%m.%Y} — {cfg.semester_end:%d.%m.%Y}\n"
        f"Сегодня: неделя {week_number(today, cfg)}, <b>{parity}</b>\n"
        f"Напоминание за: {cfg.reminder_minutes} мин до пары\n"
        f"Утренний бриф: {cfg.morning_brief_time}\n\n"
        "<i>Редактирование расписания и настроек — через веб-панель "
        "(будет на следующем этапе).</i>",
        reply_markup=kb.main_menu(),
    )


# ---------------- Фолбэк ----------------
@router.message(F.text)
async def fallback(message: Message, state: FSMContext):
    # Любой текст вне сценариев — показываем меню.
    if message.text in MENU_TEXTS:
        return
    await message.answer("Выбери действие на кнопках снизу 👇", reply_markup=kb.main_menu())
