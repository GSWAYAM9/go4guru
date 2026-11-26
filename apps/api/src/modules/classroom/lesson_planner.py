"""Structured LessonArtifact Planner & Timed Subtitle/Whiteboard Synchronizer."""

from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.classroom.schemas import (
    CheckpointOption,
    CheckpointSpec,
    LessonArtifact,
    LessonGenerateRequest,
    LessonSegment,
    SubtitleCue,
    WhiteboardActionSchema,
)
from src.modules.curriculum.public import resolve_tutor_curriculum_context


def _sample_parabola_points(x_min: float = -4.0, x_max: float = 4.0) -> list[list[float]]:
    pts: list[list[float]] = []
    step = 0.5
    cur = x_min
    while cur <= x_max + 1e-9:
        pts.append([round(cur, 2), round(0.5 * cur * cur, 2)])
        cur += step
    return pts


def _chunk_narration_to_cues(narration: str, duration_ms: int) -> list[SubtitleCue]:
    sentences = [
        s.strip() for s in narration.replace("!", ".").replace("?", ".").split(".") if s.strip()
    ]
    if not sentences:
        return [SubtitleCue(start_ms=0, end_ms=duration_ms, text=narration[:300])]
    slice_ms = max(1000, duration_ms // len(sentences))
    cues: list[SubtitleCue] = []
    pos = 0
    for idx, sent in enumerate(sentences):
        end = duration_ms if idx == len(sentences) - 1 else min(duration_ms, pos + slice_ms)
        cues.append(SubtitleCue(start_ms=pos, end_ms=max(pos + 500, end), text=f"{sent}."))
        pos = end
    return cues


async def generate_structured_lesson(
    db: AsyncSession, payload: LessonGenerateRequest, student_id: UUID
) -> LessonArtifact:
    """Build schema-validated LessonArtifact grounded in published curriculum metadata."""
    _ = student_id
    curr = await resolve_tutor_curriculum_context(
        db,
        subject_id=payload.subject_id,
        chapter_id=payload.chapter_id,
        concept_id=payload.concept_id,
    )
    topic = payload.topic_title.strip()
    subject_label = curr.subject_name or "STEM"
    lang = payload.language_code.strip() or "en"
    objectives = list(curr.learning_objectives) or [
        f"Explain core physical or mathematical principles of {topic}.",
        f"Interpret graphical and symbolic equations for {topic} with SI units.",
        f"Solve a verification checkpoint on {topic}.",
    ]

    # Segment 1: Concept Explanation + Diagram & Arrows
    s1_narration = (
        f"Welcome to this live interactive lesson on {topic}. "
        f"We begin by drawing a clear coordinate reference and vector diagram. "
        f"Observe how key quantities relate proportionally across the system."
    )
    s1_dur = 12000
    s1_actions = [
        WhiteboardActionSchema(
            id="s1_heading",
            opcode="WRITE_TEXT",
            sequence=1,
            at_ms=0,
            aria_summary=f"Title heading: {topic}",
            payload={
                "x": 40,
                "y": 40,
                "text": f"{subject_label}: {topic}",
                "font_size": 22,
                "color": "#0f172a",
                "max_width": 680,
            },
        ),
        WhiteboardActionSchema(
            id="s1_box",
            opcode="DRAW_SHAPE",
            sequence=2,
            at_ms=1500,
            aria_summary="Core concept summary box around key definition.",
            payload={
                "shape": "rect",
                "x": 40,
                "y": 90,
                "w": 300,
                "h": 95,
                "stroke": "#4338ca",
                "fill": "#eef2ff",
                "label": f"Core Model: {topic}",
            },
        ),
        WhiteboardActionSchema(
            id="s1_baseline",
            opcode="DRAW_LINE",
            sequence=3,
            at_ms=3200,
            aria_summary="Horizontal reference line dividing system states.",
            payload={
                "x1": 60,
                "y1": 240,
                "x2": 520,
                "y2": 240,
                "stroke": "#334155",
                "style": "dashed",
            },
        ),
        WhiteboardActionSchema(
            id="s1_arrow",
            opcode="DRAW_ARROW",
            sequence=4,
            at_ms=4800,
            aria_summary="Vector arrow showing direction of net rate of change.",
            payload={
                "x1": 120,
                "y1": 240,
                "x2": 320,
                "y2": 150,
                "stroke": "#059669",
                "label": "Direction / Net Effect",
            },
        ),
        WhiteboardActionSchema(
            id="s1_diagram",
            opcode="DRAW_DIAGRAM",
            sequence=5,
            at_ms=7200,
            aria_summary="Structured system diagram template illustrating input to response.",
            payload={
                "template": "mind_map",
                "x": 400,
                "y": 85,
                "title": topic,
                "nodes": ["Input Parameter", "Governing Law", "Measured Output"],
            },
        ),
    ]

    # Segment 2: Worked Example + Formula + Graph + Highlight
    s2_narration = (
        "Next let us apply the governing mathematical relationship $y = 0.5 x^2$ "
        "and plot how $y$ changes across negative and positive values of $x$. "
        "Notice the highlight showing symmetry around the vertical axis."
    )
    s2_dur = 14000
    s2_actions = [
        WhiteboardActionSchema(
            id="s2_formula",
            opcode="INSERT_FORMULA",
            sequence=10,
            at_ms=0,
            aria_summary="Formula inserted: y equals 0.5 x squared.",
            payload={
                "x": 40,
                "y": 270,
                "latex": r"y = \frac{1}{2}x^2 \quad (\text{symmetric quadratic model})",
                "font_size": 18,
                "color": "#1e1b4b",
            },
        ),
        WhiteboardActionSchema(
            id="s2_graph",
            opcode="DRAW_GRAPH",
            sequence=11,
            at_ms=3000,
            aria_summary="2D Cartesian graph plotting y = 0.5 x^2 from -4 to 4.",
            payload={
                "x": 380,
                "y": 230,
                "w": 280,
                "h": 170,
                "x_label": "x",
                "y_label": "y",
                "x_range": [-4, 4],
                "y_range": [0, 8],
                "series": [{"label": "y = 0.5x^2", "points": _sample_parabola_points()}],
            },
        ),
        WhiteboardActionSchema(
            id="s2_hl",
            opcode="HIGHLIGHT",
            sequence=12,
            at_ms=7500,
            aria_summary="Highlighting key formula box.",
            payload={"target_id": "s2_formula", "color": "#f59e0b", "duration_ms": 2500},
        ),
    ]

    # Segment 3: Interactive Checkpoint Question
    s3_narration = (
        f"Now let us pause for a quick checkpoint on {topic}. "
        f"Evaluate the value of $0.5 x^2$ when $x = 4$, and pick the matching option."
    )
    s3_dur = 9000
    s3_actions = [
        WhiteboardActionSchema(
            id="s3_prompt",
            opcode="WRITE_TEXT",
            sequence=20,
            at_ms=0,
            aria_summary="Checkpoint prompt on board: Evaluate y = 0.5 * 4^2.",
            payload={
                "x": 40,
                "y": 350,
                "text": "Checkpoint: At x = 4, what is y = 0.5 * x^2?",
                "font_size": 16,
                "color": "#7c2d12",
                "max_width": 320,
            },
        ),
    ]
    checkpoint = CheckpointSpec(
        question_type="mcq_single",
        prompt=f"[{topic}] Using $y = 0.5 x^2$, what is the value of $y$ when $x = 4$?",
        options=[
            CheckpointOption(key="A", text="$4$"),
            CheckpointOption(key="B", text="$8$"),
            CheckpointOption(key="C", text="$16$"),
        ],
        correct_key="B",
        remediation_hint="First square x = 4 to obtain 16, then multiply by 0.5.",
    )

    # Segment 4: Summary & Key Takeaways
    s4_narration = (
        "Great work completing the checkpoint! Remember that structured visual models, "
        f"symbolic equations, and dimensional checks together prevent common mistakes in {topic}."
    )
    s4_dur = 8000
    s4_actions = [
        WhiteboardActionSchema(
            id="s4_summary",
            opcode="WRITE_TEXT",
            sequence=30,
            at_ms=0,
            aria_summary="Summary takeaway written on whiteboard.",
            payload={
                "x": 40,
                "y": 400,
                "text": f"Summary: Check units & symmetry every time you apply {topic}.",
                "font_size": 15,
                "color": "#065f46",
                "max_width": 600,
            },
        ),
    ]

    _ = math.isfinite(1.0)
    segments = [
        LessonSegment(
            sequence=1,
            type="concept_explanation",
            title=f"1. Visual Intuition: {topic}",
            narration=s1_narration,
            subtitle_cues=_chunk_narration_to_cues(s1_narration, s1_dur),
            canvas_actions=s1_actions,
            checkpoint=None,
            duration_ms=s1_dur,
        ),
        LessonSegment(
            sequence=2,
            type="worked_example",
            title=f"2. Equation & Graph: {topic}",
            narration=s2_narration,
            subtitle_cues=_chunk_narration_to_cues(s2_narration, s2_dur),
            canvas_actions=s2_actions,
            checkpoint=None,
            duration_ms=s2_dur,
        ),
        LessonSegment(
            sequence=3,
            type="checkpoint_question",
            title="3. Quick Understanding Check",
            narration=s3_narration,
            subtitle_cues=_chunk_narration_to_cues(s3_narration, s3_dur),
            canvas_actions=s3_actions,
            checkpoint=checkpoint,
            duration_ms=s3_dur,
        ),
        LessonSegment(
            sequence=4,
            type="summary",
            title="4. Key Exam Takeaways",
            narration=s4_narration,
            subtitle_cues=_chunk_narration_to_cues(s4_narration, s4_dur),
            canvas_actions=s4_actions,
            checkpoint=None,
            duration_ms=s4_dur,
        ),
    ]

    return LessonArtifact(
        schema_version="1.0.0",
        title=f"{subject_label}: {topic}",
        curriculum_context={
            "board": curr.board_code or "CBSE",
            "grade": curr.grade_number,
            "subject": subject_label,
            "chapter": curr.chapter_title,
            "concept": curr.concept_title or topic,
        },
        language=lang,
        voice_language=payload.voice_language.strip() or lang,
        subtitle_language=payload.subtitle_language.strip() or lang,
        objectives=objectives,
        segments=segments,
    )
