"""KubanoID: регистрация, вход, сессии и управление аккаунтом."""
from __future__ import annotations

import psycopg
from flask import Blueprint, g

from .accounts import anonymize_user
from .errors import conflict, unauthorized, validation_error
from .extensions import get_db
from .security import (
    bearer_token,
    hash_token,
    issue_session,
    rate_limit,
    require_user,
    resolve_token,
    verify_password,
    hash_password,
)
from .serializers import iso, user_json
from .validators import body, boolean, email, password, text

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    rate_limit("register", 10, 3600)
    data = body()
    email_value = email(data)
    password_value = password(data)
    full_name = text(data, "full_name", required=True, min_len=2, max_len=120)
    if not boolean(data, "privacy_consent"):
        raise validation_error("Нужно согласие на обработку персональных данных")

    conn = get_db()
    if conn.execute(
        "SELECT 1 FROM users WHERE lower(email) = %s", (email_value,)
    ).fetchone():
        raise conflict("Аккаунт с таким email уже существует")

    try:
        row = conn.execute(
            """
            INSERT INTO users (email, password_hash, full_name, privacy_consent_at)
            VALUES (%s, %s, %s, now())
            RETURNING id, email, full_name, role, is_active, privacy_consent_at, created_at
            """,
            (email_value, hash_password(password_value), full_name),
        ).fetchone()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise conflict("Аккаунт с таким email уже существует") from None

    token, expires_at = issue_session(conn, row["id"])
    conn.commit()
    return {"token": token, "expires_at": iso(expires_at), "user": user_json(row)}, 201


@bp.post("/login")
def login():
    data = body()
    email_value = email(data)
    password_value = password(data)
    rate_limit("login", 5, 900, extra=email_value)

    conn = get_db()
    row = conn.execute(
        """
        SELECT id, email, password_hash, full_name, role, is_active,
               privacy_consent_at, created_at
        FROM users WHERE lower(email) = %s
        """,
        (email_value,),
    ).fetchone()
    if not row or not row["is_active"] or not verify_password(
        row["password_hash"], password_value
    ):
        raise unauthorized("Неверный email или пароль")

    token, expires_at = issue_session(conn, row["id"])
    conn.commit()
    return {"token": token, "expires_at": iso(expires_at), "user": user_json(row)}


@bp.post("/logout")
def logout():
    token = bearer_token()
    if not token:
        raise unauthorized()
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token_hash = %s", (hash_token(token),))
    conn.commit()
    return {"ok": True}


@bp.get("/me")
def me():
    require_user(g.get("user"))
    return {"user": user_json(g.user)}


@bp.post("/change-password")
def change_password():
    require_user(g.get("user"))
    data = body()
    current = data.get("current_password")
    if not isinstance(current, str):
        raise validation_error("Введите текущий пароль")
    new_password = data.get("new_password")
    if not isinstance(new_password, str) or not 8 <= len(new_password) <= 128:
        raise validation_error("Новый пароль должен быть от 8 до 128 символов")
    if current == new_password:
        raise validation_error("Новый пароль должен отличаться от текущего")

    conn = get_db()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id = %s", (g.user["id"],)
    ).fetchone()
    if not verify_password(row["password_hash"], current):
        raise validation_error("Текущий пароль неверен")
    conn.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hash_password(new_password), g.user["id"]),
    )
    conn.execute("DELETE FROM sessions WHERE user_id = %s", (g.user["id"],))
    conn.commit()
    return {"ok": True, "relogin": True}


@bp.delete("/account")
def delete_account():
    require_user(g.get("user"))
    data = body()
    supplied = data.get("password")
    if not isinstance(supplied, str):
        raise validation_error("Подтвердите удаление паролем")
    conn = get_db()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id = %s", (g.user["id"],)
    ).fetchone()
    if not verify_password(row["password_hash"], supplied):
        raise validation_error("Пароль неверен")

    anonymize_user(conn, g.user["id"])
    conn.commit()
    return {"ok": True, "deleted": True}


@bp.get("/session")
def session_info():
    """Диагностика: есть ли валидная сессия; не отдаёт PII."""
    token = bearer_token()
    if not token:
        return {"authenticated": False}
    user = resolve_token(get_db(), token)
    return {"authenticated": bool(user)}
