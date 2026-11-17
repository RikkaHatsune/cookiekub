from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from conftest import TEST_URL, login


def _db():
    return psycopg.connect(TEST_URL, row_factory=dict_row)


def test_register_hashes_password_and_returns_session(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "password": "Secret123!",
            "full_name": "Новый Гость",
            "privacy_consent": True,
        },
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["role"] == "user"
    assert body["user"]["email"] == "new@example.com"
    assert body["token"]
    with _db() as conn:
        row = conn.execute(
            "SELECT password_hash, privacy_consent_at FROM users WHERE email = %s",
            ("new@example.com",),
        ).fetchone()
        assert row["password_hash"].startswith("scrypt:")
        assert "Secret123!" not in row["password_hash"]
        assert row["privacy_consent_at"] is not None
        token_row = conn.execute(
            "SELECT token_hash FROM sessions WHERE token_hash = %s",
            (__import__("hashlib").sha256(body["token"].encode()).hexdigest(),),
        ).fetchone()
        assert token_row is not None


def test_register_duplicate_and_consent(client):
    payload = {
        "email": "dup@example.com",
        "password": "Secret123!",
        "full_name": "Дубль",
        "privacy_consent": True,
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409
    payload["email"] = "noconsent@example.com"
    payload["privacy_consent"] = False
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert "согласие" in response.get_json()["error"]["message"].lower()


def test_login_is_generic_and_logout_revokes(client, user_auth):
    wrong = client.post(
        "/api/auth/login",
        json={"email": "user@cookiekub.ru", "password": "WrongPass1"},
    )
    assert wrong.status_code == 401
    assert wrong.get_json()["error"]["message"] == "Неверный email или пароль"

    missing = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass1"},
    )
    assert missing.status_code == 401
    assert missing.get_json()["error"]["message"] == "Неверный email или пароль"

    assert client.get("/api/auth/me", headers=user_auth).status_code == 200
    assert client.post("/api/auth/logout", headers=user_auth).status_code == 200
    assert client.get("/api/auth/me", headers=user_auth).status_code == 401


def test_change_password_revokes_all_sessions(client, user_auth):
    response = client.post(
        "/api/auth/change-password",
        headers=user_auth,
        json={"current_password": "User123!", "new_password": "NewUser123!"},
    )
    assert response.status_code == 200
    assert response.get_json()["relogin"] is True
    assert client.get("/api/auth/me", headers=user_auth).status_code == 401

    old = client.post(
        "/api/auth/login",
        json={"email": "user@cookiekub.ru", "password": "User123!"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/auth/login",
        json={"email": "user@cookiekub.ru", "password": "NewUser123!"},
    )
    assert new.status_code == 200


def test_delete_account_anonymizes_user_and_order(client):
    registered = client.post(
        "/api/auth/register",
        json={
            "email": "delete-me@example.com",
            "password": "Secret123!",
            "full_name": "Удаляемый",
            "privacy_consent": True,
        },
    ).get_json()
    headers = {"Authorization": f"Bearer {registered['token']}"}
    order = client.post(
        "/api/orders",
        headers=headers,
        json={
            "items": [{"product_id": 1, "quantity": 1}],
            "fulfillment": "pickup",
            "cafe_id": 1,
            "customer_phone": "+7 900 123-45-67",
            "privacy_consent": True,
        },
    )
    assert order.status_code == 201
    number = order.get_json()["order"]["number"]

    response = client.delete(
        "/api/auth/account", headers=headers, json={"password": "Secret123!"}
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401

    with _db() as conn:
        user = conn.execute(
            "SELECT email, full_name, is_active, anonymized_at FROM users WHERE id = %s",
            (registered["user"]["id"],),
        ).fetchone()
        assert user["email"].startswith("deleted+")
        assert user["full_name"] == "Удалённый пользователь"
        assert user["is_active"] is False
        assert user["anonymized_at"] is not None
        order_row = conn.execute(
            "SELECT customer_name, customer_email FROM orders WHERE order_number = %s",
            (number,),
        ).fetchone()
        assert order_row["customer_name"] == "Удалённый пользователь"
        assert order_row["customer_email"].startswith("deleted+")


def test_blocked_user_cannot_login_or_use_old_token(client, admin_auth, user_auth):
    user = login(client, "user@cookiekub.ru", "User123!")
    response = client.patch(
        f"/api/admin/users/{user['user']['id']}",
        headers=admin_auth,
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me", headers=user_auth).status_code == 401
    blocked = client.post(
        "/api/auth/login",
        json={"email": "user@cookiekub.ru", "password": "User123!"},
    )
    assert blocked.status_code == 401
