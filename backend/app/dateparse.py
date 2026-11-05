"""Гибкий разбор дедлайна из текста для бота.

Поддерживает: ISO (2026-11-20), 20.11 / 20.11.26 / 20.11.2026,
«сегодня», «завтра», «послезавтра», дни недели (пн..вс / полные),
«+N» (через N дней). Пустая строка → None. Непонятный ввод → ValueError.
"""
from __future__ import annotations

import datetime as dt
import re

_WORDS = {
    "сегодня": 0,
    "сёдня": 0,
    "седня": 0,
    "завтра": 1,
    "завтро": 1,
    "послезавтра": 2,
}

_WEEKDAYS = {
    "пн": 0, "понедельник": 0,
    "вт": 1, "вторник": 1,
    "ср": 2, "среда": 2,
    "чт": 3, "четверг": 3,
    "пт": 4, "пятница": 4,
    "сб": 5, "суббота": 5,
    "вс": 6, "воскресенье": 6,
}


def parse_due(text: str, today: dt.date) -> dt.date | None:
    s = text.strip().lower()
    if not s:
        return None

    if s in _WORDS:
        return today + dt.timedelta(days=_WORDS[s])

    if s in _WEEKDAYS:
        delta = (_WEEKDAYS[s] - today.weekday()) % 7
        delta = delta or 7  # ближайший будущий такой день, не сегодня
        return today + dt.timedelta(days=delta)

    m = re.fullmatch(r"\+(\d+)", s)
    if m:
        return today + dt.timedelta(days=int(m.group(1)))

    # ISO
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        pass

    # DD.MM[.YY[YY]] (также через / или -)
    m = re.fullmatch(r"(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?", s)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        if m.group(3):
            year = int(m.group(3))
            if year < 100:
                year += 2000
        else:
            year = today.year
        try:
            d = dt.date(year, month, day)
        except ValueError as e:
            raise ValueError("неверная дата") from e
        # Без года: если дата уже прошла — берём следующий год.
        if not m.group(3) and d < today:
            d = d.replace(year=year + 1)
        return d

    raise ValueError("не распознал дату")
