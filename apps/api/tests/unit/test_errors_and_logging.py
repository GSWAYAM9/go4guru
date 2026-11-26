"""Unit tests for structured JSON logging, redaction, and AppError."""

from __future__ import annotations

import json
import logging

from src.core.errors import AppError, build_error_response
from src.core.logging import JsonLogFormatter, redact_sensitive_text, request_id_ctx_var


def test_redact_sensitive_text_masks_tokens_and_passwords() -> None:
    sample = "Authorization: Bearer abc.def.ghi password=supersecret api_key=sk-12345"
    redacted = redact_sensitive_text(sample)
    assert "abc.def.ghi" not in redacted
    assert "supersecret" not in redacted
    assert "sk-12345" not in redacted
    assert "[REDACTED]" in redacted


def test_json_log_formatter_includes_request_id_and_redacts() -> None:
    formatter = JsonLogFormatter()
    token = request_id_ctx_var.set("req-trace-999")
    try:
        record = logging.LogRecord(
            name="go4guru.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=30,
            msg="Attempting login with token=secret123",
            args=(),
            exc_info=None,
        )
        rendered = formatter.format(record)
    finally:
        request_id_ctx_var.reset(token)

    parsed = json.loads(rendered)
    assert parsed["level"] == "INFO"
    assert parsed["request_id"] == "req-trace-999"
    assert "secret123" not in parsed["message"]
    assert "[REDACTED]" in parsed["message"]


def test_error_envelope_builder_matches_contract() -> None:
    err = AppError(status_code=403, code="FORBIDDEN", message="Denied", details={"role": "student"})
    resp = build_error_response(
        status_code=err.status_code,
        code=err.code,
        message=err.message,
        details=err.details,
        request_id="req-abc",
    )
    assert resp.status_code == 403
    body = json.loads(resp.body)
    assert body == {
        "error": {
            "code": "FORBIDDEN",
            "message": "Denied",
            "details": {"role": "student"},
            "request_id": "req-abc",
        }
    }
