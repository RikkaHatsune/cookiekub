"""Тикеты поддержки: форма бага + имитация письма."""
from __future__ import annotations

from flask import Blueprint, current_app, g

from .errors import validation_error
from .extensions import get_db
from .security import rate_limit, require_user
from .serializers import iso
from .validators import body, email, one_of, text

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


def ticket_json(row) -> dict:
    return {
        "id": row["id"],
        "subject": row["subject"],
        "category": row["category"],
        "message": row["message"],
        "status": row["status"],
        "admin_reply": row["admin_reply"],
        "replied_at": iso(row["replied_at"]),
        "created_at": iso(row["created_at"]),
    }


@bp.post("")
def create_ticket():
    rate_limit("ticket", 5, 3600)
    data = body()
    user = g.get("user")
    if user:
        email_value = user["email"]
    else:
        email_value = email(data)
    subject = text(data, "subject", required=True, min_len=3, max_len=120)
    category = one_of(
        text(data, "category", default="other", max_len=20),
        {"bug", "question", "other"},
        "Категория: bug, question или other",
    )
    message = text(data, "message", required=True, min_len=5, max_len=4000)

    conn = get_db()
    row = conn.execute(
        """
        INSERT INTO tickets (user_id, email, subject, category, message)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """,
        (user["id"] if user else None, email_value, subject, category, message),
    ).fetchone()
    conn.commit()
    return {
        "ticket": ticket_json(row),
        "simulated_email": {
            "to": current_app.config["SUPPORT_EMAIL"],
            "subject": f"[CookieKub] {subject}",
            "note": "Письмо не отправляется: это симулятор. Тикет уже в базе.",
        },
    }, 201


@bp.get("/my")
def my_tickets():
    user = g.get("user")
    require_user(user)
    rows = get_db().execute(
        "SELECT * FROM tickets WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
        (user["id"],),
    ).fetchall()
    return {"tickets": [ticket_json(row) for row in rows]}


@bp.get("/<int:ticket_id>")
def get_ticket(ticket_id: int):
    user = g.get("user")
    require_user(user)
    row = get_db().execute(
        "SELECT * FROM tickets WHERE id = %s AND user_id = %s", (ticket_id, user["id"])
    ).fetchone()
    if not row:
        raise validation_error("Тикет не найден")
    return {"ticket": ticket_json(row)}
