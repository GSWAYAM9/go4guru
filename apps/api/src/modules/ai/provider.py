"""Model-agnostic LLM Provider abstraction, routing, circuit breaker & honest fallbacks."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from src.core.config import Settings

TaskComplexity = Literal["light", "reasoning"]


@dataclass(frozen=True, slots=True)
class ProviderInvocationRequest:
    """Typed payload forwarded strictly from backend orchestrator (zero student PII)."""

    system_instruction: str
    user_prompt: str
    complexity: TaskComplexity = "light"
    response_json_schema: dict[str, Any] | None = None
    max_tokens: int = 1200
    temperature: float = 0.2


@dataclass(frozen=True, slots=True)
class ProviderInvocationResult:
    """Normalized vendor/fallback output with exact token counts, timing, and fallback status."""

    provider: str
    model_id: str
    raw_text: str
    parsed_json: dict[str, Any] | None
    tokens_in: int
    tokens_out: int
    latency_ms: int
    is_fallback: bool
    error_note: str | None = None


class ProviderCallError(RuntimeError):
    """Normalized exception raised by HTTP vendor adapters before circuit breaking/failover."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.status_code = status_code


class CircuitBreaker:
    """Sliding failure threshold breaker preventing cascading timeouts across turns."""

    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failures: dict[str, int] = {}
        self._opened_until: dict[str, float] = {}

    def state(self, provider: str) -> Literal["closed", "open", "half_open"]:
        opened_at = self._opened_until.get(provider)
        if opened_at is None:
            return "closed"
        if time.monotonic() < opened_at:
            return "open"
        return "half_open"

    def allow_request(self, provider: str) -> bool:
        return self.state(provider) != "open"

    def record_success(self, provider: str) -> None:
        self._failures[provider] = 0
        self._opened_until.pop(provider, None)

    def record_failure(self, provider: str) -> None:
        cnt = self._failures.get(provider, 0) + 1
        self._failures[provider] = cnt
        if cnt >= self.failure_threshold:
            self._opened_until[provider] = time.monotonic() + self.recovery_seconds


def _strip_json_fences(raw: str) -> str:
    txt = raw.strip()
    if txt.startswith("```"):
        lines = txt.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        txt = "\n".join(lines).strip()
    return txt


