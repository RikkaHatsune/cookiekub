"""Самописная админ-панель: товары, пользователи, заказы, промокоды, тикеты."""
from __future__ import annotations

import psycopg
from flask import Blueprint, g, request

from .accounts import anonymize_user
from .audit import record_audit
from .errors import conflict, not_found, validation_error
from .extensions import get_db
from .security import require_admin, require_user
from .serializers import (
    PRODUCT_CATEGORIES,
    cafe_json,
    iso,
    order_json,
    product_json,
    user_json,
)
from .tickets import ticket_json
from .validators import (
    body,
    boolean,
    clean_slug,
    integer,
    iso_datetime,
    one_of,
    slugify,
    text,
)

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _admin():
    user = g.get("user")
    require_admin(user)
    return user


def _product_values(data: dict, existing=None) -> dict:
    values = {}
    if existing is not None:
        values = {
            "name": existing["name"],
            "slug": existing["slug"],
            "short_description": existing["short_description"],
            "description": existing["description"],
            "price_cents": existing["price_cents"],
            "image_url": existing["image_url"],
            "category": existing["category"],
            "stock_qty": existing["stock_qty"],
            "is_active": existing["is_active"],
            "sort_order": existing["sort_order"],
        }
    if "name" in data or existing is None:
        values["name"] = text(data, "name", required=True, min_len=2, max_len=120)
    if "slug" in data and data.get("slug"):
        values["slug"] = clean_slug(data["slug"])
    elif existing is None:
        values["slug"] = slugify(values["name"])
    if "short_description" in data or existing is None:
        values["short_description"] = text(
            data, "short_description", max_len=200, default=""
        )
    if "description" in data or existing is None:
        values["description"] = text(data, "description", max_len=3000, default="")
    if "price_cents" in data or existing is None:
        values["price_cents"] = integer(
            data, "price_cents", minimum=1, maximum=1_000_000
        )
    if "image_url" in data or existing is None:
        values["image_url"] = text(data, "image_url", max_len=500, default="")
    if "category" in data or existing is None:
        values["category"] = one_of(
            text(data, "category", default="classic", max_len=30),
            set(PRODUCT_CATEGORIES),
            "Неизвестная категория",
        )
    if "stock_qty" in data or existing is None:
        values["stock_qty"] = integer(
            data, "stock_qty", minimum=0, maximum=100_000, default=0, required=False
        )
    if "is_active" in data or existing is None:
        values["is_active"] = boolean(data, "is_active", default=True)
    if "sort_order" in data or existing is None:
        values["sort_order"] = integer(
            data, "sort_order", minimum=-1000, maximum=1000, default=0, required=False
        )
    return values


@bp.get("/stats")
def stats():
    _admin()
    conn = get_db()
    row = conn.execute(
        """
        SELECT
          (SELECT count(*) FROM users WHERE role = 'user' AND anonymized_at IS NULL) AS users,
          (SELECT count(*) FROM products WHERE is_active = TRUE) AS products,
          (SELECT count(*) FROM orders) AS orders_total,
          (SELECT count(*) FROM orders WHERE status = 'processing') AS orders_processing,
          (SELECT count(*) FROM orders WHERE status = 'completed') AS orders_completed,
          (SELECT count(*) FROM tickets WHERE status = 'open') AS tickets_open,
          (SELECT COALESCE(sum(total_cents), 0) FROM orders WHERE status = 'completed') AS revenue
        """
    ).fetchone()
    recent = conn.execute(
        "SELECT * FROM orders ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    return {
        "stats": {
            "users": row["users"],
            "products": row["products"],
            "orders_total": row["orders_total"],
            "orders_processing": row["orders_processing"],
            "orders_completed": row["orders_completed"],
            "tickets_open": row["tickets_open"],
            "revenue_cents": row["revenue"],
        },
        "recent_orders": [
            order_json(conn, item, include_customer=False) for item in recent
        ],
    }


@bp.get("/products")
def list_products():
    _admin()
    search = (request.args.get("search") or "").strip()
    params = []
    where = ""
    if search:
        where = "WHERE name ILIKE %s OR slug ILIKE %s"
        params = [f"%{search}%", f"%{search}%"]
    rows = get_db().execute(
        f"SELECT * FROM products {where} ORDER BY sort_order, id", params
    ).fetchall()
    return {"products": [product_json(row) for row in rows]}


@bp.post("/products")
def create_product():
    admin = _admin()
    data = body()
    values = _product_values(data)
    conn = get_db()
    try:
        row = conn.execute(
            """
            INSERT INTO products (name, slug, short_description, description, price_cents,
                                  image_url, category, stock_qty, is_active, sort_order)
            VALUES (%(name)s, %(slug)s, %(short_description)s, %(description)s,
                    %(price_cents)s, %(image_url)s, %(category)s, %(stock_qty)s,
                    %(is_active)s, %(sort_order)s)
            RETURNING *
            """,
            values,
        ).fetchone()
        record_audit(conn, admin["id"], "product.create", "product", row["id"])
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise conflict("Товар с таким slug уже существует") from None
    return {"product": product_json(row)}, 201


