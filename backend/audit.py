"""Журнал действий администраторов (без PII в details)."""
from __future__ import annotations

import json


def record_audit(
    conn,
    actor_user_id: int,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO admin_audit (actor_user_id, action, entity_type, entity_id, details)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        """,
        (actor_user_id, action, entity_type, str(entity_id), json.dumps(details or {})),
    )
