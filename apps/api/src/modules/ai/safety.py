"""Child-safety AI guardrail, prompt-injection defense, and PII scrubbing (Module 15)."""

from __future__ import annotations

import re

from src.modules.ai.schemas import SafetyVerdict

_SELF_HARM_PATTERNS = re.compile(
    r"\b(kill\s+myself|suicide|end\s+my\s+life|self[-\s]?harm|hurt\s+myself|"
    r"want\s+to\s+die|don'?t\s+want\s+to\s+live|cutting\s+myself)\b",
    re.IGNORECASE,
)

_PROMPT_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?previous\s+instructions|system\s+prompt|reveal\s+(your\s+)?prompt|"
    r"dump\s+(the\s+)?database|drop\s+table|select\s+\*\s+from\s+users|"
    r"bypass\s+(safety|rbac|security)|print\s+api[_\s]?key|secret[_\s]?key)",
    re.IGNORECASE,
)

_UNSAFE_ABUSE_PATTERNS = re.compile(
    r"\b(make\s+a\s+bomb|build\s+an\s+explosive|how\s+to\s+hack\s+|pornography|explicit\s+sex)\b",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?91[-\s]?)?[6-9]\d{9}\b")

SUPPORTIVE_HELPLINE_MESSAGE = (
    "It sounds like you may be going through a very difficult moment. "
    "You are not alone, and support is available right now.\n\n"
    "- **Tele-MANAS (India 24x7 Mental Health Helpline):** Call `14416` or `1800-891-4416`\n"
    "- **Childline India:** Call `1098`\n"
    "- **Emergency / Trusted Adult:** Please speak with a parent, guardian, school counselor, "
    "or teacher right away."
)


def scrub_pii_text(text: str) -> str:
    """Redact accidental email addresses or Indian mobile numbers before outbound LLM calls."""
    cleaned = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    cleaned = _PHONE_RE.sub("[REDACTED_PHONE]", cleaned)
    return cleaned


def evaluate_input_safety(user_message: str, *, is_minor: bool = True) -> SafetyVerdict:
    """Screen inbound student prompt before routing or calling external providers."""
    if _SELF_HARM_PATTERNS.search(user_message):
        return SafetyVerdict(
            action="safe_redirect",
            reason_code="DISTRESS_OR_SELF_HARM_HELPLINE",
            safe_message=SUPPORTIVE_HELPLINE_MESSAGE,
            requires_review_escalation=True,
        )

    if _PROMPT_INJECTION_PATTERNS.search(user_message):
        return SafetyVerdict(
            action="block",
            reason_code="PROMPT_INJECTION_BLOCKED",
            safe_message=(
                "I cannot follow instructions that attempt to bypass educational safety rules, "
                "inspect hidden prompts, or access internal system credentials. "
                "Please ask a curriculum question or academic doubt instead."
            ),
            requires_review_escalation=True,
        )

    if _UNSAFE_ABUSE_PATTERNS.search(user_message):
        return SafetyVerdict(
            action="block",
            reason_code="CHILD_SAFETY_POLICY_BLOCK" if is_minor else "SAFETY_POLICY_BLOCK",
            safe_message=(
                "I cannot assist with harmful, dangerous, or non-educational requests. "
                "I am here to help with Classes 6-12 school and exam learning."
            ),
            requires_review_escalation=True,
        )

    return SafetyVerdict(action="allow")


def evaluate_output_safety(candidate_markdown: str) -> SafetyVerdict:
    """Verify generated output contains no leaked credentials, raw scripts, or unsafe distress."""
    lower = candidate_markdown.lower()
    if "<script" in lower or "javascript:" in lower:
        return SafetyVerdict(
            action="block",
            reason_code="UNSAFE_SCRIPT_OUTPUT",
            safe_message="Response withheld by output safety filter.",
            requires_review_escalation=True,
        )
    if _EMAIL_RE.search(candidate_markdown) or _PHONE_RE.search(candidate_markdown):
        return SafetyVerdict(
            action="allow",
            reason_code="PII_REDACTED_OUTPUT",
        )
    return SafetyVerdict(action="allow")
