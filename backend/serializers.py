"""Сериализация строк БД в JSON API."""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

MOSCOW = ZoneInfo("Europe/Moscow")

ORDER_STATUS_LABELS = {
    "processing": "В обработке",
    "completed": "Выполнен",
    "cancelled": "Отменён",
}

PRODUCT_CATEGORIES = {
    "classic": "Классика",
    "chocolate": "Шоколад",
    "fruit": "Фруктовые",
    "nuts": "Ореховые",
    "vegan": "Веган",
    "gift": "Подарочные",
}


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")


def _time_text(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def _decimal(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def user_json(user) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "created_at": iso(user["created_at"]),
        "privacy_consent_at": iso(user.get("privacy_consent_at")),
    }


def product_json(row) -> dict:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "short_description": row["short_description"],
        "description": row["description"],
        "price_cents": row["price_cents"],
        "image_url": row["image_url"],
        "category": row["category"],
        "category_label": PRODUCT_CATEGORIES.get(row["category"], row["category"]),
        "stock_qty": row["stock_qty"],
        "in_stock": row["stock_qty"] > 0,
        "is_active": row["is_active"],
        "sort_order": row["sort_order"],
    }


def cafe_open_state(row, now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(MOSCOW)
    opens: time = row["opens_at"]
    closes: time = row["closes_at"]
    current = now.time().replace(tzinfo=None)
    if opens <= closes:
        is_open = opens <= current < closes
    else:
        is_open = current >= opens or current < closes

    if is_open:
        return True, f"Открыто · до {_time_text(closes)}"
    if current < opens:
        return False, f"Закрыто · откроемся в {_time_text(opens)}"
    return False, f"Закрыто · откроемся завтра в {_time_text(opens)}"


def cafe_json(row, now: datetime | None = None) -> dict:
    is_open, status = cafe_open_state(row, now)
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "address": row["address"],
        "phone": row["phone"],
        "opens_at": _time_text(row["opens_at"]),
        "closes_at": _time_text(row["closes_at"]),
        "map_x": _decimal(row["map_x"]),
        "map_y": _decimal(row["map_y"]),
        "is_open": is_open,
        "status_text": status,
        "is_active": row["is_active"],
    }


def order_items(conn, order_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT product_id, product_name, unit_price_cents, quantity, line_total_cents
        FROM order_items WHERE order_id = %s ORDER BY id
        """,
        (order_id,),
    ).fetchall()
    return [
        {
            "product_id": row["product_id"],
            "name": row["product_name"],
            "unit_price_cents": row["unit_price_cents"],
            "quantity": row["quantity"],
            "line_total_cents": row["line_total_cents"],
        }
        for row in rows
    ]


def order_json(conn, order, *, include_customer: bool = True) -> dict:
    cafe = None
    if order["cafe_id"]:
        cafe_row = conn.execute(
            "SELECT * FROM cafes WHERE id = %s", (order["cafe_id"],)
        ).fetchone()
        if cafe_row:
            cafe = cafe_json(cafe_row)

    promo_label = None
    if order["promo_id"]:
        promo_row = conn.execute(
            "SELECT discount_type, percent_value, amount_cents FROM promos WHERE id = %s",
            (order["promo_id"],),
        ).fetchone()
        if promo_row:
            if promo_row["discount_type"] == "percent":
                promo_label = f"−{promo_row['percent_value']}%"
            else:
                promo_label = f"−{promo_row['amount_cents'] / 100:.0f} ₽"

    data = {
        "id": order["id"],
        "number": order["order_number"],
        "status": order["status"],
        "status_label": ORDER_STATUS_LABELS.get(order["status"], order["status"]),
        "fulfillment": order["fulfillment"],
        "fulfillment_label": "Самовывоз" if order["fulfillment"] == "pickup" else "Доставка",
        "cafe": cafe,
        "delivery_address": order["delivery_address"],
        "subtotal_cents": order["subtotal_cents"],
        "discount_cents": order["discount_cents"],
        "total_cents": order["total_cents"],
        "promo": {
            "code": order["promo_code"],
            "label": promo_label,
            "discount_cents": order["discount_cents"],
        }
        if order["promo_code"]
        else None,
        "payment": {
            "method": "card_sim",
            "last4": order["card_last4"],
            "reference": order["payment_ref"],
            "paid_at": iso(order["paid_at"]),
            "simulated": True,
        },
        "items": order_items(conn, order["id"]),
        "created_at": iso(order["created_at"]),
        "paid_at": iso(order["paid_at"]),
        "completed_at": iso(order["completed_at"]),
    }
    if include_customer:
        data["customer"] = {
            "name": order["customer_name"],
            "email": order["customer_email"],
            "phone": order["customer_phone"],
            "comment": order["customer_comment"],
        }
    return data
