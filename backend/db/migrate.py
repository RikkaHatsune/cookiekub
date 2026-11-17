"""Раннер SQL-миграций CookieKub.

Запуск:  python -m backend.db.migrate
Повторный запуск безопасен: применённые версии пропускаются.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .connection import connect, database_url

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def ensure_migrations_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.commit()


def applied_versions(conn) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def migrate(url: str | None = None, verbose: bool = True) -> list[str]:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        raise RuntimeError(f"Не найдено миграций в {MIGRATIONS_DIR}")

    applied: list[str] = []
    with connect(url) as conn:
        ensure_migrations_table(conn)
        done = applied_versions(conn)
        for path in migration_files:
            version = path.name
            if version in done:
                if verbose:
                    print(f"  = {version} (уже применена)")
                continue
            sql = path.read_text(encoding="utf-8")
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
                )
            applied.append(version)
            if verbose:
                print(f"  + {version}")
    return applied


def main() -> int:
    print(f"База: {database_url()}")
    print(f"Миграции: {MIGRATIONS_DIR}")
    try:
        applied = migrate()
    except Exception as exc:  # noqa: BLE001 — CLI должен показать причину
        print(f"ОШИБКА миграций: {exc}", file=sys.stderr)
        return 1
    if applied:
        print(f"Применено миграций: {len(applied)}")
    else:
        print("Схема уже актуальна.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
