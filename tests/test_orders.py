from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from conftest import TEST_URL, login


def _guest_payload(**overrides):
    payload = {
        "items": [{"product_id": 1, "quantity": 2}],
        "fulfillment": "pickup",
        "cafe_id": 1,
        "customer_name": "Гость Печенькин",
        "customer_email": "guest@example.com",
        "customer_phone": "+7 900 123-45-67",
        "privacy_consent": True,
        "payment": {
            "number": "4111 1111 1111 1111",
            "cvv": "123",
            "holder": "GUEST COOKIE",
            "expiry": "12/30",
            "last4": "4242",
        },
    }
    payload.update(overrides)
    return payload


def _db():
    return psycopg.connect(TEST_URL, row_factory=dict_row)


def test_guest_order_saves_only_last4_and_lookup(client):
    response = client.post("/api/orders", json=_guest_payload())
    assert response.status_code == 201, response.get_json()
    order = response.get_json()["order"]
    assert order["status"] == "processing"
    assert order["customer"]["email"] == "guest@example.com"
    assert order["payment"]["last4"] == "4242"
    assert order["payment"]["simulated"] is True
    assert order["payment"]["reference"].startswith("PAY-")
    assert order["items"][0]["quantity"] == 2

    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_number = %s", (order["number"],)
        ).fetchone()
        assert row["card_last4"] == "4242"
        assert row["user_id"] is None
        assert "4111" not in str(dict(row))
        assert "123" != row["card_last4"]

    lookup = client.post(
        "/api/orders/lookup",
        json={"number": order["number"], "email": "guest@example.com"},
    )
    assert lookup.status_code == 200
    assert lookup.get_json()["order"]["number"] == order["number"]

    wrong = client.post(
        "/api/orders/lookup",
        json={"number": order["number"], "email": "other@example.com"},
    )
    assert wrong.status_code == 404
    assert "не найден" in wrong.get_json()["error"]["message"].lower()


def test_guest_order_requires_consent_and_delivery_fields(client):
    no_consent = client.post(
        "/api/orders", json=_guest_payload(privacy_consent=False)
    )
    assert no_consent.status_code == 422
    assert "согласие" in no_consent.get_json()["error"]["message"].lower()

    no_address = client.post(
        "/api/orders", json=_guest_payload(fulfillment="delivery")
    )
    assert no_address.status_code == 422
    assert "адрес" in no_address.get_json()["error"]["message"].lower()

    no_cafe = client.post(
        "/api/orders", json=_guest_payload(cafe_id=None)
    )
    assert no_cafe.status_code == 422


def test_stock_conflict_does_not_change_stock(client):
    with _db() as conn:
        before = conn.execute(
            "SELECT stock_qty FROM products WHERE id = 1"
        ).fetchone()["stock_qty"]
    response = client.post(
        "/api/orders",
        json=_guest_payload(items=[{"product_id": 1, "quantity": before + 1}]),
    )
    assert response.status_code == 409
    with _db() as conn:
        after = conn.execute(
            "SELECT stock_qty FROM products WHERE id = 1"
        ).fetchone()["stock_qty"]
        assert after == before
        assert conn.execute("SELECT count(*) AS n FROM orders").fetchone()["n"] == 0


def test_user_order_uses_account_and_ownership(client, user_auth):
    response = client.post(
        "/api/orders",
        headers=user_auth,
        json={
            "items": [{"product_id": 2, "quantity": 1}],
            "fulfillment": "delivery",
            "delivery_address": "Москва, ул. Песочная, 7",
            "customer_phone": "+7 900 000-00-00",
            "payment": {"last4": "9999"},
        },
    )
    assert response.status_code == 201, response.get_json()
    order = response.get_json()["order"]
    assert order["customer"]["email"] == "user@cookiekub.ru"
    assert order["fulfillment"] == "delivery"
    with _db() as conn:
        row = conn.execute(
            "SELECT user_id, privacy_consent_at FROM orders WHERE order_number = %s",
            (order["number"],),
        ).fetchone()
        assert row["user_id"] is not None
        assert row["privacy_consent_at"] is not None

    mine = client.get("/api/orders", headers=user_auth)
    assert mine.status_code == 200
    assert any(o["number"] == order["number"] for o in mine.get_json()["orders"])

    other = client.post(
        "/api/auth/register",
        json={
            "email": "other@example.com",
            "password": "Secret123!",
            "full_name": "Другой",
            "privacy_consent": True,
        },
    ).get_json()
    other_headers = {"Authorization": f"Bearer {other['token']}"}
    assert client.get(f"/api/orders/{order['number']}", headers=other_headers).status_code == 404
    assert client.get(f"/api/orders/{order['number']}", headers=user_auth).status_code == 200


def test_order_auto_completes_after_delay(app, client):
    created = client.post("/api/orders", json=_guest_payload()).get_json()["order"]
    app.config["ORDER_COMPLETE_DELAY_SECONDS"] = 0
    lookup = client.post(
        "/api/orders/lookup",
        json={"number": created["number"], "email": "guest@example.com"},
    )
    assert lookup.status_code == 200
    assert lookup.get_json()["order"]["status"] == "completed"
    assert lookup.get_json()["order"]["completed_at"]


def test_admin_cancel_restores_stock_and_promo(client, admin_auth):
    created = client.post(
        "/api/orders",
        json=_guest_payload(
            items=[{"product_id": 1, "quantity": 2}],
            promo_code="COOKIE10",
        ),
    ).get_json()["order"]
    with _db() as conn:
        before = conn.execute(
            "SELECT stock_qty FROM products WHERE id = 1"
        ).fetchone()["stock_qty"]
        used = conn.execute(
            "SELECT used_count FROM promos WHERE code = 'COOKIE10'"
        ).fetchone()["used_count"]
        assert used == 1
    response = client.patch(
        f"/api/admin/orders/{created['id']}/status",
        headers=admin_auth,
        json={"status": "cancelled"},
    )
    assert response.status_code == 200
    with _db() as conn:
        after = conn.execute(
            "SELECT stock_qty FROM products WHERE id = 1"
        ).fetchone()["stock_qty"]
        used = conn.execute(
            "SELECT used_count FROM promos WHERE code = 'COOKIE10'"
        ).fetchone()["used_count"]
        order = conn.execute(
            "SELECT status FROM orders WHERE id = %s", (created["id"],)
        ).fetchone()
        assert after == before + 2
        assert used == 0
        assert order["status"] == "cancelled"
        assert conn.execute(
            "SELECT count(*) AS n FROM promo_redemptions WHERE order_id = %s",
            (created["id"],),
        ).fetchone()["n"] == 0


def test_order_requires_items(client):
    response = client.post("/api/orders", json=_guest_payload(items=[]))
    assert response.status_code == 422
    assert "Корзина пуста" in response.get_json()["error"]["message"]
