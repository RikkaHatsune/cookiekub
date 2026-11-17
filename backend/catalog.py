"""Публичный каталог: печеньки, кафе и проверка промокодов."""
from __future__ import annotations

from flask import Blueprint, request

from .errors import not_found, validation_error
from .extensions import get_db
from .pricing import promo_discount, promo_json
from .security import rate_limit
from .serializers import PRODUCT_CATEGORIES, cafe_json, product_json
from .validators import body, integer, text

bp = Blueprint("catalog", __name__, url_prefix="/api")


@bp.get("/products")
def products():
    conn = get_db()
    category = (request.args.get("category") or "").strip()
    search = (request.args.get("search") or "").strip()
    conditions = ["is_active = TRUE"]
    params: list = []
    if category and category != "all":
        conditions.append("category = %s")
        params.append(category)
    if search:
        conditions.append("(name ILIKE %s OR short_description ILIKE %s)")
        like = f"%{search}%"
        params.extend([like, like])
    rows = conn.execute(
        f"""
        SELECT * FROM products
        WHERE {' AND '.join(conditions)}
        ORDER BY sort_order, id
        """,
        params,
    ).fetchall()
    categories = [
        {"value": key, "label": label}
        for key, label in PRODUCT_CATEGORIES.items()
    ]
    return {"products": [product_json(row) for row in rows], "categories": categories}


@bp.get("/products/<slug>")
def product(slug: str):
    row = get_db().execute(
        "SELECT * FROM products WHERE slug = %s AND is_active = TRUE", (slug,)
    ).fetchone()
    if not row:
        raise not_found("Печенька не найдена")
    return {"product": product_json(row)}


@bp.get("/cafes")
def cafes():
    rows = get_db().execute(
        "SELECT * FROM cafes WHERE is_active = TRUE ORDER BY sort_order, id"
    ).fetchall()
    return {"cafes": [cafe_json(row) for row in rows]}


@bp.post("/promos/validate")
def validate_promo():
    rate_limit("promo", 30, 60)
    data = body()
    code = text(data, "code", required=True, max_len=40).upper()
    subtotal = integer(data, "subtotal_cents", minimum=0, maximum=10_000_000)
    conn = get_db()
    promo = conn.execute(
        "SELECT * FROM promos WHERE upper(code) = %s", (code,)
    ).fetchone()
    if not promo:
        raise validation_error("Промокод не найден")
    discount = promo_discount(promo, subtotal or 0)
    return {"promo": promo_json(promo, discount, (subtotal or 0) - discount)}
