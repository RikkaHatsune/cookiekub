"""KubanoID: пароли, непрозрачные сессии и простой rate-limit."""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from flask import current_app, request
from werkzeug.security import check_password_hash, generate_password_hash

from .errors import ApiError, unauthorized

_limiter = defaultdict(deque)
_limiter_lock = threading.Lock()


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def issue_session(conn, user_id: int) -> tuple[str, datetime]:
    ttl_days = int(current_app.config.get("SESSION_TTL_DAYS", 7))
    token = new_token()
    expires_at = now_utc() + timedelta(days=ttl_days)
    conn.execute("DELETE FROM sessions WHERE expires_at <= now()")
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
        (hash_token(token), user_id, expires_at),
    )
    return token, expires_at


def bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return token or None


def resolve_token(conn, token: str):
    return conn.execute(
        """
        SELECT u.id, u.email, u.full_name, u.role, u.is_active,
               u.privacy_consent_at, u.created_at, s.expires_at
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = %s
          AND s.expires_at > now()
          AND u.is_active = TRUE
        """,
        (hash_token(token),),
    ).fetchone()


def require_user(user) -> None:
    if not user:
        raise unauthorized()


def require_admin(user) -> None:
    require_user(user)
    if user["role"] != "admin":
        raise ApiError(403, "admin_required", "Нужны права администратора")


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.remote_addr or "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int, extra: str = "") -> None:
    """Best-effort in-memory лимит. На Vercel serverless у каждого инстанса свой
    счётчик, при cold start он сбрасывается; это дополнительный барьер, не основной."""
    if not current_app.config.get("RATE_LIMIT_ENABLED", True):
        return
    key = f"{scope}:{client_ip()}:{extra}"
    now = time.monotonic()
    with _limiter_lock:
        bucket = _limiter[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            raise ApiError(
                429,
                "rate_limited",
                "Слишком много попыток. Попробуйте позже.",
                {"retry_after": retry_after},
            )
        bucket.append(now)
    # Не даём словарю расти бесконечно.
    if len(_limiter) > 5000:
        with _limiter_lock:
            for stale_key in list(_limiter)[:2000]:
                if not _limiter[stale_key]:
                    _limiter.pop(stale_key, None)