@bp.patch("/products/<int:product_id>")
def update_product(product_id: int):
    admin = _admin()
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM products WHERE id = %s", (product_id,)
    ).fetchone()
    if not existing:
        raise not_found("Товар не найден")
    values = _product_values(body(), existing=existing)
    try:
        row = conn.execute(
            """
            UPDATE products SET name = %(name)s, slug = %(slug)s,
                short_description = %(short_description)s,
                description = %(description)s,
                price_cents = %(price_cents)s, image_url = %(image_url)s,
                category = %(category)s, stock_qty = %(stock_qty)s,
                is_active = %(is_active)s, sort_order = %(sort_order)s
            WHERE id = %(id)s
            RETURNING *
            """,
            {**values, "id": product_id},
        ).fetchone()
        record_audit(conn, admin["id"], "product.update", "product", product_id)
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise conflict("Товар с таким slug уже существует") from None
    return {"product": product_json(row)}


@bp.delete("/products/<int:product_id>")
def archive_product(product_id: int):
    admin = _admin()
    conn = get_db()
    row = conn.execute(
        "UPDATE products SET is_active = FALSE WHERE id = %s RETURNING id",
        (product_id,),
    ).fetchone()
    if not row:
        raise not_found("Товар не найден")
    record_audit(conn, admin["id"], "product.archive", "product", product_id)
    conn.commit()
    return {"ok": True, "archived": True}


@bp.get("/users")
def list_users():
    _admin()
    search = (request.args.get("search") or "").strip()
    params = []
    where = ""
    if search:
        where = "WHERE u.email ILIKE %s OR u.full_name ILIKE %s"
        params = [f"%{search}%", f"%{search}%"]
    rows = get_db().execute(
        f"""
        SELECT u.*, count(o.id) AS orders_count,
               max(o.created_at) AS last_order_at
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
        {where}
        GROUP BY u.id
        ORDER BY u.created_at DESC
        LIMIT 200
        """,
        params,
    ).fetchall()
    return {
        "users": [
            {
                **user_json(row),
                "is_active": row["is_active"],
                "anonymized_at": iso(row["anonymized_at"]),
                "orders_count": row["orders_count"],
                "last_order_at": iso(row["last_order_at"]),
            }
            for row in rows
        ]
    }


@bp.patch("/users/<int:user_id>")
def update_user(user_id: int):
    admin = _admin()
    data = body()
    if user_id == admin["id"]:
        raise validation_error("Нельзя менять собственные роль и блокировку")
    conn = get_db()
    target = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    if not target:
        raise not_found("Пользователь не найден")
    role = target["role"]
    is_active = target["is_active"]
    if "role" in data:
        role = one_of(text(data, "role", required=True, max_len=10), {"user", "admin"}, "Роль: user или admin")
    if "is_active" in data:
        is_active = boolean(data, "is_active")
    if target["role"] == "admin" and (role != "admin" or not is_active):
        remaining = conn.execute(
            "SELECT count(*) AS n FROM users WHERE role = 'admin' AND is_active = TRUE AND id <> %s",
            (user_id,),
        ).fetchone()["n"]
        if remaining == 0:
            raise conflict("Нельзя оставить систему без активного администратора")
    conn.execute(
        "UPDATE users SET role = %s, is_active = %s WHERE id = %s",
        (role, is_active, user_id),
    )
    if not is_active:
        conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    record_audit(
        conn,
        admin["id"],
        "user.update",
        "user",
        user_id,
        {"role": role, "is_active": is_active},
    )
    conn.commit()
    return {"ok": True}


@bp.delete("/users/<int:user_id>")
def delete_user(user_id: int):
    admin = _admin()
    if user_id == admin["id"]:
        raise validation_error("Нельзя удалить собственный аккаунт здесь")
    conn = get_db()
    target = conn.execute(
        "SELECT role, is_active FROM users WHERE id = %s", (user_id,)
    ).fetchone()
    if not target:
        raise not_found("Пользователь не найден")
    if target["role"] == "admin" and target["is_active"]:
        remaining = conn.execute(
            "SELECT count(*) AS n FROM users WHERE role = 'admin' AND is_active = TRUE AND id <> %s",
            (user_id,),
        ).fetchone()["n"]
        if remaining == 0:
            raise conflict("Нельзя оставить систему без активного администратора")
    anonymize_user(conn, user_id)
    record_audit(conn, admin["id"], "user.anonymize", "user", user_id)
    conn.commit()
    return {"ok": True, "anonymized": True}


