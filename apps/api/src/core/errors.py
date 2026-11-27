"""Standardized API error envelope and exception handlers (docs/API_SPECIFICATION.md)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging import request_id_ctx_var

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Canonical error payload inside `{ "error": ... }`."""

    code: str
    message: str
    details: Any = Field(default=None)
    request_id: str


class ErrorEnvelope(BaseModel):
    """Standard top-level API error response body."""

    error: ErrorDetail


class AppError(Exception):
    """Domain-safe typed application error serialized via ErrorEnvelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    request_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create a JSONResponse matching the standard API error envelope."""
    rid = request_id or request_id_ctx_var.get()
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
            request_id=rid,
        )
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump(), headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global handlers so every failure emits the canonical error envelope."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or request_id_ctx_var.get()
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=rid,
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or request_id_ctx_var.get()
        code = f"HTTP_{exc.status_code}"
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        details = None if isinstance(exc.detail, str) else exc.detail
        return build_error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
            request_id=rid,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or request_id_ctx_var.get()
        sanitized_errors = [
            {
                "loc": list(err.get("loc", ())),
                "msg": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
            for err in exc.errors()
        ]
        return build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message="Input validation failed.",
            details=sanitized_errors,
            request_id=rid,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or request_id_ctx_var.get()
        logger.exception("Unhandled server exception", extra={"event": "unhandled_exception"})
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal error occurred.",
            details=None,
            request_id=rid,
        )
