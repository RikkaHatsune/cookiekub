"""Подключение к PostgreSQL для CookieKub."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:5433/cookiekub"


def database_url() -> str:
    """URL из конфигурации Flask, иначе из окружения (скрипты/миграции)."""
    try:
        from flask import current_app

        configured = current_app.config.get("DATABASE_URL")
        if configured:
            return configured
    except (ImportError, RuntimeError):
        pass
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def connect(url: str | None = None) -> psycopg.Connection:
    """Открывает соединение с dict-строками и коротким таймаутом."""
    return psycopg.connect(
        url or database_url(),
        row_factory=dict_row,
        connect_timeout=5,
        application_name="cookiekub",
    )


@contextmanager
def get_connection(url: str | None = None) -> Iterator[psycopg.Connection]:
    conn = connect(url)
    try:
        yield conn
    finally:
        conn.close()
