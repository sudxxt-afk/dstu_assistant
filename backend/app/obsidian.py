from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .config import settings

VAULT = Path(settings.vault_path)


def _safe(name: str) -> str:
    """Имя, безопасное для файловой системы и для [[ссылок]] Obsidian."""
    name = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    return name or "Без названия"


def subject_dir(subject_name: str) -> Path:
    d = VAULT / _safe(subject_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def attachments_dir(subject_name: str) -> Path:
    d = subject_dir(subject_name) / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_lecture(
    subject_name: str,
    date: dt.date,
    pair_number: int | None,
    content: str,
    attachment_rel_paths: list[str] | None = None,
) -> Path:
    """Создать/дополнить заметку лекции: Vault/<Предмет>/<YYYY-MM-DD>.md"""
    path = subject_dir(subject_name) / f"{date.isoformat()}.md"
    now = dt.datetime.now().strftime("%H:%M")

    if not path.exists():
        pair_line = f"пара {pair_number} · " if pair_number else ""
        header = (
            f"---\n"
            f"date: {date.isoformat()}\n"
            f"subject: {subject_name}\n"
            f"tags: [лекция, {_safe(subject_name)}]\n"
            f"---\n\n"
            f"# {subject_name} — {date.isoformat()}\n"
            f"{pair_line}[[{_safe(subject_name)}]]\n\n"
        )
        path.write_text(header, encoding="utf-8")

    block = [f"\n## {now}\n"]
    if content.strip():
        block.append(content.strip() + "\n")
    for rel in attachment_rel_paths or []:
        block.append(f"\n![[{rel}]]\n")

    with path.open("a", encoding="utf-8") as f:
        f.write("".join(block))
    return path


def write_daily_note(
    date: dt.date,
    lessons: list,
    tasks: list,
    week_no: int | None = None,
    parity: str | None = None,
) -> Path:
    """Утренняя заметка: Vault/Daily/<YYYY-MM-DD>.md"""
    daily = VAULT / "Daily"
    daily.mkdir(parents=True, exist_ok=True)
    path = daily / f"{date.isoformat()}.md"

    parity_ru = {"odd": "нечётная", "even": "чётная"}.get(parity or "", "")
    meta = []
    if week_no:
        meta.append(f"неделя {week_no}")
    if parity_ru:
        meta.append(parity_ru)
    meta_line = " · ".join(meta)

    lines = [
        "---",
        f"date: {date.isoformat()}",
        "tags: [daily]",
        "---",
        "",
        f"# {date.isoformat()}" + (f"  ({meta_line})" if meta_line else ""),
        "",
        "## Расписание",
    ]
    if lessons:
        for ls in lessons:
            t = (
                f"{ls.start_time}–{ls.end_time}"
                if ls.start_time
                else f"пара {ls.pair_number}"
            )
            room = f" · ауд. {ls.room}" if ls.room else ""
            mark = {"moved": " ⟲", "added": " ➕"}.get(ls.status, "")
            lines.append(
                f"- {t} — [[{_safe(ls.subject_name)}]] ({ls.type}){room}{mark}"
            )
    else:
        lines.append("- пар нет 🎉")

    lines += ["", "## Задачи"]
    if tasks:
        for tk in tasks:
            due = f" (до {tk.due_date.isoformat()})" if tk.due_date else ""
            box = "x" if tk.done else " "
            lines.append(f"- [{box}] {tk.title}{due}")
    else:
        lines.append("- дедлайнов нет")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
