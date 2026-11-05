from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    allowed_user_id: int | None = None
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
    api_token: str = "change-me"

    tz: str = "Europe/Moscow"
    database_url: str = "sqlite+aiosqlite:////data/app.db"
    vault_path: str = "/data/vault"
    media_path: str = "/data/media"  # вложения лекций (нейтральное хранилище, не Obsidian)


settings = Settings()
