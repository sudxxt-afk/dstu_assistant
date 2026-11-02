from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

HOME_BTN = InlineKeyboardButton(text="⬅️ Меню", callback_data="menu:home")


def dashboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="nav:today"),
                InlineKeyboardButton(text="📅 Завтра", callback_data="nav:tomorrow"),
            ],
            [
                InlineKeyboardButton(text="📆 Неделя", callback_data="nav:week"),
                InlineKeyboardButton(text="⏭ Следующая", callback_data="nav:next"),
            ],
            [
                InlineKeyboardButton(text="📝 Лекция", callback_data="menu:lecture"),
                InlineKeyboardButton(text="✅ Задачи", callback_data="menu:tasks"),
            ],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")],
        ]
    )


def subjects_kb(subjects: list, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=s.name, callback_data=f"{prefix}:{s.id}")]
        for s in subjects
    ]
    rows.append([HOME_BTN])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def capture_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💾 Готово", callback_data="cap:done"),
                InlineKeyboardButton(text="✖️ Отмена", callback_data="cap:cancel"),
            ]
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
    rows.append(
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="task:add"),
            HOME_BTN,
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[HOME_BTN]])
