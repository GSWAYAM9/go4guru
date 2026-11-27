"""Unit tests for Phase 6 Homework AI: upload security, OCR fallbacks, 5-subject evaluators & anti-spoiler guard."""

from __future__ import annotations

import asyncio
import struct
import zlib
from uuid import uuid4

import pytest

from src.core.config import Settings
from src.modules.ai.public import ProviderInvocationRequest, ProviderInvocationResult
from src.modules.homework.evaluator import (
    EvaluationDraft,
    detect_subject_area,
    evaluate_homework_submission,
    extract_question_and_steps,
    validate_evaluation_output,
)
from src.modules.homework.file_security import (
    FileValidationError,
    build_private_homework_storage_key,
    extract_pdf_embedded_text,
    validate_and_sanitize_upload,
)
from src.modules.homework.ocr import HomeworkOcrPipeline
from src.modules.homework.schemas import (
    SUBJECT_ERROR_CATEGORIES,
    ErrorClassificationOut,
    GraduatedHintOut,
)


def _make_minimal_jpeg(*, with_exif: bool = False) -> bytes:
    out = bytearray(b"\xff\xd8")
    if with_exif:
        exif_payload = b"Exif\x00\x00FakeCameraGPSData12345"
        out.extend(b"\xff\xe1")
        out.extend((len(exif_payload) + 2).to_bytes(2, "big"))
        out.extend(exif_payload)
    # Minimal APP0 + SOS + EOI
    app0 = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    out.extend(b"\xff\xe0")
    out.extend((len(app0) + 2).to_bytes(2, "big"))
    out.extend(app0)
    out.extend(b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x00\xff\xd9")
    return bytes(out)


def _make_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _make_minimal_png(*, with_text_meta: bool = False) -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    chunks = [b"\x89PNG\r\n\x1a\n", _make_png_chunk(b"IHDR", ihdr)]
    if with_text_meta:
        chunks.append(_make_png_chunk(b"tEXt", b"Author\x00StudentRealName"))
    chunks.append(_make_png_chunk(b"IDAT", idat))
    chunks.append(_make_png_chunk(b"IEND", b""))
    return b"".join(chunks)


def _make_minimal_pdf(text: str = "Solve 2x + 4 = 10", *, pages: int = 1, active_js: bool = False) -> bytes:
    page_objs = "\n".join(
        f"{i + 2} 0 obj\n<< /Type /Page /Parent 1 0 R >>\nendobj" for i in range(pages)
    )
    js_snippet = "\n/OpenAction << /S /JavaScript /JS (app.alert(1)) >>" if active_js else ""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = (
        "%PDF-1.4\n"
        f"1 0 obj\n<< /Type /Pages /Count {pages}{js_snippet} >>\nendobj\n"
        f"{page_objs}\n"
        "99 0 obj\n<< /Length 64 >>\nstream\n"
        f"BT /F1 12 Tf ({escaped}) Tj ET\n"
        "endstream\nendobj\n"
        "%%EOF\n"
    )
    return content.encode("latin-1")


class _StubGateway:
    """Deterministic stub replacing external LLM/Vision APIs in unit tests."""

    def __init__(self, vision_payload: dict | None = None, llm_payload: dict | None = None) -> None:
        self.vision_payload = vision_payload
        self.llm_payload = llm_payload

    async def invoke_or_fallback(
        self, req: ProviderInvocationRequest, preferred_provider: str = "auto"
    ) -> tuple[ProviderInvocationResult | None, list[str]]:
        if req.inline_media and self.vision_payload is not None:
            return (
                ProviderInvocationResult(
                    provider="gemini",
                    model_id="gemini-2.5-flash",
                    text="{}",
                    parsed_json=self.vision_payload,
                    tokens_in=100,
                    tokens_out=60,
                    latency_ms=42,
                ),
                [],
            )
        if not req.inline_media and self.llm_payload is not None:
            return (
                ProviderInvocationResult(
                    provider="gemini",
                    model_id="gemini-2.5-pro",
                    text="{}",
                    parsed_json=self.llm_payload,
                    tokens_in=200,
                    tokens_out=150,
                    latency_ms=55,
                ),
                [],
            )
        return None, ["no_provider_configured"]


def test_upload_security_magic_bytes_exif_stripping_and_pdf_blocks() -> None:
    # 1. JPEG EXIF stripped
    jpg = _make_minimal_jpeg(with_exif=True)
    res_jpg = validate_and_sanitize_upload(
        filename="../../secret/hw_page.jpg",
        raw_bytes=jpg,
        declared_content_type="image/jpeg",
        max_file_bytes=10_000_000,
        max_pdf_pages=10,
        page_index=1,
    )
    assert res_jpg.detected_format == "jpeg"
    assert res_jpg.exif_stripped is True
    assert b"FakeCameraGPSData" not in res_jpg.sanitized_bytes
    assert res_jpg.original_filename == "hw_page.jpg"

    # 2. PNG metadata stripped
    png = _make_minimal_png(with_text_meta=True)
    res_png = validate_and_sanitize_upload(
        filename="work.png",
        raw_bytes=png,
        declared_content_type="image/png",
        max_file_bytes=10_000_000,
        max_pdf_pages=10,
        page_index=1,
    )
    assert res_png.detected_format == "png"
    assert res_png.exif_stripped is True
    assert b"StudentRealName" not in res_png.sanitized_bytes

    # 3. Spoofed SVG disguised as PNG rejected
    with pytest.raises(FileValidationError) as svg_exc:
        validate_and_sanitize_upload(
            filename="fake.png",
            raw_bytes=b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            declared_content_type="image/png",
            max_file_bytes=10_000_000,
            max_pdf_pages=10,
            page_index=1,
        )
    assert svg_exc.value.code == "UNSAFE_FILE_TYPE"

    # 4. PDF with embedded JavaScript rejected
    with pytest.raises(FileValidationError) as pdf_js_exc:
        validate_and_sanitize_upload(
            filename="exploit.pdf",
            raw_bytes=_make_minimal_pdf("Solve x+1=2", active_js=True),
            declared_content_type="application/pdf",
            max_file_bytes=10_000_000,
            max_pdf_pages=10,
            page_index=1,
        )
    assert pdf_js_exc.value.code == "UNSAFE_PDF_PAYLOAD"

    # 5. PDF exceeding page limit rejected
    with pytest.raises(FileValidationError) as pdf_pages_exc:
        validate_and_sanitize_upload(
            filename="huge.pdf",
            raw_bytes=_make_minimal_pdf("Page text", pages=12),
            declared_content_type="application/pdf",
            max_file_bytes=10_000_000,
            max_pdf_pages=10,
            page_index=1,
        )
    assert pdf_pages_exc.value.code == "PDF_PAGE_LIMIT_EXCEEDED"

    # 6. Storage key ignores user filename
    key = build_private_homework_storage_key(
        student_id=uuid4(),
        submission_id=uuid4(),
        page_no=2,
        sha256=res_jpg.sha256,
        detected_format="jpeg",
    )
    assert key.startswith("homework/")
    assert "secret" not in key
    assert key.endswith(".jpg")


def test_pdf_embedded_text_and_ocr_fallback_honesty() -> None:
    pdf_bytes = _make_minimal_pdf("Question: Solve 2x + 4 = 10")
    assert "Solve 2x + 4 = 10" in extract_pdf_embedded_text(pdf_bytes)

    settings = Settings(homework_ocr_provider="auto", homework_ocr_min_confidence=0.65)
    pipeline_no_keys = HomeworkOcrPipeline(settings, ai_gateway=_StubGateway())

    # Digital PDF succeeds cleanly without external keys
    pdf_outcome = asyncio.run(
        pipeline_no_keys.extract_page(
            raw_bytes=pdf_bytes,
            detected_format="pdf",
            mime_type="application/pdf",
            page_no=1,
        )
    )
    assert pdf_outcome.ocr_provider == "pdf_text_stream"
    assert pdf_outcome.needs_review is False

    # Image without OCR keys returns honest low-confidence manual-review state (never fabricated text)
    img_outcome = asyncio.run(
        pipeline_no_keys.extract_page(
            raw_bytes=_make_minimal_jpeg(),
            detected_format="jpeg",
            mime_type="image/jpeg",
            page_no=1,
        )
    )
    assert img_outcome.needs_review is True
    assert img_outcome.extracted_text == ""
    assert img_outcome.confidence < 0.35

    # Multimodal Vision OCR handles handwriting cleanly when provider responds
    pipeline_vision = HomeworkOcrPipeline(
        settings,
        ai_gateway=_StubGateway(
            vision_payload={
                "extracted_text": "Solve 3x - 6 = 9\nStep 1: 3x = 15\nStep 2: x = 5",
                "extracted_latex": "3x - 6 = 9",
                "handwriting_detected": True,
                "confidence": 0.91,
                "warnings": [],
            }
        ),
    )
    vision_outcome = asyncio.run(
        pipeline_vision.extract_page(
            raw_bytes=_make_minimal_jpeg(),
            detected_format="jpeg",
            mime_type="image/jpeg",
            page_no=1,
        )
    )
    assert vision_outcome.ocr_provider == "gemini_vision"
    assert vision_outcome.handwriting_detected is True
    assert vision_outcome.handwriting_supported is True
    assert vision_outcome.needs_review is False


def test_subject_detection_and_five_subject_evaluators() -> None:
    settings = Settings(homework_ocr_min_confidence=0.65)
    stub = _StubGateway()

    assert detect_subject_area("Solve 2x + 5 = 11")[0] == "mathematics"
    assert detect_subject_area("Calculate force for mass 5 kg and acceleration 2 m/s^2")[0] == "physics"
    assert detect_subject_area("Balance the chemical equation H2 + O2 -> H2O")[0] == "chemistry"
    assert detect_subject_area("Write an essay paragraph checking grammar and tense")[0] == "english"
    assert (
        detect_subject_area("Explain the timeline and causes of the 1857 revolt in history")[0]
        == "social_science"
    )

    # 1. Mathematics: sign error detection
    math_draft, math_report, subj, _ = asyncio.run(
        evaluate_homework_submission(
            combined_text="Question: Solve x + 5 = 0\nStep 1: x = 5",
            selected_subject="mathematics",
            ocr_avg_confidence=0.95,
            settings=settings,
            ai_gateway=stub,
        )
    )
    assert subj == "mathematics"
    assert math_draft.overall_status == "needs_correction"
    assert any(e.category == "sign" for e in math_draft.error_classifications)
    assert math_report.spoiler_guard_passed is True

    # 2. Physics: missing SI units & formula
    phys_draft, _, _, _ = asyncio.run(
        evaluate_homework_submission(
            combined_text="Calculate the force acting on a 5 kg mass with acceleration 2 m/s^2\nStep 1: 5 * 2 = 10",
            selected_subject="physics",
            ocr_avg_confidence=0.95,
            settings=settings,
            ai_gateway=stub,
        )
    )
    phys_cats = {e.category for e in phys_draft.error_classifications}
    assert "units" in phys_cats
    assert "formula" in phys_cats

    # 3. Chemistry: unbalanced chemical equation detection
    chem_draft, _, _, _ = asyncio.run(
        evaluate_homework_submission(
            combined_text="Balance the reaction:\nStep 1: H2 + O2 -> H2O",
            selected_subject="chemistry",
            ocr_avg_confidence=0.95,
            settings=settings,
            ai_gateway=stub,
        )
    )
    assert any(e.category == "equation" for e in chem_draft.error_classifications)

    # 4. English: spelling & grammar check
    eng_draft, _, _, _ = asyncio.run(
        evaluate_homework_submission(
            combined_text="Explain why reading matters.\nStep 1: he are going to recieve teh award tommorow.",
            selected_subject="english",
            ocr_avg_confidence=0.95,
            settings=settings,
            ai_gateway=stub,
        )
    )
    eng_cats = {e.category for e in eng_draft.error_classifications}
    assert "spelling" in eng_cats
    assert "grammar" in eng_cats

    # 5. Social Science: missing points & map/timeline check
    soc_draft, _, _, _ = asyncio.run(
        evaluate_homework_submission(
            combined_text="Explain the timeline and causes of the Non-Cooperation Movement.\nStep 1: People protested.",
            selected_subject="social_science",
            ocr_avg_confidence=0.95,
            settings=settings,
            ai_gateway=stub,
        )
    )
    soc_cats = {e.category for e in soc_draft.error_classifications}
    assert "missing_points" in soc_cats
    assert "map_timeline" in soc_cats


def test_feedback_validation_enforces_taxonomy_anti_spoiler_and_low_ocr_gate() -> None:
    draft = EvaluationDraft(
        subject_area="mathematics",
        detected_question="Solve 2x + 4 = 10",
        student_work_summary="1 step",
        extracted_steps=[],
        step_evaluations=[],
        error_classifications=[
            ErrorClassificationOut(
                subject_area="mathematics",
                category="made_up_category",
                severity="high",
                step_no=1,
                summary="Invalid taxonomy test",
                guidance="Fix it",
            )
        ],
        overall_status="needs_correction",
        feedback_summary="Review Step 1.",
        strengths=[],
        hints=[
            GraduatedHintOut(
                level=1,
                stage="conceptual_nudge",
                title="Level 1",
                content_markdown="The final answer is x = 3.",
            ),
            GraduatedHintOut(
                level=2,
                stage="method_scaffold",
                title="Level 2",
                content_markdown="Solve to get x = 3 immediately.",
            ),
            GraduatedHintOut(
                level=3,
                stage="targeted_correction",
                title="Level 3",
                content_markdown="Check subtraction on Step 1.",
            ),
        ],
        complete_solution_markdown="2x = 6 -> x = 3",
        verifier_results={"checks": [{"verified": True, "computed_value": "x = [3]"}]},
        revision_recommendations=[],
        confidence=0.92,
        provider_used="gemini",
        model_id="gemini-2.5-pro",
        is_fallback=False,
    )

    validated, report = validate_evaluation_output(
        draft,
        ocr_min_confidence=0.65,
        ocr_avg_confidence=0.30,
    )
    assert report.taxonomy_valid is False
    assert validated.error_classifications[0].category in SUBJECT_ERROR_CATEGORIES["mathematics"]
    assert report.spoiler_guard_passed is False
    assert "x = 3" not in validated.hints[0].content_markdown
    assert "x = 3" not in validated.hints[1].content_markdown
    assert report.confidence_adjusted is True
    assert validated.overall_status == "unreadable_or_uncertain"

    q, steps = extract_question_and_steps("Question: Solve 2x = 6\nStep 1: x = 3")
    assert q == "Solve 2x = 6"
    assert len(steps) == 1
    assert steps[0].expression == "x = 3"