@bp.get("/orders")
def list_orders():
    _admin()
    conn = get_db()
    status = (request.args.get("status") or "").strip()
    search = (request.args.get("search") or "").strip()
    conditions = []
    params = []
    if status:
        conditions.append("status = %s")
        params.append(status)
    if search:
        conditions.append("(order_number ILIKE %s OR customer_email ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM orders {where} ORDER BY created_at DESC LIMIT 200", params
    ).fetchall()
    return {"orders": [order_json(conn, row) for row in rows]}


def _cancel_order(conn, order) -> None:
    items = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id = %s",
        (order["id"],),
    ).fetchall()
    for item in items:
        if item["product_id"]:
            conn.execute(
                "UPDATE products SET stock_qty = stock_qty + %s WHERE id = %s",
                (item["quantity"], item["product_id"]),
            )
    redemption = conn.execute(
        "SELECT promo_id FROM promo_redemptions WHERE order_id = %s", (order["id"],)
    ).fetchone()
    if redemption:
        conn.execute(
            "DELETE FROM promo_redemptions WHERE order_id = %s", (order["id"],)
        )
        conn.execute(
            "UPDATE promos SET used_count = greatest(used_count - 1, 0) WHERE id = %s",
            (redemption["promo_id"],),
        )


@bp.patch("/orders/<int:order_id>/status")
def change_order_status(order_id: int):
    admin = _admin()
    data = body()
    status = one_of(
        text(data, "status", required=True, max_len=20),
        {"processing", "completed", "cancelled"},
        "Статус: processing, completed или cancelled",
    )
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id = %s FOR UPDATE", (order_id,)
    ).fetchone()
    if not order:
        raise not_found("Заказ не найден")
    if order["status"] == "cancelled" and status != "cancelled":
        raise conflict("Отменённый заказ нельзя вернуть в работу")
    if order["status"] == status:
        return {"ok": True, "order": order_json(conn, order)}
    if status == "cancelled":
        _cancel_order(conn, order)
    completed_at_sql = "now()" if status == "completed" else "NULL"
    conn.execute(
        f"UPDATE orders SET status = %s, completed_at = {completed_at_sql} WHERE id = %s",
        (status, order_id),
    )
    record_audit(
        conn,
        admin["id"],
        "order.status",
        "order",
        order["order_number"],
        {"from": order["status"], "to": status},
    )
    conn.commit()
    fresh = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    return {"ok": True, "order": order_json(conn, fresh)}


@bp.get("/promos")
def list_promos():
    _admin()
    rows = get_db().execute("SELECT * FROM promos ORDER BY created_at DESC").fetchall()
    return {
        "promos": [
            {
                "id": row["id"],
                "code": row["code"],
                "discount_type": row["discount_type"],
                "percent_value": row["percent_value"],
                "amount_cents": row["amount_cents"],
                "min_order_cents": row["min_order_cents"],
                "max_uses": row["max_uses"],
                "used_count": row["used_count"],
                "starts_at": iso(row["starts_at"]),
                "ends_at": iso(row["ends_at"]),
                "is_active": row["is_active"],
            }
            for row in rows
        ]
    }


def _promo_values(data: dict, existing=None) -> dict:
    values = {}
    if existing:
        values = {
            "code": existing["code"],
            "discount_type": existing["discount_type"],
            "percent_value": existing["percent_value"],
            "amount_cents": existing["amount_cents"],
            "min_order_cents": existing["min_order_cents"],
            "max_uses": existing["max_uses"],
            "starts_at": existing["starts_at"],
            "ends_at": existing["ends_at"],
            "is_active": existing["is_active"],
        }
    if "code" in data or existing is None:
        values["code"] = text(data, "code", required=True, min_len=2, max_len=40).upper()
    if "discount_type" in data or existing is None:
        values["discount_type"] = one_of(
            text(data, "discount_type", required=True, max_len=10),
            {"percent", "fixed"},
            "Тип скидки: percent или fixed",
        )
    if values.get("discount_type") == "percent":
        values["amount_cents"] = None
        if "percent_value" in data or existing is None:
            values["percent_value"] = integer(
                data, "percent_value", minimum=1, maximum=100, required=True
            )
    else:
        values["percent_value"] = None
        if "amount_cents" in data or existing is None:
            values["amount_cents"] = integer(
                data, "amount_cents", minimum=1, maximum=1_000_000, required=True
            )
    if "min_order_cents" in data or existing is None:
        values["min_order_cents"] = integer(
            data, "min_order_cents", minimum=0, maximum=1_000_000, default=0, required=False
        )
    if "max_uses" in data or existing is None:
        values["max_uses"] = integer(
            data, "max_uses", minimum=1, maximum=1_000_000, required=False
        )
    if "starts_at" in data or existing is None:
        values["starts_at"] = iso_datetime(data, "starts_at")
    if "ends_at" in data or existing is None:
        values["ends_at"] = iso_datetime(data, "ends_at")
    if "is_active" in data or existing is None:
        values["is_active"] = boolean(data, "is_active", default=True)

    if values["discount_type"] == "percent" and not values["percent_value"]:
        raise validation_error("Для процентной скидки укажите percent_value")
    if values["discount_type"] == "fixed" and not values["amount_cents"]:
        raise validation_error("Для фиксированной скидки укажите amount_cents")
    if (
        values.get("starts_at")
        and values.get("ends_at")
        and values["ends_at"] <= values["starts_at"]
    ):
        raise validation_error("Дата окончания должна быть позже начала")
    return values


