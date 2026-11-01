from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from .config import settings

TZ = ZoneInfo(settings.tz)


def now_local() -> dt.datetime:
    return dt.datetime.now(TZ)


def today_local() -> dt.date:
    return now_local().date()


def at(date: dt.date, hhmm: str) -> dt.datetime:
    """Собрать tz-aware datetime из даты и строки 'HH:MM'."""
    h, m = map(int, hhmm.split(":"))
    return dt.datetime(date.year, date.month, date.day, h, m, tzinfo=TZ)
