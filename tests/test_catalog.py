from __future__ import annotations

import psycopg

from conftest import TEST_URL


def test_products_and_categories(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["products"]) == 12
    assert body["categories"]
    nuts = [p for p in body["products"] if p["category"] == "nuts"]
    assert len(nuts) == 2
    assert nuts[0]["category_label"] == "Ореховые"
    assert all(p["in_stock"] for p in body["products"])

    filtered = client.get("/api/products?category=nuts").get_json()
    assert len(filtered["products"]) == 2

    found = client.get("/api/products?search=шоколад").get_json()
    assert len(found["products"]) >= 1
    assert all("шоколад" in p["name"].lower() or "шоколад" in p["short_description"].lower()
               for p in found["products"])


def test_product_detail_and_inactive(client):
    detail = client.get("/api/products/klassicheskiy-kubik")
    assert detail.status_code == 200
    assert detail.get_json()["product"]["name"] == "Классический кубик"
    assert client.get("/api/products/nope").status_code == 404

    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute("UPDATE products SET is_active = FALSE WHERE slug = %s", ("klassicheskiy-kubik",))
    assert client.get("/api/products/klassicheskiy-kubik").status_code == 404
    listed = client.get("/api/products").get_json()["products"]
    assert all(p["slug"] != "klassicheskiy-kubik" for p in listed)


def test_cafes_have_map_and_status(client):
    response = client.get("/api/cafes")
    assert response.status_code == 200
    cafes = response.get_json()["cafes"]
    assert len(cafes) == 3
    for cafe in cafes:
        assert 0 <= cafe["map_x"] <= 100
        assert 0 <= cafe["map_y"] <= 100
        assert cafe["status_text"]
        assert isinstance(cafe["is_open"], bool)


def test_promo_percent_fixed_and_errors(client):
    percent = client.post(
        "/api/promos/validate",
        json={"code": "cookie10", "subtotal_cents": 100_000},
    )
    assert percent.status_code == 200
    promo = percent.get_json()["promo"]
    assert promo["discount_cents"] == 10_000
    assert promo["total_cents"] == 90_000
    assert promo["label"] == "−10%"

    below_min = client.post(
        "/api/promos/validate",
        json={"code": "SWEET500", "subtotal_cents": 100_000},
    )
    assert below_min.status_code == 422
    assert "1500" in below_min.get_json()["error"]["message"]

    fixed = client.post(
        "/api/promos/validate",
        json={"code": "SWEET500", "subtotal_cents": 150_000},
    )
    assert fixed.status_code == 200
    assert fixed.get_json()["promo"]["discount_cents"] == 50_000
    assert fixed.get_json()["promo"]["total_cents"] == 100_000

    first = client.post(
        "/api/promos/validate",
        json={"code": "FIRST15", "subtotal_cents": 50_000},
    )
    assert first.get_json()["promo"]["discount_cents"] == 7_500

    unknown = client.post(
        "/api/promos/validate",
        json={"code": "NOPE", "subtotal_cents": 100_000},
    )
    assert unknown.status_code == 422
    assert "не найден" in unknown.get_json()["error"]["message"]


def test_search_is_parameterized(client):
    response = client.get("/api/products?search=%27%20OR%201%3D1%20--")
    assert response.status_code == 200
    assert response.get_json()["products"] == []
