"""Единый формат ошибок API."""
from __future__ import annotations

from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": {"code": self.code, "message": self.message}}
        if self.details is not None:
            body["error"]["details"] = self.details
        return body


def bad_request(message: str, details: Any | None = None) -> ApiError:
    return ApiError(400, "bad_request", message, details)


def unauthorized(message: str = "Нужно войти в KubanoID") -> ApiError:
    return ApiError(401, "unauthorized", message)


def forbidden(message: str = "Недостаточно прав") -> ApiError:
    return ApiError(403, "forbidden", message)


def not_found(message: str = "Не найдено") -> ApiError:
    return ApiError(404, "not_found", message)


def conflict(message: str) -> ApiError:
    return ApiError(409, "conflict", message)


def validation_error(message: str, details: Any | None = None) -> ApiError:
    return ApiError(422, "validation_error", message, details)


def too_many(message: str = "Слишком много попыток. Попробуйте позже.") -> ApiError:
    return ApiError(429, "rate_limited", message)
