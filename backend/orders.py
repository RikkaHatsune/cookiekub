"""Заказы: гостевой и пользовательский checkout, lookup, авто-завершение."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from flask import Blueprint, current_app, g

from .errors import ApiError, conflict, not_found, unauthorized, validation_error
from .extensions import get_db
from .pricing import promo_discount
from .security import rate_limit, require_user
from .serializers import MOSCOW, order_json
from .validators import (
    body,
    boolean,
    email,
    integer,
    phone,
    text,
)

bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def maybe_complete_orders(conn) -> None:
    delay = int(current_app.config.get("ORDER_COMPLETE_DELAY_SECONDS", 60))
    result = conn.execute(
        """
        UPDATE orders
        SET status = 'completed', completed_at = now()
        WHERE status = 'processing'
          AND paid_at IS NOT NULL
          AND paid_at + make_interval(secs => %s) <= now()
        """,
        (delay,),
    )
    if result.rowcount:
        conn.commit()


def _items(data: dict) -> list[tuple[int, int]]:
    raw = data.get("items")
    if not isinstance(raw, list) or not raw:
        raise validation_error("Корзина пуста")
    if len(raw) > 50:
        raise validation_error("Слишком много позиций в заказе")
    merged: dict[int, int] = {}
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise validation_error(f"Позиция {index} должна быть объектом")
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if isinstance(product_id, bool) or not isinstance(product_id, int):
            raise validation_error(f"Позиция {index}: неверный product_id")
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise validation_error(f"Позиция {index}: неверное количество")
        if not 1 <= quantity <= 99:
            raise validation_error(f"Позиция {index}: количество от 1 до 99")
        merged[product_id] = merged.get(product_id, 0) + quantity
        if merged[product_id] > 99:
            raise validation_error("Слишком много одной печеньки")
    return list(merged.items())


def _last4(data: dict) -> str | None:
    payment = data.get("payment")
    raw = None
    if isinstance(payment, dict):
        raw = payment.get("last4")
    if raw is None:
        raw = data.get("card_last4")
    if raw in (None, ""):
        return None
    if not isinstance(raw, str) or not (raw.isdigit() and len(raw) == 4):
        return None
    return raw


def _checkout(conn, user, data: dict):
    items = _items(data)
    fulfillment = data.get("fulfillment", "pickup")
    if fulfillment not in {"pickup", "delivery"}:
        raise validation_error("Способ получения: pickup или delivery")

    cafe = None
    delivery_address = None
    if fulfillment == "pickup":
        cafe_id = integer(data, "cafe_id", minimum=1)
        cafe = conn.execute(
            "SELECT * FROM cafes WHERE id = %s AND is_active = TRUE", (cafe_id,)
        ).fetchone()
        if not cafe:
            raise validation_error("Выберите кафе для самовывоза")
    else:
        delivery_address = text(
            data, "delivery_address", required=True, min_len=5, max_len=300
        )

    if user:
        customer_name = text(
            data, "customer_name", required=False, max_len=120
        ) or user["full_name"] or "Гость"
        # Email заказа у авторизованного пользователя всегда из аккаунта:
        # так гостевая форма lookup не привяжет чужой заказ к произвольному адресу.
        customer_email = user["email"]
        consent = user["privacy_consent_at"] is not None or boolean(
            data, "privacy_consent"
        )
        consent_at = user["privacy_consent_at"] or (
            datetime.now(timezone.utc) if consent else None
        )
        if not consent:
            raise validation_error("Нужно согласие на обработку персональных данных")
    else:
        customer_name = text(
            data, "customer_name", required=True, min_len=2, max_len=120
        )
        customer_email = email(data, "customer_email")
        consent_at = datetime.now(timezone.utc) if boolean(data, "privacy_consent") else None
        if not consent_at:
            raise validation_error("Нужно согласие на обработку персональных данных")

    customer_phone = phone(data, "customer_phone", required=True)
    customer_comment = text(data, "customer_comment", max_len=500, default="")

    products = conn.execute(
        "SELECT * FROM products WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
        ([pid for pid, _ in items],),
    ).fetchall()
    by_id = {row["id"]: row for row in products}
    for product_id, quantity in items:
        product = by_id.get(product_id)
        if not product or not product["is_active"]:
            raise conflict("Одна из печенек больше не продаётся")
        if product["stock_qty"] < quantity:
            raise conflict(f"«{product['name']}»: осталось {product['stock_qty']} шт.")

    subtotal = sum(by_id[pid]["price_cents"] * qty for pid, qty in items)
    promo = None
    discount = 0
    promo_code = text(data, "promo_code", required=False, max_len=40).upper() or None
    if promo_code:
        promo = conn.execute(
            "SELECT * FROM promos WHERE upper(code) = %s FOR UPDATE", (promo_code,)
        ).fetchone()
        if not promo:
            raise validation_error("Промокод не найден")
        discount = promo_discount(promo, subtotal)
    total = subtotal - discount

    seq = conn.execute("SELECT nextval('order_number_seq') AS n").fetchone()["n"]
    date_part = datetime.now(MOSCOW).strftime("%Y%m%d")
    order_number = f"CK-{date_part}-{seq:04d}"
    payment_ref = f"SIM-{secrets.token_hex(5).upper()}"
    last4 = _last4(data)

    order = conn.execute(
        """
        INSERT INTO orders (
            order_number, user_id, customer_name, customer_email, customer_phone,
            customer_comment, fulfillment, cafe_id, delivery_address, status,
            subtotal_cents, discount_cents, total_cents, promo_id, promo_code,
            payment_ref, card_last4, privacy_consent_at, paid_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, 'processing',
            %s, %s, %s, %s, %s, %s, %s, %s, now()
        )
        RETURNING *
        """,
        (
            order_number,
            user["id"] if user else None,
            customer_name,
            customer_email,
            customer_phone,
            customer_comment,
            fulfillment,
            cafe["id"] if cafe else None,
            delivery_address,
            subtotal,
            discount,
            total,
            promo["id"] if promo else None,
            promo["code"] if promo else None,
            payment_ref,
            last4,
            consent_at,
        ),
    ).fetchone()

    for pid, qty in items:
        conn.execute(
            """
            INSERT INTO order_items (order_id, product_id, product_name, unit_price_cents,
                                     quantity, line_total_cents)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                order["id"],
                pid,
                by_id[pid]["name"],
                by_id[pid]["price_cents"],
                qty,
                by_id[pid]["price_cents"] * qty,
            ),
        )
    for product_id, quantity in items:
        conn.execute(
            "UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s",
            (quantity, product_id),
        )

    if promo:
        conn.execute(
            "INSERT INTO promo_redemptions (promo_id, order_id, user_id) VALUES (%s, %s, %s)",
            (promo["id"], order["id"], user["id"] if user else None),
        )
        conn.execute(
            "UPDATE promos SET used_count = used_count + 1 WHERE id = %s",
            (promo["id"],),
        )
    if user and user["privacy_consent_at"] is None:
        conn.execute(
            "UPDATE users SET privacy_consent_at = %s WHERE id = %s",
            (consent_at, user["id"]),
        )

    return order


