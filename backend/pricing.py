"""Расчёт скидки. Все суммы — копейки, округление половины вверх."""
from __future__ import annotations

from datetime import datetime, timezone

from .errors import validation_error


def promo_discount(promo, subtotal_cents: int, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    if not promo["is_active"]:
        raise validation_error("Промокод неактивен")
    if promo["starts_at"] and promo["starts_at"] > now:
        raise validation_error("Промокод ещё не начал действовать")
    if promo["ends_at"] and promo["ends_at"] <= now:
        raise validation_error("Срок действия промокода истёк")
    if promo["max_uses"] is not None and promo["used_count"] >= promo["max_uses"]:
        raise validation_error("Лимит использований промокода исчерпан")
    if subtotal_cents < promo["min_order_cents"]:
        need = (promo["min_order_cents"] - subtotal_cents) / 100
        raise validation_error(
            f"Промокод действует от {promo['min_order_cents'] / 100:.0f} ₽ "
            f"(не хватает {need:.0f} ₽)"
        )
    if promo["discount_type"] == "percent":
        discount = (subtotal_cents * int(promo["percent_value"]) + 50) // 100
    else:
        discount = int(promo["amount_cents"])
    return max(0, min(discount, subtotal_cents))


def promo_label(promo) -> str:
    if promo["discount_type"] == "percent":
        return f"−{promo['percent_value']}%"
    return f"−{promo['amount_cents'] / 100:.0f} ₽"


def promo_json(promo, discount_cents: int, total_cents: int) -> dict:
    return {
        "id": promo["id"],
        "code": promo["code"],
        "discount_type": promo["discount_type"],
        "percent_value": promo["percent_value"],
        "amount_cents": promo["amount_cents"],
        "min_order_cents": promo["min_order_cents"],
        "label": promo_label(promo),
        "discount_cents": discount_cents,
        "total_cents": total_cents,
    }
