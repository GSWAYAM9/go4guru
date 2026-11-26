"""Unit tests for Phase 4 Math-to-Speech, ElevenLabs Adapter/Caching & Whiteboard Safety."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from src.core.config import Settings
from src.modules.classroom.schemas import TTSResponseOut, WhiteboardActionSchema
from src.modules.classroom.voice.provider import (
    ElevenLabsVoiceAdapter,
    chunk_tts_text,
    normalize_math_for_speech,
)
from src.modules.classroom.whiteboard_engine import reduce_actions_to_list


def test_normalize_math_for_speech_and_chunking() -> None:
    text = (
        "Let $y = x^2 + \\sin(x)$ and $v^3 - u_1 = 2\\times a$. "
        "Calculate the result carefully across the parabola."
    )
    spoken = normalize_math_for_speech(text)
    assert "$" not in spoken
    assert "y equals x squared plus sine (x)" in spoken
    assert "v cubed minus u sub 1 equals 2 times a" in spoken

    long_text = " ".join(f"Sentence number {i} explains kinematics." for i in range(1, 25))
    chunks = chunk_tts_text(long_text, max_chars=120)
    assert len(chunks) > 1
    assert all(len(c) <= 120 for c in chunks)


def test_whiteboard_action_schema_blocks_xss_and_external_urls() -> None:
    with pytest.raises(ValidationError):
        WhiteboardActionSchema(
            id="bad_script",
            opcode="WRITE_TEXT",
            sequence=1,
            at_ms=0,
            aria_summary="Malicious script attempt",
            payload={"text": "<script>alert(1)</script>"},
        )

    with pytest.raises(ValidationError):
        WhiteboardActionSchema(
            id="bad_js",
            opcode="WRITE_TEXT",
            sequence=2,
            at_ms=0,
            aria_summary="javascript:void(0)",
            payload={"text": "Safe label"},
        )

    with pytest.raises(ValidationError):
        WhiteboardActionSchema(
            id="bad_img_url",
            opcode="INSERT_IMAGE",
            sequence=3,
            at_ms=0,
            aria_summary="External URL blocked",
            payload={"src": "https://evil.example/img.png"},
        )

    valid = WhiteboardActionSchema(
        id="ok_formula",
        opcode="INSERT_FORMULA",
        sequence=4,
        at_ms=500,
        aria_summary="Quadratic formula on board",
        payload={"x": 40, "y": 120, "latex": r"y = \frac{1}{2}x^2"},
    )
    assert valid.opcode == "INSERT_FORMULA"


def test_reduce_actions_to_list_move_transform_highlight_erase() -> None:
    a1 = WhiteboardActionSchema(
        id="box1",
        opcode="DRAW_SHAPE",
        sequence=1,
        at_ms=0,
        aria_summary="Rectangle box 1",
        payload={"shape": "rect", "x": 10, "y": 20, "w": 100, "h": 50},
    )
    a2 = WhiteboardActionSchema(
        id="box2",
        opcode="DRAW_SHAPE",
        sequence=2,
        at_ms=100,
        aria_summary="Circle box 2",
        payload={"shape": "circle", "x": 200, "y": 200, "r": 30},
    )
    move1 = WhiteboardActionSchema(
        id="m1",
        opcode="MOVE",
        sequence=3,
        at_ms=200,
        aria_summary="Move box1",
        payload={"target_id": "box1", "dx": 25, "dy": -10},
    )
    t1 = WhiteboardActionSchema(
        id="t1",
        opcode="TRANSFORM",
        sequence=4,
        at_ms=250,
        aria_summary="Rotate box1",
        payload={"target_id": "box1", "rotate_deg": 15, "scale_x": 1.2},
    )
    hi1 = WhiteboardActionSchema(
        id="h1",
        opcode="HIGHLIGHT",
        sequence=5,
        at_ms=300,
        aria_summary="Highlight box1",
        payload={"target_id": "box1", "color": "#f59e0b"},
    )
    erase2 = WhiteboardActionSchema(
        id="e1",
        opcode="ERASE",
        sequence=6,
        at_ms=350,
        aria_summary="Erase box2",
        payload={"target_id": "box2"},
    )
    reduced = reduce_actions_to_list([erase2, hi1, t1, move1, a2, a1])
    assert len(reduced) == 1
    item = reduced[0]
    assert item.id == "box1"
    assert item.payload["dx"] == 25.0
    assert item.payload["dy"] == -10.0
    assert item.payload["rotate_deg"] == 15
    assert item.payload["scale_x"] == 1.2
    assert item.payload["highlighted"] is True


async def test_elevenlabs_adapter_unconfigured_honest_fallback(tmp_path: Path) -> None:
    settings = Settings(
        app_env="test",
        storage_local_dir=str(tmp_path / "voice_unconf"),
        elevenlabs_api_key=SecretStr(""),
    )
    adapter = ElevenLabsVoiceAdapter(settings)
    res = await adapter.synthesize_speech(text="Force $F = ma$", language_code="en")
    assert res.audio_available is False
    assert res.audio_bytes is None
    assert res.is_fallback is True
    assert res.fallback_mode == "timed_subtitles_only"
    assert res.provider == "none_configured"
    assert "F equals ma" in res.normalized_text


async def test_elevenlabs_adapter_http_synthesis_sha256_cache_and_500_fallback(
    tmp_path: Path,
) -> None:
    call_count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        assert request.headers["xi-api-key"] == "test-elevenlabs-key"
        if "fail" in request.url.path:
            return httpx.Response(500, json={"detail": "upstream error"})
        return httpx.Response(200, content=b"ID3-FAKE-MP3-PAYLOAD-CHUNK")

    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport) as mock_http:
        settings = Settings(
            app_env="test",
            storage_local_dir=str(tmp_path / "voice_conf"),
            elevenlabs_api_key=SecretStr("test-elevenlabs-key"),
        )
        adapter = ElevenLabsVoiceAdapter(settings, http_client=mock_http)

        # First call hits mock HTTP API and writes SHA-256 cached MP3
        res1 = await adapter.synthesize_speech(
            text="Energy equals $m c^2$.",
            language_code="en",
            voice_id="voiceA",
            speed=1.0,
        )
        assert res1.audio_available is True
        assert res1.cache_hit is False
        assert res1.is_fallback is False
        assert res1.audio_bytes == b"ID3-FAKE-MP3-PAYLOAD-CHUNK"
        assert res1.cache_key is not None
        assert call_count == 1

        # Second identical call serves cleanly from disk cache (zero upstream calls)
        res2 = await adapter.synthesize_speech(
            text="Energy equals $m c^2$.",
            language_code="en",
            voice_id="voiceA",
            speed=1.0,
        )
        assert res2.audio_available is True
        assert res2.cache_hit is True
        assert res2.audio_bytes == b"ID3-FAKE-MP3-PAYLOAD-CHUNK"
        assert call_count == 1

        # Stream chunks yields bytes
        streamed = b"".join(
            [
                chunk
                async for chunk in adapter.stream_speech(
                    text="Energy equals $m c^2$.",
                    language_code="en",
                    voice_id="voiceA",
                    speed=1.0,
                )
            ]
        )
        assert streamed == b"ID3-FAKE-MP3-PAYLOAD-CHUNK"

        # Upstream HTTP 500 degrades honestly to subtitles
        res_err = await adapter.synthesize_speech(
            text="Force equals mass times acceleration.",
            language_code="en",
            voice_id="voice-fail",
            speed=1.0,
        )
        assert res_err.audio_available is False
        assert res_err.is_fallback is True
        assert res_err.provider == "elevenlabs_degraded"
        assert res_err.fallback_mode == "timed_subtitles_only"

        # Schema check
        out = TTSResponseOut(
            audio_available=res2.audio_available,
            audio_url="/api/v1/voice/audio/sample.mp3",
            cache_key=res2.cache_key,
            normalized_speakable_text=res2.normalized_text,
            provider=res2.provider,
            voice_id=res2.voice_id,
            language_code="en",
            characters_count=res2.characters_count,
            estimated_duration_ms=res2.estimated_duration_ms,
            cache_hit=res2.cache_hit,
            is_fallback=res2.is_fallback,
        )
        assert out.cache_hit is True
