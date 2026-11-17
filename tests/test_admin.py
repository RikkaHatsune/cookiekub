from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from conftest import TEST_URL


def _db():
    return psycopg.connect(TEST_URL, row_factory=dict_row)


def test_admin_endpoints_require_admin(client, user_auth):
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/stats", headers=user_auth).status_code == 403
    assert client.get("/api/admin/products", headers=user_auth).status_code == 403
    assert client.get("/api/admin/users", headers=user_auth).status_code == 403


def test_admin_stats_and_product_crud(client, admin_auth):
    stats = client.get("/api/admin/stats", headers=admin_auth)
    assert stats.status_code == 200
    assert stats.get_json()["stats"]["products"] == 12

    created = client.post(
        "/api/admin/products",
        headers=admin_auth,
        json={
            "name": "Тестовый кубик",
            "price_cents": 12345,
            "category": "nuts",
            "stock_qty": 7,
            "short_description": "Для теста",
            "description": "Описание",
        },
    )
    assert created.status_code == 201, created.get_json()
    product = created.get_json()["product"]
    assert product["slug"] == "testovyy-kubik"
    assert product["category_label"] == "Ореховые"
    assert product["in_stock"] is True

    updated = client.patch(
        f"/api/admin/products/{product['id']}",
        headers=admin_auth,
        json={"price_cents": 15000, "stock_qty": 0},
    )
    assert updated.status_code == 200
    assert updated.get_json()["product"]["price_cents"] == 15000
    assert updated.get_json()["product"]["in_stock"] is False

    archived = client.delete(
        f"/api/admin/products/{product['id']}", headers=admin_auth
    )
    assert archived.status_code == 200
    assert client.get(f"/api/products/{product['slug']}").status_code == 404

    audit = client.get("/api/admin/audit", headers=admin_auth).get_json()["entries"]
    actions = {entry["action"] for entry in audit}
    assert "product.create" in actions
    assert "product.update" in actions
    assert "product.archive" in actions


def test_admin_promo_create_update_type(client, admin_auth):
    created = client.post(
        "/api/admin/promos",
        headers=admin_auth,
        json={
            "code": "testpromo",
            "discount_type": "fixed",
            "amount_cents": 25000,
            "min_order_cents": 100000,
            "max_uses": 5,
        },
    )
    assert created.status_code == 201, created.get_json()
    promo_id = created.get_json()["promo"]["id"]

    duplicate = client.post(
        "/api/admin/promos",
        headers=admin_auth,
        json={
            "code": "TESTPROMO",
            "discount_type": "percent",
            "percent_value": 10,
        },
    )
    assert duplicate.status_code == 409

    switched = client.patch(
        f"/api/admin/promos/{promo_id}",
        headers=admin_auth,
        json={"discount_type": "percent", "percent_value": 20},
    )
    assert switched.status_code == 200, switched.get_json()
    with _db() as conn:
        row = conn.execute(
            "SELECT discount_type, percent_value, amount_cents FROM promos WHERE id = %s",
            (promo_id,),
        ).fetchone()
        assert row["discount_type"] == "percent"
        assert row["percent_value"] == 20
        assert row["amount_cents"] is None

    archived = client.delete(f"/api/admin/promos/{promo_id}", headers=admin_auth)
    assert archived.status_code == 200


def test_admin_users_block_and_last_admin_guard(client, admin_auth, user_auth):
    me = client.get("/api/auth/me", headers=admin_auth).get_json()["user"]
    own = client.patch(
        f"/api/admin/users/{me['id']}", headers=admin_auth, json={"role": "user"}
    )
    assert own.status_code == 422

    user = client.get("/api/auth/me", headers=user_auth).get_json()["user"]
    blocked = client.patch(
        f"/api/admin/users/{user['id']}", headers=admin_auth, json={"is_active": False}
    )
    assert blocked.status_code == 200
    assert client.get("/api/auth/me", headers=user_auth).status_code == 401

    # Админ не может удалить сам себя через админку.
    assert client.delete(f"/api/admin/users/{me['id']}", headers=admin_auth).status_code == 422


def test_tickets_public_and_admin_reply(client, admin_auth, user_auth):
    public = client.post(
        "/api/tickets",
        json={
            "email": "bug@example.com",
            "subject": "Кнопка не нажимается",
            "category": "bug",
            "message": "На странице каталога кнопка зависла.",
        },
    )
    assert public.status_code == 201
    body = public.get_json()
    assert body["ticket"]["status"] == "open"
    assert body["simulated_email"]["to"] == "support@cookiekub.ru"
    ticket_id = body["ticket"]["id"]

    mine = client.post(
        "/api/tickets",
        headers=user_auth,
        json={
            "subject": "Вопрос по заказу",
            "category": "question",
            "message": "Когда будет готов заказ?",
        },
    )
    assert mine.status_code == 201
    assert mine.get_json()["ticket"]["status"] == "open"
    assert client.get("/api/tickets/my", headers=user_auth).status_code == 200

    listed = client.get("/api/admin/tickets", headers=admin_auth)
    assert listed.status_code == 200
    assert any(t["id"] == ticket_id for t in listed.get_json()["tickets"])

    replied = client.patch(
        f"/api/admin/tickets/{ticket_id}",
        headers=admin_auth,
        json={"admin_reply": "Спасибо, проверяем"},
    )
    assert replied.status_code == 200
    assert replied.get_json()["ticket"]["status"] == "answered"
    assert replied.get_json()["ticket"]["admin_reply"] == "Спасибо, проверяем"

    audit = client.get("/api/admin/audit", headers=admin_auth).get_json()["entries"]
    assert any(entry["action"] == "ticket.update" for entry in audit)


def test_admin_completes_order(client, admin_auth):
    created = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": 1, "quantity": 1}],
            "fulfillment": "pickup",
            "cafe_id": 1,
            "customer_name": "Гость",
            "customer_email": "guest2@example.com",
            "customer_phone": "+7 900 111-22-33",
            "privacy_consent": True,
        },
    ).get_json()["order"]
    response = client.patch(
        f"/api/admin/orders/{created['id']}/status",
        headers=admin_auth,
        json={"status": "completed"},
    )
    assert response.status_code == 200, response.get_json()
    order = response.get_json()["order"]
    assert order["status"] == "completed"
    assert order["completed_at"]

    cancelled_back = client.patch(
        f"/api/admin/orders/{created['id']}/status",
        headers=admin_auth,
        json={"status": "processing"},
    )
    assert cancelled_back.status_code == 200
