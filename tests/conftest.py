"""Общие фикстуры pytest: отдельная БД, чистое состояние перед каждым тестом."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/cookiekub_test"
)
os.environ["DATABASE_URL"] = TEST_URL

from backend.app import create_app  # noqa: E402
from backend.db.migrate import migrate  # noqa: E402
from backend.db.seed import seed  # noqa: E402

TABLES = (
    "users, sessions, products, promos, cafes, orders, order_items, "
    "promo_redemptions, tickets, admin_audit"
)


def _reset_database() -> None:
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
        conn.execute("ALTER SEQUENCE order_number_seq RESTART WITH 1")
    seed(TEST_URL, verbose=False)


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    migrate(TEST_URL, verbose=False)
    seed(TEST_URL, verbose=False)
    yield


@pytest.fixture()
def app(prepare_database):
    _reset_database()
    application = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": TEST_URL,
            "RATE_LIMIT_ENABLED": False,
            "MAINTENANCE_TOKEN": "test-token",
            "ORDER_COMPLETE_DELAY_SECONDS": 60,
        }
    )
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email: str, password: str):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


@pytest.fixture()
def admin_auth(client):
    data = login(client, "admin@cookiekub.ru", "Admin123!")
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture()
def user_auth(client):
    data = login(client, "user@cookiekub.ru", "User123!")
    return {"Authorization": f"Bearer {data['token']}"}
