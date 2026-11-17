"""Конфигурация Flask-приложения CookieKub."""
from __future__ import annotations

import os

try:  # python-dotenv есть в requirements, но приложение не должно падать без него
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env_list(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cookiekub-dev-secret-change-me")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/cookiekub"
    )
    APP_ENV = os.environ.get("APP_ENV", "development")
    SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@cookiekub.ru")
    ORDER_COMPLETE_DELAY_SECONDS = int(
        os.environ.get("ORDER_COMPLETE_DELAY_SECONDS", "60")
    )
    SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "7"))
    MAINTENANCE_TOKEN = os.environ.get("MAINTENANCE_TOKEN", "dev-maintenance-token")
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    CORS_ORIGINS = _env_list(
        "CORS_ORIGINS",
        "http://127.0.0.1:5000,http://localhost:5000,"
        "http://127.0.0.1:8000,http://localhost:8000",
    )
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    JSON_SORT_KEYS = False