@bp.post("")
def create_order():
    rate_limit("order", 10, 60)
    data = body()
    user = g.get("user")
    conn = get_db()
    try:
        with conn.transaction():
            order = _checkout(conn, user, data)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    fresh = conn.execute(
        "SELECT * FROM orders WHERE id = %s", (order["id"],)
    ).fetchone()
    return {"order": order_json(conn, fresh)}, 201


@bp.get("")
def my_orders():
    user = g.get("user")
    require_user(user)
    conn = get_db()
    maybe_complete_orders(conn)
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
        (user["id"],),
    ).fetchall()
    return {"orders": [order_json(conn, row, include_customer=False) for row in rows]}


@bp.post("/lookup")
def lookup_order():
    rate_limit("lookup", 15, 60)
    data = body()
    number = text(data, "number", required=True, max_len=40).upper()
    email_value = email(data)
    conn = get_db()
    maybe_complete_orders(conn)
    row = conn.execute(
        "SELECT * FROM orders WHERE order_number = %s AND lower(customer_email) = %s",
        (number, email_value),
    ).fetchone()
    if not row:
        raise not_found("Заказ не найден. Проверьте номер и email.")
    return {"order": order_json(conn, row)}


@bp.get("/<number>")
def get_order(number: str):
    user = g.get("user")
    require_user(user)
    conn = get_db()
    maybe_complete_orders(conn)
    row = conn.execute(
        "SELECT * FROM orders WHERE order_number = %s", (number.upper(),)
    ).fetchone()
    if not row:
        raise not_found("Заказ не найден")
    if user["role"] != "admin" and row["user_id"] != user["id"]:
        # Не раскрываем существование чужого заказа.
        raise not_found("Заказ не найден")
    return {"order": order_json(conn, row)}


@bp.get("/<number>/receipt")
def receipt(number: str):
    user = g.get("user")
    require_user(user)
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_number = %s", (number.upper(),)
    ).fetchone()
    if not row:
        raise not_found("Заказ не найден")
    if user["role"] != "admin" and row["user_id"] != user["id"]:
        raise not_found("Заказ не найден")
    return {"order": order_json(conn, row)}
