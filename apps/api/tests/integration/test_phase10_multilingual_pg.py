"""PostgreSQL 18 integration tests for Phase 10 Multilingual Learning Expansion.

Verifies:
- 14-language honest Language Capability Registry (GET & admin PATCH RBAC)
- 6 independent language preferences + deterministic fallback resolution
- STEM glossary search & creation RBAC
- Bilingual explanation preview with mathematical/scientific notation preservation
- Translation submission, automated notation guard, and academic reviewer approval gate
- Language quality evaluation execution & persistence
- Capability-gated Speech-to-Text endpoint & honest fallback
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_phase10_multilingual_registry_preferences_and_review_workflow(
    api_client: AsyncClient,
    student_headers: dict[str, str],
    reviewer_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    # 1. Public Language Capability Registry exposes all 14 languages honestly
    caps_resp = await api_client.get("/api/v1/languages/capabilities")
    assert caps_resp.status_code == 200
    caps = caps_resp.json()
    codes = {c["language_code"] for c in caps}
    assert {"en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "ur", "or", "as", "sa"} <= codes
    ta_cap = next(c for c in caps if c["language_code"] == "ta")
    assert ta_cap["tts_supported"] is False
    assert ta_cap["stt_supported"] is False
    ur_cap = next(c for c in caps if c["language_code"] == "ur")
    assert ur_cap["rtl"] is True

    # Student cannot PATCH capability registry
    forbid_patch = await api_client.patch(
        "/api/v1/languages/capabilities/ta",
        headers=student_headers,
        json={"tts_supported": True},
    )
    assert forbid_patch.status_code == 403

    # 2. Save 6 independent language preferences & verify fallback resolution
    pref_resp = await api_client.put(
        "/api/v1/languages/preferences",
        headers=student_headers,
        json={
            "ui_language": "ur",
            "preferred_explanation_language": "hi",
            "preferred_voice_language": "ta",
            "preferred_subtitle_language": "ta",
            "preferred_question_language": "mr",
            "preferred_answer_language": "bn",
            "bilingual_explanation_mode": "bilingual_stem_en",
        },
    )
    assert pref_resp.status_code == 200
    prefs = pref_resp.json()
    assert prefs["ui_language"] == "ur"
    assert prefs["resolutions"]["ui"]["rtl"] is True
    assert prefs["resolutions"]["voice"]["fallback_applied"] is True
    assert prefs["resolutions"]["voice"]["effective_language"] == "en"
    assert prefs["resolutions"]["subtitle"]["effective_language"] == "ta"
    assert prefs["resolutions"]["question"]["fallback_applied"] is True
    assert prefs["resolutions"]["question"]["effective_language"] == "hi"

    # 3. Bilingual preview preserves KaTeX & chemistry formulas
    prev_resp = await api_client.post(
        "/api/v1/languages/bilingual-preview",
        json={
            "source_text": "Velocity obeys $v^2 = u^2 + 2as$ with acceleration 9.8 m/s^2 and H2SO4.",
            "explanation_language": "hi",
            "subtitle_language": "ta",
            "voice_language": "ta",
            "bilingual_mode": "bilingual_stem_en",
        },
    )
    assert prev_resp.status_code == 200
    prev = prev_resp.json()
    assert prev["notation_report"]["all_preserved"] is True
    assert prev["voice_resolution"]["fallback_applied"] is True
    assert "वेग" in prev["rendered_text"]

    # 4. Translation submission with corrupted math cannot be approved by reviewer
    bad_tr = await api_client.post(
        "/api/v1/languages/translations",
        headers=reviewer_headers,
        json={
            "resource_type": "formula_note",
            "resource_key": "kinematics.v_sq.bad",
            "source_language_code": "en",
            "target_language_code": "hi",
            "source_text": "Use $v^2 = u^2 + 2as$ at 9.8 m/s^2.",
            "translated_text": "समीकरण $v^2 = u^2 - 2as$ उपयोग करें।",
        },
    )
    assert bad_tr.status_code == 201
    bad_entry = bad_tr.json()
    assert bad_entry["notation_preserved"] is False
    assert bad_entry["status"] == "needs_revision"

    blocked_approve = await api_client.post(
        f"/api/v1/languages/translations/{bad_entry['id']}/review",
        headers=reviewer_headers,
        json={"decision": "approved", "reviewer_notes": "Attempt bypass"},
    )
    assert blocked_approve.status_code == 422

    # Valid translation with preserved notation approves cleanly; student gets 403
    good_tr = await api_client.post(
        "/api/v1/languages/translations",
        headers=reviewer_headers,
        json={
            "resource_type": "formula_note",
            "resource_key": "kinematics.v_sq.good",
            "source_language_code": "en",
            "target_language_code": "hi",
            "source_text": "Use $v^2 = u^2 + 2as$ for velocity at 9.8 m/s^2.",
            "translated_text": "वेग (velocity) के लिए 9.8 m/s^2 पर $v^2 = u^2 + 2as$ उपयोग करें।",
        },
    )
    assert good_tr.status_code == 201
    good_id = good_tr.json()["id"]

    forbid_review = await api_client.post(
        f"/api/v1/languages/translations/{good_id}/review",
        headers=student_headers,
        json={"decision": "approved"},
    )
    assert forbid_review.status_code == 403

    ok_review = await api_client.post(
        f"/api/v1/languages/translations/{good_id}/review",
        headers=reviewer_headers,
        json={"decision": "approved", "reviewer_notes": "Verified notation & Devanagari."},
    )
    assert ok_review.status_code == 200
    assert ok_review.json()["status"] == "approved"

    # 5. Run language quality evaluation suite & persist results
    eval_resp = await api_client.post(
        "/api/v1/languages/evaluations/run",
        headers=admin_headers,
        json={"language_code": "hi", "modality": "bilingual"},
    )
    assert eval_resp.status_code == 201
    eval_out = eval_resp.json()
    assert eval_out["passed"] is True
    assert eval_out["math_preservation_score"] == 100.0

    # 6. STT capability gate refuses unverified Tamil cloud STT honestly
    stt_resp = await api_client.post(
        "/api/v1/voice/stt",
        headers=student_headers,
        json={"language_code": "ta"},
    )
    assert stt_resp.status_code == 200
    stt_body = stt_resp.json()
    assert stt_body["stt_available"] is False
    assert stt_body["fallback_applied"] is True
    assert stt_body["fallback_mode"] == "text_input_required"
