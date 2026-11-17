"""Быстрый smoke-тест backend на тестовой БД (запускается вручную)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "postgresql://postgres@127.0.0.1:5433/cookiekub_test"

from backend.app import create_app  # noqa: E402

app = create_app(
    {
        "TESTING": True,
        "DATABASE_URL": os.environ["DATABASE_URL"],
        "RATE_LIMIT_ENABLED": False,
        "MAINTENANCE_TOKEN": "test-token",
    }
)
c = app.test_client()


def show(label, response):
    body = response.get_json(silent=True)
    print(f"{label}: {response.status_code} {json.dumps(body, ensure_ascii=False)[:400]}")
    return body


def auth(token):
    return {"Authorization": f"Bearer {token}"}


products = show("products", c.get("/api/products"))
assert products and len(products["products"]) == 12
cafes = show("cafes", c.get("/api/cafes"))
assert cafes and len(cafes["cafes"]) == 3

show("bad login", c.post("/api/auth/login", json={"email": "admin@cookiekub.ru", "password": "x"}))
admin = show(
    "admin login",
    c.post(
        "/api/auth/login",
        json={"email": "admin@cookiekub.ru", "password": "Admin123!"},
    ),
)
assert admin["token"]
user = show(
    "user login",
    c.post(
        "/api/auth/login",
        json={"email": "user@cookiekub.ru", "password": "User123!"},
    ),
)

me = show("me", c.get("/api/auth/me", headers=auth(user["token"])))
assert me["user"]["role"] == "user"

promo = show(
    "promo",
    c.post("/api/promos/validate", json={"code": "COOKIE10", "subtotal_cents": 100000}),
)
assert promo["promo"]["discount_cents"] == 10000

order = show(
    "guest order",
    c.post(
        "/api/orders",
        json={
            "items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
            "fulfillment": "pickup",
            "cafe_id": 1,
            "customer_name": "Гость Тестов",
            "customer_email": "guest@example.com",
            "customer_phone": "+7 900 000-00-00",
            "customer_comment": "Без орехов",
            "privacy_consent": True,
            "promo_code": "COOKIE10",
            "payment": {"last4": "4242"},
        },
    ),
)
assert order["order"]["status"] == "processing"
assert order["order"]["discount_cents"] == 4870
number = order["order"]["number"]

show(
    "lookup wrong",
    c.post("/api/orders/lookup", json={"number": number, "email": "other@example.com"}),
)
show(
    "lookup ok",
    c.post("/api/orders/lookup", json={"number": number, "email": "guest@example.com"}),
)

user_order = show(
    "user order",
    c.post(
        "/api/orders",
        headers=auth(user["token"]),
        json={
            "items": [{"product_id": 3, "quantity": 1}],
            "fulfillment": "delivery",
            "delivery_address": "Москва, ул. Тестовая, 1",
            "customer_phone": "+7 900 111-22-33",
            "privacy_consent": True,
            "payment": {"last4": "1111"},
        },
    ),
)
assert user_order["order"]["fulfillment"] == "delivery"
show("my orders", c.get("/api/orders", headers=auth(user["token"])))

print("admin stats", c.get("/api/admin/stats", headers=auth(admin["token"])).status_code)
show(
    "admin complete",
    c.patch(
        f"/api/admin/orders/{order['order']['id']}/status",
        headers=auth(admin["token"]),
        json={"status": "completed"},
    ),
)
show(
    "order after complete",
    c.post("/api/orders/lookup", json={"number": number, "email": "guest@example.com"}),
)

ticket = show(
    "ticket",
    c.post(
        "/api/tickets",
        json={
            "email": "guest@example.com",
            "subject": "Не пришло письмо",
            "category": "question",
            "message": "Проверка тикета, всё ли работает",
        },
    ),
)
assert ticket["ticket"]["id"]

show("admin tickets", c.get("/api/admin/tickets", headers=auth(admin["token"])))
show("audit", c.get("/api/admin/audit", headers=auth(admin["token"])))
show("maintenance no token", c.post("/api/maintenance/purge"))
show(
    "maintenance",
    c.post("/api/maintenance/purge", headers={"X-Maintenance-Token": "test-token"}),
)

print("SMOKE OK")
