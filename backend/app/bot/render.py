from __future__ import annotations

import datetime as dt

from ..schedule_logic import WEEKDAY_RU, ResolvedLesson

STATUS_MARK = {"moved": " (перенос)", "added": " (доб.)"}


def _pair_block(ls: ResolvedLesson, bold: bool = True) -> str:
    """Один блок пары: номер) название / кабинет / препод."""
    name = ls.subject_name + STATUS_MARK.get(ls.status, "")
    title = f"{ls.pair_number}) {name}"
    lines = [f"<b>{title}</b>" if bold else title]
    if ls.room:
        lines.append(ls.room)
    if ls.teacher:
        lines.append(ls.teacher)
    return "\n".join(lines)


def render_day(
    date: dt.date,
    lessons: list[ResolvedLesson],
    week_no: int | None = None,
    parity: str | None = None,
) -> str:
    head = f"🗓 <b>{WEEKDAY_RU[date.isoweekday()]}, {date:%d.%m}</b>"
    if week_no:
        head += f"\n<i>неделя {week_no}</i>"
    if not lessons:
        return head + "\n\nПар нет 🎉"
    blocks = [_pair_block(ls) for ls in lessons]
    return head + "\n\n" + "\n\n".join(blocks)


def render_week(days: list[tuple[dt.date, list[ResolvedLesson]]], week_no: int) -> str:
    out = [f"📆 <b>Неделя {week_no}</b>"]
    any_day = False
    for date, lessons in days:
        if not lessons:
            continue
        any_day = True
        day_head = f"<b>{WEEKDAY_RU[date.isoweekday()]} {date:%d.%m}</b>"
        blocks = [_pair_block(ls, bold=False) for ls in lessons]
        out.append(day_head + "\n" + "\n\n".join(blocks))
    if not any_day:
        out.append("Пар на неделе нет 🎉")
    return "\n\n".join(out)
