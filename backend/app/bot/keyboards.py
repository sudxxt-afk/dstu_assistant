from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Тексты кнопок главного меню (используются и как роутинг в хендлерах).
BTN_TODAY = "📅 Сегодня"
BTN_TOMORROW = "📅 Завтра"
BTN_WEEK = "📆 Неделя"
BTN_NEXT = "⏭ Следующая"
BTN_LECTURE = "📝 Лекция"
BTN_TASKS = "✅ Задачи"
BTN_SETTINGS = "⚙️ Настройки"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TODAY), KeyboardButton(text=BTN_TOMORROW)],
            [KeyboardButton(text=BTN_WEEK), KeyboardButton(text=BTN_NEXT)],
            [KeyboardButton(text=BTN_LECTURE), KeyboardButton(text=BTN_TASKS)],
            [KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
    )


def subjects_kb(subjects: list, prefix: str) -> InlineKeyboardMarkup:
    """Инлайн-кнопки предметов. callback_data = f'{prefix}:{id}'."""
    rows = [
        [InlineKeyboardButton(text=s.name, callback_data=f"{prefix}:{s.id}")]
        for s in subjects
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def capture_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="cap:done")]
        ]
    )


def tasks_kb(tasks: list) -> InlineKeyboardMarkup:
    rows = []
    for t in tasks:
        mark = "✅" if t.done else "⬜"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {t.title}", callback_data=f"task:toggle:{t.id}"
                ),
                InlineKeyboardButton(text="🗑", callback_data=f"task:del:{t.id}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="task:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
