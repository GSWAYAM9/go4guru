"""HTTP middleware for correlation IDs, security headers, and structured request logs."""

from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.core.hardening import build_api_security_headers
from src.core.logging import request_id_ctx_var

logger = logging.getLogger("go4guru.http")
_REQUEST_ID_SAFE_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextAndSecurityMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID, log structured request metrics, and inject security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming_id if _REQUEST_ID_SAFE_RE.match(incoming_id) else str(uuid4())

        request.state.request_id = request_id
        token = request_id_ctx_var.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            request_id_ctx_var.reset(token)

        settings = getattr(request.app.state, "settings", None)
        app_env = getattr(settings, "app_env", "development")

        response.headers["X-Request-ID"] = request_id
        for header_name, header_val in build_api_security_headers(app_env).items():
            response.headers[header_name] = header_val

        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )
        return response
