from __future__ import annotations

import hashlib

import psycopg
from psycopg.rows import dict_row

from conftest import TEST_URL, login


def _db():
    return psycopg.connect(TEST_URL, row_factory=dict_row)


def test_health_headers_and_json_404(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json()["db"] is True
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["Referrer-Policy"] == "no-referrer"
    assert health.headers["Cache-Control"] == "no-store"

    missing = client.get("/api/does-not-exist")
    assert missing.status_code == 404
    assert missing.is_json
    assert missing.get_json()["error"]["code"] == "not_found"


def test_cors_allowlist(client):
    allowed = client.options(
        "/api/products",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("Access-Control-Allow-Origin") == "http://localhost:5000"
    assert "authorization" in allowed.headers.get("Access-Control-Allow-Headers", "").lower()
    assert "Origin" in allowed.headers.get("Vary", "")

    denied = client.options(
        "/api/products",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert denied.status_code == 200
    assert denied.headers.get("Access-Control-Allow-Origin") is None


def test_session_token_is_hashed_and_invalid_is_401(client):
    data = login(client, "user@cookiekub.ru", "User123!")
    raw = data["token"]
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with _db() as conn:
        row = conn.execute(
            "SELECT token_hash FROM sessions WHERE token_hash = %s", (digest,)
        ).fetchone()
        assert row is not None
        plain = conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash = %s", (raw,)
        ).fetchone()
        assert plain is None
    assert client.get(
        "/api/auth/me", headers={"Authorization": "Bearer nope"}
    ).status_code == 401


def test_login_rate_limit(app, client):
    app.config["RATE_LIMIT_ENABLED"] = True
    headers = {"X-Forwarded-For": "203.0.113.77"}
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            headers=headers,
            json={"email": "ratelimit@example.com", "password": "WrongPass1"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/auth/login",
        headers=headers,
        json={"email": "ratelimit@example.com", "password": "WrongPass1"},
    )
    assert blocked.status_code == 429
    assert blocked.get_json()["error"]["code"] == "rate_limited"
    assert blocked.get_json()["error"]["details"]["retry_after"] >= 1


def test_maintenance_token_and_retention(client, admin_auth):
    assert client.post("/api/maintenance/purge").status_code == 403
    assert (
        client.post(
            "/api/maintenance/purge", headers={"X-Maintenance-Token": "wrong"}
        ).status_code
        == 403
    )

    data = login(client, "user@cookiekub.ru", "User123!")
    with _db() as conn:
        conn.execute(
            "UPDATE sessions SET expires_at = now() - interval '1 minute' WHERE token_hash = %s",
            (hashlib.sha256(data["token"].encode()).hexdigest(),),
        )
    purge = client.post(
        "/api/maintenance/purge", headers={"X-Maintenance-Token": "test-token"}
    )
    assert purge.status_code == 200
    assert purge.get_json()["deleted"]["sessions"] >= 1
    assert (
        client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"}
        ).status_code
        == 401
    )


def test_maintenance_deletes_old_guest_orders(client):
    order = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": 1, "quantity": 1}],
            "fulfillment": "pickup",
            "cafe_id": 1,
            "customer_name": "Старый Гость",
            "customer_email": "old@example.com",
            "customer_phone": "+7 900 555-44-33",
            "privacy_consent": True,
        },
    ).get_json()["order"]
    with _db() as conn:
        conn.execute(
            "UPDATE orders SET created_at = now() - interval '13 months' WHERE id = %s",
            (order["id"],),
        )
    purge = client.post(
        "/api/maintenance/purge", headers={"X-Maintenance-Token": "test-token"}
    )
    assert purge.status_code == 200
    assert purge.get_json()["deleted"]["guest_orders"] == 1
    assert (
        client.post(
            "/api/orders/lookup",
            json={"number": order["number"], "email": "old@example.com"},
        ).status_code
        == 404
    )


def test_admin_audit_has_no_pii(client, admin_auth):
    client.post(
        "/api/admin/products",
        headers=admin_auth,
        json={"name": "Аудит-кубик", "price_cents": 10000, "category": "classic"},
    )
    entries = client.get("/api/admin/audit", headers=admin_auth).get_json()["entries"]
    product_entry = next(e for e in entries if e["action"] == "product.create")
    details = str(product_entry["details"])
    assert "@" not in details
    assert "+7" not in details
