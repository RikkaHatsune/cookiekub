"""Retention: ежедневная очистка/анонимизация по токену из GitHub Actions."""
from __future__ import annotations

import hmac

from flask import Blueprint, current_app, request

from .errors import forbidden
from .extensions import get_db

bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")


@bp.post("/purge")
def purge():
    supplied = request.headers.get("X-Maintenance-Token", "")
    expected = current_app.config.get("MAINTENANCE_TOKEN", "")
    if not expected or not hmac.compare_digest(supplied, expected):
        raise forbidden("Неверный maintenance-токен")

    conn = get_db()
    sessions = conn.execute("DELETE FROM sessions WHERE expires_at <= now()").rowcount
    guest_orders = conn.execute(
        """
        DELETE FROM orders
        WHERE user_id IS NULL AND created_at < now() - interval '12 months'
        """
    ).rowcount
    orders_anonymized = conn.execute(
        """
        UPDATE orders
        SET customer_name = 'Удалённый пользователь',
            customer_email = 'deleted+' || id || '@kubanoid.invalid',
            customer_phone = '',
            customer_comment = '',
            delivery_address = CASE WHEN fulfillment = 'delivery' THEN 'Адрес удалён' ELSE NULL END
        WHERE user_id IS NOT NULL
          AND created_at < now() - interval '12 months'
          AND customer_email NOT LIKE 'deleted+%'
        """
    ).rowcount
    tickets = conn.execute(
        "DELETE FROM tickets WHERE created_at < now() - interval '12 months'"
    ).rowcount
    audit = conn.execute(
        "DELETE FROM admin_audit WHERE created_at < now() - interval '12 months'"
    ).rowcount
    conn.commit()
    return {
        "ok": True,
        "deleted": {
            "sessions": sessions,
            "guest_orders": guest_orders,
            "tickets": tickets,
            "audit": audit,
        },
        "anonymized_orders": orders_anonymized,
    }
