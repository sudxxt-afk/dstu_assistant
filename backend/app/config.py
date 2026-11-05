from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    allowed_user_id: int | None = None
    # ID пользователей «только для чтения» (одногруппники): видят лишь расписание
    # и получают утреннее уведомление + напоминания о парах. Строка CSV в .env,
    # разобранный список — в свойстве readonly_ids (str, т.к. pydantic-settings
    # пытается JSON-парсить env для сложных типов вроде list[int]).
    readonly_user_ids: str = ""
    # Кастомный адрес Telegram Bot API (напр. Cloudflare Worker-прокси).
    # Пусто -> штатный api.telegram.org.
    telegram_api_base: str = ""
    # Пароль для входа в веб-панель (обменивается на api_token через /auth/login).
    panel_password: str = ""

    @field_validator("allowed_user_id", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        # Пустая строка в .env (ALLOWED_USER_ID=) -> None
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @property
    def readonly_ids(self) -> list[int]:
        # "1058333123, 222" -> [1058333123, 222]; пусто -> []
        raw = self.readonly_user_ids or ""
        return [int(x) for x in raw.replace(";", ",").split(",") if x.strip()]
    api_token: str = "change-me"

    tz: str = "Europe/Moscow"
    database_url: str = "sqlite+aiosqlite:////data/app.db"
    vault_path: str = "/data/vault"
    media_path: str = "/data/media"  # вложения лекций (нейтральное хранилище, не Obsidian)

    # --- Notion-синк лекций (одностороннее: приложение -> Notion) ---
    notion_token: str = ""  # Internal Integration Secret (ntn_… / secret_…)
    notion_parent_page_id: str = ""  # страница-родитель, где создаётся база
    notion_version: str = "2022-06-28"  # стабильная версия (модель database_id)
    # Прокси для обхода блокировки api.notion.com по SNI (как TG-воркер).
    # Пусто -> штатный https://api.notion.com. Указывать origin воркера.
    notion_api_base: str = ""


settings = Settings()
