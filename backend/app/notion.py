"""Односторонний синк лекций в Notion (приложение -> Notion).

Пинится стабильная версия API (database_id-модель). Создание базы — явно через
/notion/setup; sync_lecture пушит/обновляет страницу лекции. Картинки-вложения
пока не заливаются (нужен File Upload API / публичный URL) — только текст и
счётчик вложений. Всё best-effort: ошибки логируются, сохранение лекции не рвут.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import settings
from .db import async_session
from .models import AppMeta, LectureNote

log = logging.getLogger("notion")

API = "https://api.notion.com/v1"
DB_KEY = "notion_lectures_db_id"
_TEXT_LIMIT = 1900  # запас к лимиту Notion 2000 симв/фрагмент
_db_id_cache: str | None = None


def enabled() -> bool:
    return bool(settings.notion_token)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.notion_token}",
        "Notion-Version": settings.notion_version,
        "Content-Type": "application/json",
    }


async def _req(method: str, path: str, json: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.request(method, API + path, headers=_headers(), json=json)
    if r.status_code >= 400:
        raise RuntimeError(f"Notion {method} {path} -> {r.status_code}: {r.text[:300]}")
    return r.json()


# ---------- meta (id созданной базы) ----------
async def _get_meta(key: str) -> str | None:
    async with async_session() as db:
        row = await db.get(AppMeta, key)
        return row.value if row else None


async def _set_meta(key: str, value: str) -> None:
    async with async_session() as db:
        row = await db.get(AppMeta, key)
        if row:
            row.value = value
        else:
            db.add(AppMeta(key=key, value=value))
        await db.commit()


# ---------- база ----------
async def ensure_database(create: bool = False) -> str | None:
    """Вернуть id базы лекций. create=True — создать, если её ещё нет."""
    global _db_id_cache
    if _db_id_cache:
        return _db_id_cache

    stored = await _get_meta(DB_KEY)
    if stored:
        try:
            db = await _req("GET", f"/databases/{stored}")
            if not db.get("archived"):
                _db_id_cache = stored
                return stored
        except RuntimeError as e:
            log.warning("stored Notion DB недоступна: %s", e)

    if not create:
        return None
    if not settings.notion_parent_page_id:
        raise RuntimeError("NOTION_PARENT_PAGE_ID не задан в .env")

    payload = {
        "parent": {"type": "page_id", "page_id": settings.notion_parent_page_id},
        "title": [{"type": "text", "text": {"content": "Лекции DSTU"}}],
        "icon": {"type": "emoji", "emoji": "📚"},
        "properties": {
            "Name": {"title": {}},
            "Предмет": {"select": {}},
            "Дата": {"date": {}},
            "Пара": {"number": {}},
            "Вложений": {"number": {}},
        },
    }
    created = await _req("POST", "/databases", payload)
    db_id = created["id"]
    await _set_meta(DB_KEY, db_id)
    _db_id_cache = db_id
    log.info("Создана база лекций в Notion: %s", db_id)
    return db_id


# ---------- блоки из текста ----------
def _chunks(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _blocks(content: str, n_attach: int) -> list[dict]:
    blocks: list[dict] = []
    for para in (content or "").split("\n\n"):
        para = para.strip("\n")
        if not para.strip():
            continue
        for chunk in _chunks(para, _TEXT_LIMIT):
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": chunk}}
                        ]
                    },
                }
            )
    if n_attach:
        blocks.append(
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "📎"},
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Вложений в приложении: {n_attach}"
                            },
                        }
                    ],
                },
            }
        )
    return blocks[:100]  # Notion: не больше 100 детей за раз


def _props(note: LectureNote, subject_name: str, n_attach: int) -> dict:
    title = f"{subject_name} · {note.date.isoformat()}"
    props: dict = {
        "Name": {"title": [{"type": "text", "text": {"content": title}}]},
        "Предмет": {"select": {"name": subject_name.replace(",", " ")[:100]}},
        "Дата": {"date": {"start": note.date.isoformat()}},
        "Вложений": {"number": n_attach},
    }
    if note.pair_number:
        props["Пара"] = {"number": note.pair_number}
    return props


async def _clear_children(page_id: str) -> None:
    data = await _req("GET", f"/blocks/{page_id}/children?page_size=100")
    for block in data.get("results", []):
        try:
            await _req("DELETE", f"/blocks/{block['id']}")
        except RuntimeError as e:
            log.warning("не удалить блок: %s", e)


# ---------- синк одной лекции ----------
async def sync_lecture(note_id: int) -> None:
    if not enabled():
        return
    try:
        db_id = await ensure_database(create=False)
        if not db_id:
            log.info("Notion не настроен (нет базы) — пропуск синка лекции %s", note_id)
            return

        async with async_session() as db:
            q = (
                select(LectureNote)
                .options(
                    selectinload(LectureNote.subject),
                    selectinload(LectureNote.attachments),
                )
                .where(LectureNote.id == note_id)
            )
            note = (await db.execute(q)).scalar_one_or_none()
            if not note:
                return
            subject_name = note.subject.name if note.subject else "Без предмета"
            n_attach = len(note.attachments)
            page_id = note.notion_page_id
            props = _props(note, subject_name, n_attach)
            blocks = _blocks(note.content_md, n_attach)

        if page_id:
            await _req("PATCH", f"/pages/{page_id}", {"properties": props})
            await _clear_children(page_id)
            if blocks:
                await _req(
                    "PATCH", f"/blocks/{page_id}/children", {"children": blocks}
                )
            url = None
        else:
            created = await _req(
                "POST",
                "/pages",
                {
                    "parent": {"database_id": db_id},
                    "properties": props,
                    "children": blocks,
                },
            )
            page_id = created["id"]
            url = created.get("url")

        async with async_session() as db:
            note = await db.get(LectureNote, note_id)
            if note:
                note.notion_page_id = page_id
                if url:
                    note.notion_url = url
                await db.commit()
        log.info("Синхронизирована лекция %s -> Notion %s", note_id, page_id)
    except Exception as e:  # noqa: BLE001
        log.warning("sync_lecture %s failed: %s", note_id, e)


async def archive_page(page_id: str | None) -> None:
    if not enabled() or not page_id:
        return
    try:
        await _req("PATCH", f"/pages/{page_id}", {"archived": True})
    except Exception as e:  # noqa: BLE001
        log.warning("archive_page %s failed: %s", page_id, e)


async def sync_all() -> dict:
    """Пройтись по всем лекциям и запушить/обновить их. Возвращает счётчики."""
    if not enabled():
        return {"ok": False, "error": "notion token не задан"}
    db_id = await ensure_database(create=True)
    if not db_id:
        return {"ok": False, "error": "не удалось получить базу"}
    async with async_session() as db:
        ids = (
            await db.execute(select(LectureNote.id).order_by(LectureNote.id))
        ).scalars().all()
    ok = 0
    for nid in ids:
        await sync_lecture(nid)
        ok += 1
    return {"ok": True, "synced": ok}
