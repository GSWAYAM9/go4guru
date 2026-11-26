"""Structured JSON logging with correlation ID propagation and secret redaction."""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(authorization|password|passwd|secret|token|api[_-]?key|set-cookie|cookie)"
    r"(\s*[:=]\s*)(?!Bearer\s+\[REDACTED\])([^\s,;\"'}]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;\"'}]+")
_REDACTED = "[REDACTED]"


def redact_sensitive_text(value: str) -> str:
    """Mask credential-like key=value pairs or bearer tokens in log strings."""
    masked = _BEARER_PATTERN.sub(f"Bearer {_REDACTED}", value)
    return _SENSITIVE_PATTERN.sub(rf"\1\2{_REDACTED}", masked)


class RequestContextFilter(logging.Filter):
    """Attach the active correlation request_id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


class JsonLogFormatter(logging.Formatter):
    """Render log records as single-line JSON with secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", request_id_ctx_var.get()),
            "message": redact_sensitive_text(record.getMessage()),
        }
        for field in ("method", "path", "status_code", "duration_ms", "event"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = redact_sensitive_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


def configure_logging(*, level: str = "INFO", log_format: str = "json") -> None:
    """Configure root and framework loggers deterministically."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())
    if log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
        )
    root_logger.addHandler(handler)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
