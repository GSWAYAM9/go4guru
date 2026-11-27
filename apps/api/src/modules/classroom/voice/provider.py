"""VoiceProviderInterface, deterministic Math-to-Speech normalizer, ElevenLabs & caching."""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.storage import LocalPrivateStorage
from src.modules.classroom.models import VoiceUsageLog

_POW_RE = re.compile(r"([A-Za-z0-9\)]+)\^([0-9]+|[A-Za-z]+)")
_SUB_RE = re.compile(r"([A-Za-z]+)_([0-9]+)")


def normalize_math_for_speech(text: str) -> str:
    """Convert inline KaTeX formulas into natural speakable math phrases."""
    s = text.replace("$$", "").replace("$", "")
    s = s.replace("\\sin", " sine ").replace("\\cos", " cosine ").replace("\\tan", " tangent ")
    s = s.replace("\\times", " times ").replace("\\cdot", " dot ").replace("\\frac", " fraction ")
    s = s.replace("\\sqrt", " square root of ")
    s = re.sub(r"\s*=\s*", " equals ", s)
    s = re.sub(r"\s*\+\s*", " plus ", s)
    s = re.sub(r"(?<=\w)\s*-\s*(?=\w)", " minus ", s)
    s = _SUB_RE.sub(r"\1 sub \2", s)

    def _pow_sub(m: re.Match[str]) -> str:
        base, exp = m.group(1), m.group(2)
        if exp == "2":
            return f"{base} squared"
        if exp == "3":
            return f"{base} cubed"
        return f"{base} to the power of {exp}"

    s = _POW_RE.sub(_pow_sub, s)
    return re.sub(r"\s+", " ", s).strip()


def chunk_tts_text(text: str, max_chars: int = 400) -> list[str]:
    """Split speakable text along sentence boundaries under max_chars."""
    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for sent in sentences:
        if len(cur) + len(sent) + 1 <= max_chars:
            cur = f"{cur} {sent}".strip()
        else:
            if cur:
                chunks.append(cur)
            cur = sent[:max_chars]
    if cur:
        chunks.append(cur)
    return chunks or [text[:max_chars]]


@dataclass(frozen=True, slots=True)
class VoiceSynthesisResult:
    audio_available: bool
    cache_key: str | None
    audio_bytes: bytes | None
    normalized_text: str
    provider: str
    voice_id: str
    characters_count: int
    estimated_duration_ms: int
    latency_ms: int
    cache_hit: bool
    is_fallback: bool
    fallback_mode: str | None
    limitation_notice: str | None


@dataclass(frozen=True, slots=True)
class STTTranscriptionResult:
    """Honest Speech-to-Text transcription result (never fabricates transcripts)."""

    stt_available: bool
    transcript: str | None
    confidence: float | None
    language_code: str
    provider: str
    latency_ms: int
    audio_seconds: float
    is_fallback: bool
    fallback_mode: str | None
    limitation_notice: str | None


class VoiceProviderInterface(Protocol):
    async def synthesize_speech(
        self,
        *,
        text: str,
        language_code: str,
        voice_id: str,
        speed: float,
    ) -> VoiceSynthesisResult: ...

    async def stream_speech(
        self,
        *,
        text: str,
        language_code: str,
        voice_id: str,
        speed: float,
    ) -> AsyncIterator[bytes]: ...

    async def transcribe_audio(
        self,
        *,
        audio_bytes: bytes | None,
        mime_type: str,
        language_code: str,
        browser_transcript_hint: str | None = None,
    ) -> STTTranscriptionResult: ...


