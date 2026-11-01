from __future__ import annotations

import datetime as dt

from ..schedule_logic import WEEKDAY_RU, ResolvedLesson

PARITY_RU = {"odd": "нечётная", "even": "чётная"}
STATUS_MARK = {"moved": " ⟲ перенос", "added": " ➕ добавлено"}


def render_day(
    date: dt.date,
    lessons: list[ResolvedLesson],
    week_no: int | None = None,
    parity: str | None = None,
) -> str:
    head = f"<b>{WEEKDAY_RU[date.isoweekday()]}, {date.strftime('%d.%m')}</b>"
    sub = []
    if week_no:
        sub.append(f"неделя {week_no}")
    if parity:
        sub.append(PARITY_RU.get(parity, parity))
    if sub:
        head += f"\n<i>{' · '.join(sub)}</i>"

    if not lessons:
        return head + "\n\n🎉 Пар нет"

    lines = [head, ""]
    for ls in lessons:
        time = (
            f"{ls.start_time}–{ls.end_time}"
            if ls.start_time
            else f"пара {ls.pair_number}"
        )
        room = f" · ауд. {ls.room}" if ls.room else ""
        teacher = f"\n   👤 {ls.teacher}" if ls.teacher else ""
        mark = STATUS_MARK.get(ls.status, "")
        note = f"\n   💬 {ls.note}" if ls.note else ""
        lines.append(
            f"🔹 <b>{time}</b> — {ls.subject_name}"
            f"\n   <i>{ls.type}</i>{room}{mark}{teacher}{note}"
        )
    return "\n".join(lines)
