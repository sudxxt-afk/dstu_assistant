"""Нейтральное хранилище вложений лекций (не привязано к Obsidian).

Файлы лежат в /data/media/<предмет>/. Путь к файлу хранится в Attachment.file_path.
Позже отсюда же можно будет заливать в Notion.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import settings

MEDIA = Path(settings.media_path)


def _safe(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    return name or "Без названия"


def media_dir(subject_name: str) -> Path:
    d = MEDIA / _safe(subject_name)
    d.mkdir(parents=True, exist_ok=True)
    return d