class ElevenLabsVoiceAdapter:
    """ElevenLabs REST TTS & Scribe STT adapter with SHA-256 disk caching & honest fallback."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = settings.elevenlabs_api_key.get_secret_value().strip()
        self.default_voice_id = settings.elevenlabs_default_voice_id
        self.model_id = settings.elevenlabs_model_id
        self._timeout = settings.voice_request_timeout_seconds
        self._storage = LocalPrivateStorage(settings.storage_local_dir)
        self._client = http_client

    def is_configured(self) -> bool:
        return bool(self._api_key)

    @staticmethod
    def build_cache_key(
        normalized_text: str, voice_id: str, speed: float, language_code: str
    ) -> str:
        raw = f"{normalized_text}|{voice_id}|{speed:.2f}|{language_code}".encode()
        digest = hashlib.sha256(raw).hexdigest()
        return f"voice_cache/{digest}.mp3"

    async def synthesize_speech(
        self,
        *,
        text: str,
        language_code: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> VoiceSynthesisResult:
        vid = (voice_id or self.default_voice_id).strip()
        normalized = normalize_math_for_speech(text)
        est_ms = max(2500, int((len(normalized.split()) / max(0.75, speed)) * 420))
        cache_key = self.build_cache_key(normalized, vid, speed, language_code)

        # Check local private SHA-256 cache first (even if key unset, replay cached clips cleanly)
        try:
            cached = self._storage.read_bytes(cache_key)
            if cached:
                return VoiceSynthesisResult(
                    audio_available=True,
                    cache_key=cache_key,
                    audio_bytes=cached,
                    normalized_text=normalized,
                    provider="elevenlabs",
                    voice_id=vid,
                    characters_count=len(normalized),
                    estimated_duration_ms=est_ms,
                    latency_ms=1,
                    cache_hit=True,
                    is_fallback=False,
                    fallback_mode=None,
                    limitation_notice=None,
                )
        except FileNotFoundError:
            pass

        if not self._api_key:
            return VoiceSynthesisResult(
                audio_available=False,
                cache_key=None,
                audio_bytes=None,
                normalized_text=normalized,
                provider="none_configured",
                voice_id=vid,
                characters_count=len(normalized),
                estimated_duration_ms=est_ms,
                latency_ms=0,
                cache_hit=False,
                is_fallback=True,
                fallback_mode="timed_subtitles_only",
                limitation_notice=(
                    "ELEVENLABS_API_KEY is not configured; using synchronized timed subtitles "
                    "and narration transcript without fabricated audio."
                ),
            )

        t0 = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        payload = {
            "text": " ".join(chunk_tts_text(normalized)),
            "model_id": self.model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        headers = {
            "xi-api-key": self._api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400 or not resp.content:
                return VoiceSynthesisResult(
                    audio_available=False,
                    cache_key=None,
                    audio_bytes=None,
                    normalized_text=normalized,
                    provider="elevenlabs_degraded",
                    voice_id=vid,
                    characters_count=len(normalized),
                    estimated_duration_ms=est_ms,
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    cache_hit=False,
                    is_fallback=True,
                    fallback_mode="timed_subtitles_only",
                    limitation_notice=f"ElevenLabs HTTP {resp.status_code}; degraded to subtitles.",
                )
            audio = resp.content
            self._storage.put_immutable_bytes(cache_key, audio)
            return VoiceSynthesisResult(
                audio_available=True,
                cache_key=cache_key,
                audio_bytes=audio,
                normalized_text=normalized,
                provider="elevenlabs",
                voice_id=vid,
                characters_count=len(normalized),
                estimated_duration_ms=est_ms,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                cache_hit=False,
                is_fallback=False,
                fallback_mode=None,
                limitation_notice=None,
            )
        except Exception as exc:
            return VoiceSynthesisResult(
                audio_available=False,
                cache_key=None,
                audio_bytes=None,
                normalized_text=normalized,
                provider="elevenlabs_degraded",
                voice_id=vid,
                characters_count=len(normalized),
                estimated_duration_ms=est_ms,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                cache_hit=False,
                is_fallback=True,
                fallback_mode="timed_subtitles_only",
                limitation_notice=f"ElevenLabs unreachable ({exc}); using timed subtitles.",
            )
        finally:
            if owns_client:
                await client.aclose()

    async def stream_speech(
        self,
        *,
        text: str,
        language_code: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> AsyncIterator[bytes]:
        """Yield audio stream chunks (16KB slices from synthesized/cached audio)."""
        res = await self.synthesize_speech(
            text=text, language_code=language_code, voice_id=voice_id, speed=speed
        )
        if not res.audio_bytes:
            return
        chunk_size = 16 * 1024
        for offset in range(0, len(res.audio_bytes), chunk_size):
            yield res.audio_bytes[offset : offset + chunk_size]

    async def transcribe_audio(
        self,
        *,
        audio_bytes: bytes | None,
        mime_type: str,
        language_code: str,
        browser_transcript_hint: str | None = None,
    ) -> STTTranscriptionResult:
        """Transcribe audio via ElevenLabs Scribe when configured, or return honest fallback."""
        lang = (language_code or "en").strip().lower()
        est_sec = round(max(1.0, len(audio_bytes) / 16000.0), 2) if audio_bytes else 0.0

        if not self._api_key or not audio_bytes:
            if browser_transcript_hint and browser_transcript_hint.strip():
                return STTTranscriptionResult(
                    stt_available=True,
                    transcript=browser_transcript_hint.strip(),
                    confidence=0.72,
                    language_code=lang,
                    provider="browser_web_speech_passthrough",
                    latency_ms=0,
                    audio_seconds=est_sec,
                    is_fallback=True,
                    fallback_mode="browser_speech_recognition",
                    limitation_notice=(
                        "Cloud STT provider key (ELEVENLABS_API_KEY) is not configured or no "
                        "audio bytes were uploaded; accepted client Web Speech transcript with "
                        "lower confidence."
                    ),
                )
            return STTTranscriptionResult(
                stt_available=False,
                transcript=None,
                confidence=None,
                language_code=lang,
                provider="none_configured" if not self._api_key else "no_audio_payload",
                latency_ms=0,
                audio_seconds=est_sec,
                is_fallback=True,
                fallback_mode="text_input_required",
                limitation_notice=(
                    "ELEVENLABS_API_KEY is not configured for cloud Speech-to-Text; "
                    "use browser Web Speech dictation (where supported) or keyboard text input."
                ),
            )

        t0 = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        url = "https://api.elevenlabs.io/v1/speech-to-text"
        headers = {"xi-api-key": self._api_key}
        files = {"file": ("recording.webm", audio_bytes, mime_type or "audio/webm")}
        data = {"model_id": "scribe_v1", "language_code": lang}
        try:
            resp = await client.post(url, headers=headers, files=files, data=data)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if resp.status_code >= 400:
                return STTTranscriptionResult(
                    stt_available=False,
                    transcript=None,
                    confidence=None,
                    language_code=lang,
                    provider="elevenlabs_scribe_degraded",
                    latency_ms=latency_ms,
                    audio_seconds=est_sec,
                    is_fallback=True,
                    fallback_mode="text_input_required",
                    limitation_notice=(
                        f"ElevenLabs STT HTTP {resp.status_code}; fall back to keyboard input."
                    ),
                )
            body = resp.json()
            text_out = str(body.get("text", "")).strip()
            return STTTranscriptionResult(
                stt_available=bool(text_out),
                transcript=text_out or None,
                confidence=float(body.get("language_probability", 0.9)),
                language_code=lang,
                provider="elevenlabs_scribe",
                latency_ms=latency_ms,
                audio_seconds=est_sec,
                is_fallback=not bool(text_out),
                fallback_mode=None if text_out else "text_input_required",
                limitation_notice=None if text_out else "Empty transcript returned from STT.",
            )
        except Exception as exc:
            return STTTranscriptionResult(
                stt_available=False,
                transcript=None,
                confidence=None,
                language_code=lang,
                provider="elevenlabs_scribe_degraded",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                audio_seconds=est_sec,
                is_fallback=True,
                fallback_mode="text_input_required",
                limitation_notice=f"ElevenLabs STT unreachable ({exc}); use keyboard text input.",
            )
        finally:
            if owns_client:
                await client.aclose()

    def read_cached_audio(self, cache_key: str) -> bytes:
        return self._storage.read_bytes(cache_key)


async def log_voice_usage(
    db: AsyncSession,
    *,
    user_id: UUID,
    classroom_session_id: UUID | None,
    language_code: str,
    res: VoiceSynthesisResult,
) -> None:
    """Persist TTS telemetry into voice_usage_logs (zero-cost if cached or fallback)."""
    est_usd = (
        Decimal("0.000000")
        if (res.cache_hit or res.is_fallback)
        else (Decimal(res.characters_count) * Decimal("0.000030")).quantize(Decimal("0.000001"))
    )
    db.add(
        VoiceUsageLog(
            user_id=user_id,
            classroom_session_id=classroom_session_id,
            provider=res.provider,
            operation_type="tts",
            voice_id=res.voice_id,
            language_code=language_code,
            characters_count=res.characters_count,
            audio_seconds=round(res.estimated_duration_ms / 1000.0, 2),
            latency_ms=res.latency_ms,
            cache_hit=res.cache_hit,
            estimated_cost_usd=est_usd,
        )
    )


async def log_stt_usage(
    db: AsyncSession,
    *,
    user_id: UUID,
    classroom_session_id: UUID | None,
    res: STTTranscriptionResult,
) -> None:
    """Persist STT telemetry into voice_usage_logs."""
    est_usd = (
        Decimal("0.000000")
        if res.is_fallback
        else (Decimal(str(res.audio_seconds)) * Decimal("0.000100")).quantize(Decimal("0.000001"))
    )
    db.add(
        VoiceUsageLog(
            user_id=user_id,
            classroom_session_id=classroom_session_id,
            provider=res.provider,
            operation_type="stt",
            voice_id="scribe_v1",
            language_code=res.language_code,
            characters_count=len(res.transcript or ""),
            audio_seconds=res.audio_seconds,
            latency_ms=res.latency_ms,
            cache_hit=False,
            estimated_cost_usd=est_usd,
        )
    )
