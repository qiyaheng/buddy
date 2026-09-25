"""统一业务错误与错误码。"""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class BadRequestError(ApiError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__("bad_request", message, 400, details)


class NotFoundError(ApiError):
    def __init__(self, message: str = "资源不存在", details: Any = None) -> None:
        super().__init__("not_found", message, 404, details)


class ConflictError(ApiError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__("conflict", message, 409, details)
