"""Валидация пользовательского ввода и утилиты."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from flask import request

from .errors import bad_request, validation_error

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
PHONE_RE = re.compile(r"^[0-9+()\-\s]{5,30}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

LABELS = {
    "email": "Email",
    "password": "Пароль",
    "full_name": "Имя",
    "name": "Название",
    "subject": "Тема",
    "message": "Сообщение",
    "comment": "Комментарий",
    "address": "Адрес",
    "delivery_address": "Адрес доставки",
    "customer_address": "Адрес доставки",
    "phone": "Телефон",
    "code": "Промокод",
    "category": "Категория",
    "slug": "Адрес страницы (slug)",
    "image_url": "Ссылка на изображение",
}


def body() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise bad_request("Ожидается JSON-объект")
    return data


def text(
    data: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    min_len: int = 0,
    max_len: int = 500,
    default: str = "",
    label: str | None = None,
) -> str:
    value = data.get(key, default)
    if value is None:
        value = default
    if not isinstance(value, str):
        raise validation_error(f"Поле «{label or LABELS.get(key, key)}» должно быть строкой")
    value = value.strip()
    if required and not value:
        raise validation_error(f"Заполните поле «{label or LABELS.get(key, key)}»")
    if value and len(value) < min_len:
        raise validation_error(
            f"Поле «{label or LABELS.get(key, key)}» короче {min_len} символов"
        )
    if len(value) > max_len:
        raise validation_error(
            f"Поле «{label or LABELS.get(key, key)}» длиннее {max_len} символов"
        )
    return value


def email(data: dict[str, Any], key: str = "email", *, required: bool = True) -> str:
    value = text(data, key, required=required, max_len=254).lower()
    if value and not EMAIL_RE.match(value):
        raise validation_error("Введите корректный email")
    return value


def password(data: dict[str, Any], key: str = "password") -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise validation_error("Введите пароль")
    if not 8 <= len(value) <= 128:
        raise validation_error("Пароль должен быть от 8 до 128 символов")
    return value


def integer(
    data: dict[str, Any],
    key: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
    required: bool = True,
) -> int | None:
    if key not in data or data.get(key) is None:
        if required:
            raise validation_error(f"Укажите «{LABELS.get(key, key)}»")
        return default
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise validation_error(f"Поле «{LABELS.get(key, key)}» должно быть целым числом")
    if minimum is not None and value < minimum:
        raise validation_error(f"Минимальное значение — {minimum}")
    if maximum is not None and value > maximum:
        raise validation_error(f"Максимальное значение — {maximum}")
    return value


def boolean(data: dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def one_of(value: str, allowed: set[str], message: str) -> str:
    if value not in allowed:
        raise validation_error(message)
    return value


def iso_datetime(
    data: dict[str, Any], key: str, *, required: bool = False
) -> datetime | None:
    value = data.get(key)
    if value in (None, ""):
        if required:
            raise validation_error(f"Укажите «{LABELS.get(key, key)}»")
        return None
    if not isinstance(value, str):
        raise validation_error(f"Поле «{key}» должно быть датой ISO 8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise validation_error(f"Поле «{key}» должно быть датой ISO 8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def phone(data: dict[str, Any], key: str = "customer_phone", *, required: bool = True) -> str:
    value = text(data, key, required=required, min_len=5, max_len=30)
    if value and not PHONE_RE.match(value):
        raise validation_error("Телефон может содержать цифры, пробелы, +, (, ), -")
    return value


def slugify(value: str) -> str:
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    normalized = unicodedata.normalize("NFKC", value).lower()
    out = "".join(translit.get(ch, ch) for ch in normalized)
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")
    return out[:80] or "product"


def clean_slug(value: str) -> str:
    value = value.strip().lower()
    if not SLUG_RE.match(value) or len(value) > 80:
        raise validation_error("Slug: только латиница, цифры и дефис, до 80 символов")
    return value
