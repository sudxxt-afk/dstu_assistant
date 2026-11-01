from __future__ import annotations

import asyncio
import datetime as dt
import logging

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, TelegramObject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from . import obsidian
from .bot.handlers import router
from .bot.render import render_day
from .config import settings
from .db import async_session, init_db
from .models import Config, Task
from .schedule_logic import resolve_day, week_number, week_parity
from .timeutil import at, now_local, today_local

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")


class AccessMiddleware(BaseMiddleware):
    """Пропускает только владельца. Незнакомцу подсказывает его ID."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        uid = user.id if user else None
        allowed = settings.allowed_user_id

        if allowed is None:
            if isinstance(event, Message):
                await event.answer(
                    f"Твой Telegram ID: <code>{uid}</code>\n"
                    "Впиши его в .env → ALLOWED_USER_ID и перезапусти бота."
                )
            return
        if uid != allowed:
            return
        return await handler(event, data)


# --- Планировщик: защита от повторной отправки в ту же минуту ---
_sent_brief: set[str] = set()
_sent_reminders: set[tuple[str, int]] = set()
_current_day: str | None = None


async def _tick(bot: Bot):
    global _current_day
    if settings.allowed_user_id is None:
        return
    now = now_local()
    today = now.date()
    hhmm = now.strftime("%H:%M")

    # Сброс дедупликации на новый день
    if _current_day != today.isoformat():
        _current_day = today.isoformat()
        _sent_brief.clear()
        _sent_reminders.clear()

    async with async_session() as db:
        cfg = await db.get(Config, 1)
        if not cfg:
            return
        lessons = await resolve_day(db, today)

        # Утренний бриф
        if hhmm == cfg.morning_brief_time and today.isoformat() not in _sent_brief:
            tasks = (
                await db.execute(select(Task).where(Task.done == False))  # noqa: E712
            ).scalars().all()
            parity = week_parity(today, cfg)
            wk = week_number(today, cfg)
            text = "☀️ <b>Доброе утро!</b>\n\n" + render_day(today, lessons, wk, parity)
            if tasks:
                text += "\n\n📋 <b>Задачи:</b>\n" + "\n".join(
                    f"• {t.title}" + (f" (до {t.due_date:%d.%m})" if t.due_date else "")
                    for t in tasks
                )
            try:
                await bot.send_message(settings.allowed_user_id, text)
                obsidian.write_daily_note(today, lessons, tasks, wk, parity)
            except Exception as e:  # noqa: BLE001
                log.warning("brief failed: %s", e)
            _sent_brief.add(today.isoformat())

        # Напоминания перед парой
        for ls in lessons:
            if not ls.start_time:
                continue
            remind_dt = at(today, ls.start_time) - dt.timedelta(
                minutes=cfg.reminder_minutes
            )
            key = (today.isoformat(), ls.pair_number)
            if remind_dt.strftime("%H:%M") == hhmm and key not in _sent_reminders:
                room = f", ауд. {ls.room}" if ls.room else ""
                try:
                    await bot.send_message(
                        settings.allowed_user_id,
                        f"🔔 Через {cfg.reminder_minutes} мин — "
                        f"<b>{ls.subject_name}</b> ({ls.type})\n"
                        f"🕐 {ls.start_time}{room}",
                    )
                except Exception as e:  # noqa: BLE001
                    log.warning("reminder failed: %s", e)
                _sent_reminders.add(key)


async def main():
    await init_db()

    if not settings.bot_token:
        log.error("BOT_TOKEN не задан в .env")
        return

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())
    dp.include_router(router)

    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(_tick, "cron", second=0, args=[bot])  # каждую минуту
    scheduler.start()

    log.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
