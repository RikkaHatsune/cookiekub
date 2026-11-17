"""Сброс dev-БД к чистой схеме и seed-данным."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.connection import connect
from backend.db.migrate import migrate
from backend.db.seed import seed


def main() -> int:
    conn = connect()
    try:
        with conn.transaction():
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
        migrate()
        seed()
    finally:
        conn.close()
    print("RESET OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
