"""Анонимизация аккаунта и связанных PII (право на удаление)."""
from __future__ import annotations

import secrets

from .errors import conflict
from .security import hash_password


def anonymize_user(conn, user_id: int) -> None:
    user = conn.execute(
        "SELECT id, anonymized_at FROM users WHERE id = %s FOR UPDATE", (user_id,)
    ).fetchone()
    if not user:
        raise conflict("Пользователь не найден")
    if user["anonymized_at"]:
        raise conflict("Аккаунт уже удалён")

    anon_email = f"deleted+{user_id}@kubanoid.invalid"
    conn.execute(
        """
        UPDATE users
        SET email = %s, full_name = 'Удалённый пользователь',
            password_hash = %s, is_active = FALSE, anonymized_at = now()
        WHERE id = %s
        """,
        (anon_email, hash_password(secrets.token_urlsafe(24)), user_id),
    )
    conn.execute(
        """
        UPDATE orders
        SET customer_name = 'Удалённый пользователь',
            customer_email = %s,
            customer_phone = '',
            customer_comment = '',
            delivery_address = CASE WHEN fulfillment = 'delivery' THEN 'Адрес удалён' ELSE NULL END
        WHERE user_id = %s
        """,
        (anon_email, user_id),
    )
    conn.execute(
        """
        UPDATE tickets
        SET email = %s, message = '[удалено]', admin_reply = NULL
        WHERE user_id = %s
        """,
        (anon_email, user_id),
    )
    conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