@bp.post("/promos")
def create_promo():
    admin = _admin()
    values = _promo_values(body())
    conn = get_db()
    try:
        row = conn.execute(
            """
            INSERT INTO promos (code, discount_type, percent_value, amount_cents,
                                min_order_cents, max_uses, starts_at, ends_at, is_active)
            VALUES (%(code)s, %(discount_type)s, %(percent_value)s, %(amount_cents)s,
                    %(min_order_cents)s, %(max_uses)s, %(starts_at)s, %(ends_at)s,
                    %(is_active)s)
            RETURNING *
            """,
            values,
        ).fetchone()
        record_audit(conn, admin["id"], "promo.create", "promo", row["id"])
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise conflict("Промокод с таким кодом уже существует") from None
    return {"promo": {"id": row["id"], "code": row["code"]}}, 201


@bp.patch("/promos/<int:promo_id>")
def update_promo(promo_id: int):
    admin = _admin()
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM promos WHERE id = %s", (promo_id,)
    ).fetchone()
    if not existing:
        raise not_found("Промокод не найден")
    values = _promo_values(body(), existing=existing)
    try:
        conn.execute(
            """
            UPDATE promos SET code = %(code)s, discount_type = %(discount_type)s,
                percent_value = %(percent_value)s, amount_cents = %(amount_cents)s,
                min_order_cents = %(min_order_cents)s, max_uses = %(max_uses)s,
                starts_at = %(starts_at)s, ends_at = %(ends_at)s,
                is_active = %(is_active)s
            WHERE id = %(id)s
            """,
            {**values, "id": promo_id},
        )
        record_audit(conn, admin["id"], "promo.update", "promo", promo_id)
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise conflict("Промокод с таким кодом уже существует") from None
    return {"ok": True}


@bp.delete("/promos/<int:promo_id>")
def archive_promo(promo_id: int):
    admin = _admin()
    conn = get_db()
    row = conn.execute(
        "UPDATE promos SET is_active = FALSE WHERE id = %s RETURNING id", (promo_id,)
    ).fetchone()
    if not row:
        raise not_found("Промокод не найден")
    record_audit(conn, admin["id"], "promo.archive", "promo", promo_id)
    conn.commit()
    return {"ok": True, "archived": True}


@bp.get("/tickets")
def list_tickets():
    _admin()
    status = (request.args.get("status") or "").strip()
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status = %s ORDER BY created_at DESC LIMIT 200",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    return {
        "tickets": [
            {
                **ticket_json(row),
                "email": row["email"],
                "user_id": row["user_id"],
            }
            for row in rows
        ]
    }


@bp.patch("/tickets/<int:ticket_id>")
def update_ticket(ticket_id: int):
    admin = _admin()
    data = body()
    conn = get_db()
    row = conn.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    if not row:
        raise not_found("Тикет не найден")
    status = row["status"]
    reply = row["admin_reply"]
    if "status" in data:
        status = one_of(
            text(data, "status", required=True, max_len=20),
            {"open", "answered", "closed"},
            "Статус: open, answered или closed",
        )
    if "admin_reply" in data:
        reply = text(data, "admin_reply", max_len=2000, default="") or None
        if reply:
            status = "answered"
    replied_at = "now()" if reply and reply != row["admin_reply"] else "replied_at"
    conn.execute(
        f"UPDATE tickets SET status = %s, admin_reply = %s, replied_at = {replied_at} WHERE id = %s",
        (status, reply, ticket_id),
    )
    record_audit(conn, admin["id"], "ticket.update", "ticket", ticket_id, {"status": status})
    conn.commit()
    fresh = conn.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    return {"ticket": ticket_json(fresh)}


@bp.get("/audit")
def audit_log():
    _admin()
    rows = get_db().execute(
        """
        SELECT a.*, u.email AS actor_email
        FROM admin_audit a LEFT JOIN users u ON u.id = a.actor_user_id
        ORDER BY a.created_at DESC LIMIT 200
        """
    ).fetchall()
    return {
        "entries": [
            {
                "id": row["id"],
                "actor_email": row["actor_email"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": row["details"],
                "created_at": iso(row["created_at"]),
            }
            for row in rows
        ]
    }
