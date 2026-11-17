"""Per-request подключение к PostgreSQL."""
from __future__ import annotations

from flask import current_app, g

from .db.connection import connect


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_URL"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()