def _try_parse_json(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(_strip_json_fences(raw))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


class LLMProvider(ABC):
    """Abstract gateway contract isolating orchestration from vendor SDKs."""

    name: str
    fast_model: str
    reasoning_model: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True only when required backend credentials exist."""

    @abstractmethod
    async def generate(self, req: ProviderInvocationRequest) -> ProviderInvocationResult:
        """Execute inference and return normalized tokens, latency, and text/JSON."""


class GeminiProvider(LLMProvider):
    """Google Gemini Generative Language API adapter (REST via httpx)."""

    name = "gemini"

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._api_key = settings.gemini_api_key.get_secret_value().strip()
        self.fast_model = settings.ai_gemini_fast_model
        self.reasoning_model = settings.ai_gemini_reasoning_model
        self._timeout = settings.ai_request_timeout_seconds
        self._client = http_client

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(self, req: ProviderInvocationRequest) -> ProviderInvocationResult:
        if not self._api_key:
            raise ProviderCallError(self.name, "GEMINI_API_KEY not configured.")
        model = self.reasoning_model if req.complexity == "reasoning" else self.fast_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self._api_key}"
        )
        gen_cfg: dict[str, Any] = {
            "temperature": req.temperature,
            "maxOutputTokens": req.max_tokens,
        }
        if req.response_json_schema is not None:
            gen_cfg["responseMimeType"] = "application/json"
        body = {
            "systemInstruction": {"parts": [{"text": req.system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": req.user_prompt}]}],
            "generationConfig": gen_cfg,
        }
        t0 = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(url, json=body)
            if resp.status_code >= 400:
                raise ProviderCallError(
                    self.name,
                    f"HTTP {resp.status_code}: {resp.text[:240]}",
                    status_code=resp.status_code,
                )
            data = resp.json()
            candidates = data.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            text_out = "".join(str(p.get("text", "")) for p in parts)
            usage = data.get("usageMetadata", {})
            tin = int(usage.get("promptTokenCount") or max(1, len(req.user_prompt.split())))
            tout = int(usage.get("candidatesTokenCount") or max(1, len(text_out.split())))
            latency = int((time.perf_counter() - t0) * 1000)
            return ProviderInvocationResult(
                provider=self.name,
                model_id=model,
                raw_text=text_out,
                parsed_json=_try_parse_json(text_out),
                tokens_in=tin,
                tokens_out=tout,
                latency_ms=latency,
                is_fallback=False,
            )
        except ProviderCallError:
            raise
        except Exception as exc:
            raise ProviderCallError(self.name, f"Request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()


class OpenAIProvider(LLMProvider):
    """OpenAI Chat Completions adapter (REST via httpx)."""

    name = "openai"

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._api_key = settings.openai_api_key.get_secret_value().strip()
        self.fast_model = settings.ai_openai_fast_model
        self.reasoning_model = settings.ai_openai_reasoning_model
        self._timeout = settings.ai_request_timeout_seconds
        self._client = http_client

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(self, req: ProviderInvocationRequest) -> ProviderInvocationResult:
        if not self._api_key:
            raise ProviderCallError(self.name, "OPENAI_API_KEY not configured.")
        model = self.reasoning_model if req.complexity == "reasoning" else self.fast_model
        payload: dict[str, Any] = {
            "model": model,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "messages": [
                {"role": "system", "content": req.system_instruction},
                {"role": "user", "content": req.user_prompt},
            ],
        }
        if req.response_json_schema is not None:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        t0 = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            if resp.status_code >= 400:
                raise ProviderCallError(
                    self.name,
                    f"HTTP {resp.status_code}: {resp.text[:240]}",
                    status_code=resp.status_code,
                )
            data = resp.json()
            choices = data.get("choices") or []
            text_out = str(choices[0]["message"]["content"]) if choices else ""
            usage = data.get("usage", {})
            tin = int(usage.get("prompt_tokens") or max(1, len(req.user_prompt.split())))
            tout = int(usage.get("completion_tokens") or max(1, len(text_out.split())))
            latency = int((time.perf_counter() - t0) * 1000)
            return ProviderInvocationResult(
                provider=self.name,
                model_id=model,
                raw_text=text_out,
                parsed_json=_try_parse_json(text_out),
                tokens_in=tin,
                tokens_out=tout,
                latency_ms=latency,
                is_fallback=False,
            )
        except ProviderCallError:
            raise
        except Exception as exc:
            raise ProviderCallError(self.name, f"Request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API adapter (REST via httpx)."""

    name = "anthropic"

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._api_key = settings.anthropic_api_key.get_secret_value().strip()
        self.fast_model = settings.ai_anthropic_fast_model
        self.reasoning_model = settings.ai_anthropic_reasoning_model
        self._timeout = settings.ai_request_timeout_seconds
        self._client = http_client

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(self, req: ProviderInvocationRequest) -> ProviderInvocationResult:
        if not self._api_key:
            raise ProviderCallError(self.name, "ANTHROPIC_API_KEY not configured.")
        model = self.reasoning_model if req.complexity == "reasoning" else self.fast_model
        payload = {
            "model": model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "system": req.system_instruction,
            "messages": [{"role": "user", "content": req.user_prompt}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        }
        t0 = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
            )
            if resp.status_code >= 400:
                raise ProviderCallError(
                    self.name,
                    f"HTTP {resp.status_code}: {resp.text[:240]}",
                    status_code=resp.status_code,
                )
            data = resp.json()
            content = data.get("content") or []
            text_out = "".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
            usage = data.get("usage", {})
            tin = int(usage.get("input_tokens") or max(1, len(req.user_prompt.split())))
            tout = int(usage.get("output_tokens") or max(1, len(text_out.split())))
            latency = int((time.perf_counter() - t0) * 1000)
            return ProviderInvocationResult(
                provider=self.name,
                model_id=model,
                raw_text=text_out,
                parsed_json=_try_parse_json(text_out),
                tokens_in=tin,
                tokens_out=tout,
                latency_ms=latency,
                is_fallback=False,
            )
        except ProviderCallError:
            raise
        except Exception as exc:
            raise ProviderCallError(self.name, f"Request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()


class AIRouterGateway:
    """Routes AI calls across configured providers with circuit breaking & honest fallback."""

    def __init__(
        self,
        settings: Settings,
        *,
        providers: dict[str, LLMProvider] | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.settings = settings
        self.breaker = breaker or CircuitBreaker()
        self.providers: dict[str, LLMProvider] = providers or {
            "gemini": GeminiProvider(settings),
            "openai": OpenAIProvider(settings),
            "anthropic": AnthropicProvider(settings),
        }

    def routing_order(self, preferred: str = "auto") -> list[str]:
        all_names = ["gemini", "openai", "anthropic"]
        first = (
            preferred
            if preferred in all_names
            else (
                self.settings.ai_primary_provider
                if self.settings.ai_primary_provider in all_names
                else "gemini"
            )
        )
        return [first] + [p for p in all_names if p != first]

    async def invoke_or_fallback(
        self,
        req: ProviderInvocationRequest,
        *,
        preferred_provider: str = "auto",
    ) -> tuple[ProviderInvocationResult | None, list[str]]:
        """Attempt configured/healthy providers in order; return (None, errors) if none succeed."""
        errors: list[str] = []
        for pname in self.routing_order(preferred_provider):
            prov = self.providers.get(pname)
            if prov is None or not prov.is_configured():
                continue
            if not self.breaker.allow_request(pname):
                errors.append(f"{pname}: circuit_open")
                continue
            try:
                res = await prov.generate(req)
                self.breaker.record_success(pname)
                return res, errors
            except Exception as exc:
                self.breaker.record_failure(pname)
                errors.append(f"{pname}: {exc}")
        return None, errors
