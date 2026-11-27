"""Pure-stdlib Phase 9 Examination Preparation domain logic.

Covers:
1. Strict PYQ provenance validation (never fabricates or upgrades AI/unverified items).
2. Versioned exam-specific scoring & section attempt-limit evaluation
   (CBSE Board, JEE Main, JEE Advanced exact partial-subset, NEET).
3. Honest dataset & syllabus coverage auditing (never claims complete coverage
   unless every mapped chapter is explicitly audited and backed by published items).
4. Exam analytics: accuracy, speed (seconds/question vs target pace), pacing diagnosis,
   weak subjects/chapters/concepts, performance history, and improvement recommendations.
5. Deterministic exam revision schedule generation prioritizing weak high-yield chapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

VALID_EXAM_CODES = ("CBSE_BOARD", "JEE_MAIN", "JEE_ADVANCED", "NEET")

# Target seconds per question based on canonical exam timing ratios
EXAM_TARGET_SECONDS_PER_QUESTION: dict[str, int] = {
    "CBSE_BOARD": 108,  # ~3h for ~35-40 mixed objective/subjective questions (scaled per item)
    "JEE_MAIN": 144,  # 180 min / 75 questions = 144s/Q
    "JEE_ADVANCED": 180,  # 180 min / ~54-60 questions = 180s/Q
    "NEET": 60,  # 180 min / 180 questions = 60s/Q
}

PRIORITY_RANK: dict[str, int] = {
    "high_yield": 3,
    "core": 2,
    "optional": 1,
}


# ---------------------------------------------------------------------------
# 1. Strict PYQ Provenance Verification (Zero Fabrication Policy)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PyqProvenanceInput:
    """Raw provenance + question metadata evaluated for verified PYQ eligibility."""

    is_pyq: bool
    ai_generated: bool
    source_type: str | None
    verification_status: str | None
    verified_by: str | None
    exam_name: str | None
    exam_year: int | None
    exam_session: str | None = None
    exam_shift: str | None = None
    paper_code: str | None = None
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class PyqVerificationDecision:
    """Deterministic provenance gate result."""

    is_verified_pyq: bool
    badge_label: str | None
    rejection_reasons: tuple[str, ...]


def validate_pyq_provenance(item: PyqProvenanceInput) -> PyqVerificationDecision:
    """Enforce strict PYQ provenance: never label AI or unverified questions as PYQs."""
    reasons: list[str] = []

    if not item.is_pyq:
        reasons.append("not_marked_as_pyq")
    if item.ai_generated:
        reasons.append("ai_generated_questions_cannot_be_pyq")
    if (item.source_type or "").strip().lower() in {"ai_generated", "synthetic", "generated"}:
        reasons.append("synthetic_source_type_disallowed_for_pyq")
    if (item.verification_status or "").strip().lower() != "verified":
        reasons.append("verification_status_not_verified")
    if not (item.verified_by and str(item.verified_by).strip()):
        reasons.append("missing_verifier_identity")

    exam_name = (item.exam_name or "").strip()
    if not exam_name:
        reasons.append("missing_exam_name")

    if item.exam_year is None or not (1980 <= int(item.exam_year) <= 2035):
        reasons.append("invalid_or_missing_exam_year")

    if reasons:
        return PyqVerificationDecision(
            is_verified_pyq=False,
            badge_label=None,
            rejection_reasons=tuple(reasons),
        )

    parts = [exam_name, str(item.exam_year)]
    if item.exam_session and item.exam_session.strip():
        parts.append(item.exam_session.strip())
    if item.exam_shift and item.exam_shift.strip():
        parts.append(item.exam_shift.strip())
    return PyqVerificationDecision(
        is_verified_pyq=True,
        badge_label=" · ".join(parts),
        rejection_reasons=(),
    )


# ---------------------------------------------------------------------------
# 2. Exam-Specific Scoring Rules (CBSE, JEE Main, JEE Advanced, NEET)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PureScoringRule:
    """Stdlib representation of a configurable, versioned section scoring rule."""

    mode: str = "standard"  # standard | partial_subset | jee_adv_partial | match_following
    correct_marks: float = 4.0
    wrong_marks: float = -1.0
    unanswered_marks: float = 0.0
    partial_credit_per_correct_option: float = 0.0


@dataclass(frozen=True, slots=True)
class PureEvaluatedAnswer:
    """Deterministic grading outcome for a single exam question."""

    attempted: bool
    is_correct: bool
    is_partial: bool
    marks_awarded: float


def is_answer_blank(question_type: str, response: dict[str, Any]) -> bool:
    """Return True if the student left the question unattempted."""
    if not response:
        return True
    if question_type in {"mcq_single", "assertion_reason", "case_study"}:
        return not str(response.get("selected_key") or "").strip()
    if question_type == "mcq_multiple":
        keys = response.get("selected_keys")
        return not isinstance(keys, list) or len([k for k in keys if str(k).strip()]) == 0
    if question_type in {"numerical", "integer"}:
        val = response.get("numeric_value")
        return val is None or str(val).strip() == ""
    if question_type in {"match_following", "matrix_match"}:
        mapping = response.get("matches")
        return not isinstance(mapping, dict) or len(mapping) == 0
    return not str(response.get("text_answer") or "").strip()


def evaluate_exam_response(
    *,
    question_type: str,
    correct_answer: dict[str, Any],
    response: dict[str, Any],
    rule: PureScoringRule,
) -> PureEvaluatedAnswer:
    """Grade one question deterministically using versioned exam scoring rules."""
    if is_answer_blank(question_type, response):
        return PureEvaluatedAnswer(
            attempted=False,
            is_correct=False,
            is_partial=False,
            marks_awarded=float(rule.unanswered_marks),
        )

    if question_type in {"mcq_single", "assertion_reason", "case_study"}:
        expected = str(correct_answer.get("correct_key", "")).strip().upper()
        given = str(response.get("selected_key", "")).strip().upper()
        ok = bool(expected and given == expected)
        return PureEvaluatedAnswer(
            attempted=True,
            is_correct=ok,
            is_partial=False,
            marks_awarded=float(rule.correct_marks if ok else rule.wrong_marks),
        )

    if question_type == "mcq_multiple":
        expected_set = {
            str(k).strip().upper()
            for k in correct_answer.get("correct_keys", [])
            if str(k).strip()
        }
        given_raw = response.get("selected_keys", [])
        given_set = (
            {str(k).strip().upper() for k in given_raw if str(k).strip()}
            if isinstance(given_raw, list)
            else set()
        )
        if not expected_set:
            return PureEvaluatedAnswer(True, False, False, float(rule.wrong_marks))

        if given_set == expected_set:
            return PureEvaluatedAnswer(True, True, False, float(rule.correct_marks))

        # Selecting ANY wrong option incurs full negative penalty immediately
        if not given_set.issubset(expected_set):
            return PureEvaluatedAnswer(True, False, False, float(rule.wrong_marks))

        # Exact JEE Advanced partial-marking scheme (+4 / +3 / +2 / +1 / 0 / -2):
        # +4 if all correct; +3 if all 4 correct & 3 chosen; +2 if >=3 correct & 2 chosen;
        # +1 if >=2 correct & 1 chosen (generalized safely for any correct_marks >= 4).
        if rule.mode == "jee_adv_partial":
            n_exp = len(expected_set)
            n_chosen = len(given_set)
            partial_score = 0.0
            if n_exp == 4 and n_chosen == 3:
                partial_score = min(float(rule.correct_marks), 3.0)
            elif n_exp >= 3 and n_chosen == 2:
                partial_score = min(float(rule.correct_marks), 2.0)
            elif n_exp >= 2 and n_chosen == 1:
                partial_score = min(float(rule.correct_marks), 1.0)
            return PureEvaluatedAnswer(
                attempted=True,
                is_correct=False,
                is_partial=partial_score > 0,
                marks_awarded=partial_score,
            )

        if rule.mode == "partial_subset" and rule.partial_credit_per_correct_option > 0:
            partial_score = min(
                float(rule.correct_marks),
                float(len(given_set) * rule.partial_credit_per_correct_option),
            )
            return PureEvaluatedAnswer(
                attempted=True,
                is_correct=False,
                is_partial=partial_score > 0,
                marks_awarded=partial_score,
            )

        return PureEvaluatedAnswer(True, False, False, float(rule.wrong_marks))

    if question_type in {"numerical", "integer"}:
        try:
            expected_val = float(correct_answer["expected_value"])
            tol = float(correct_answer.get("tolerance_abs", 0.0 if question_type == "integer" else 0.01))
            given_val = float(response["numeric_value"])
        except (KeyError, TypeError, ValueError):
            return PureEvaluatedAnswer(True, False, False, float(rule.wrong_marks))
        ok = abs(given_val - expected_val) <= tol
        return PureEvaluatedAnswer(
            attempted=True,
            is_correct=ok,
            is_partial=False,
            marks_awarded=float(rule.correct_marks if ok else rule.wrong_marks),
        )

    if question_type in {"match_following", "matrix_match"}:
        expected_map = correct_answer.get("expected_matches")
        given_map = response.get("matches")
        if not isinstance(expected_map, dict) or not isinstance(given_map, dict) or not expected_map:
            return PureEvaluatedAnswer(True, False, False, float(rule.wrong_marks))
        norm_expected = {
            str(k).strip().upper(): str(v).strip().upper() for k, v in expected_map.items()
        }
        norm_given = {
            str(k).strip().upper(): str(v).strip().upper() for k, v in given_map.items()
        }
        ok = norm_given == norm_expected
        return PureEvaluatedAnswer(
            attempted=True,
            is_correct=ok,
            is_partial=False,
            marks_awarded=float(rule.correct_marks if ok else rule.wrong_marks),
        )

    expected_text = str(correct_answer.get("expected_text", "")).strip().lower()
    given_text = str(response.get("text_answer", "")).strip().lower()
    ok = bool(expected_text and given_text == expected_text)
    return PureEvaluatedAnswer(
        attempted=True,
        is_correct=ok,
        is_partial=False,
        marks_awarded=float(rule.correct_marks if ok else rule.wrong_marks),
    )


def apply_section_attempt_limit(
    results_in_sequence: list[PureEvaluatedAnswer],
    *,
    attempt_limit: int | None,
    unanswered_marks: float = 0.0,
) -> tuple[list[PureEvaluatedAnswer], int]:
    """Enforce optional-section caps (e.g. NEET Sec-B 10/15, JEE Main Sec-B 5/10).

    Returns (adjusted_results, excess_discarded_count). Questions attempted beyond
    `attempt_limit` in sequence order are NOT scored (set to unanswered_marks).
    """
    if attempt_limit is None:
        return list(results_in_sequence), 0

    counted = 0
    discarded = 0
    adjusted: list[PureEvaluatedAnswer] = []
    for res in results_in_sequence:
        if not res.attempted:
            adjusted.append(res)
            continue
        if counted < attempt_limit:
            counted += 1
            adjusted.append(res)
        else:
            discarded += 1
            adjusted.append(
                PureEvaluatedAnswer(
                    attempted=False,
                    is_correct=False,
                    is_partial=False,
                    marks_awarded=float(unanswered_marks),
                )
            )
    return adjusted, discarded


# ---------------------------------------------------------------------------
# 3. Honest Coverage Audit (Never Claim Complete Coverage Without Audit)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChapterCoverageInput:
    chapter_id: str
    audit_verified: bool
    syllabus_status: str
    published_question_count: int
    verified_pyq_count: int


@dataclass(frozen=True, slots=True)
class ExamCoverageAudit:
    exam_code: str
    mapped_chapters_count: int
    included_chapters_count: int
    audited_chapters_count: int
    chapters_with_questions_count: int
    published_question_count: int
    verified_pyq_count: int
    unverified_pyq_excluded_count: int
    audited_coverage_pct: float
    question_coverage_pct: float
    coverage_status: str  # empty | partial_unverified | audited_partial | audited_complete
    coverage_disclaimer: str


def compute_exam_coverage_audit(
    *,
    exam_code: str,
    chapters: list[ChapterCoverageInput],
    total_published_questions: int,
    total_verified_pyqs: int,
    unverified_pyq_excluded_count: int = 0,
) -> ExamCoverageAudit:
    """Compute honest syllabus & verified-PYQ coverage status without exaggeration."""
    mapped = len(chapters)
    included = [c for c in chapters if c.syllabus_status != "excluded"]
    included_count = len(included)
    audited_count = sum(1 for c in included if c.audit_verified)
    with_questions = sum(1 for c in included if c.published_question_count > 0)

    audited_pct = round((audited_count / included_count) * 100.0, 1) if included_count > 0 else 0.0
    question_pct = (
        round((with_questions / included_count) * 100.0, 1) if included_count > 0 else 0.0
    )

    if included_count == 0 and total_published_questions == 0:
        status = "empty"
        disclaimer = (
            "No syllabus chapters or published questions are currently mapped for this exam track. "
            "Add audited syllabus mappings and verified questions before treating coverage as complete."
        )
    elif (
        included_count > 0
        and audited_count == included_count
        and with_questions == included_count
        and total_published_questions > 0
    ):
        status = "audited_complete"
        disclaimer = (
            f"All {included_count} mapped syllabus chapters have been explicitly audited "
            f"and backed by {total_published_questions} published questions "
            f"({total_verified_pyqs} verified PYQs)."
        )
    elif audited_count > 0:
        status = "audited_partial"
        disclaimer = (
            f"Partial audited coverage: {audited_count}/{included_count} included chapters audited, "
            f"{with_questions}/{included_count} have published questions, and "
            f"{total_verified_pyqs} verified PYQs are available. Complete exam coverage is not claimed."
        )
    else:
        status = "partial_unverified"
        disclaimer = (
            f"Coverage is currently unverified ({audited_count}/{included_count} chapters audited; "
            f"{total_published_questions} published questions; {total_verified_pyqs} verified PYQs). "
            "Complete syllabus and PYQ coverage is not claimed until academic audit completes."
        )

    return ExamCoverageAudit(
        exam_code=exam_code,
        mapped_chapters_count=mapped,
        included_chapters_count=included_count,
        audited_chapters_count=audited_count,
        chapters_with_questions_count=with_questions,
        published_question_count=total_published_questions,
        verified_pyq_count=total_verified_pyqs,
        unverified_pyq_excluded_count=unverified_pyq_excluded_count,
        audited_coverage_pct=audited_pct,
        question_coverage_pct=question_pct,
        coverage_status=status,
        coverage_disclaimer=disclaimer,
    )


# ---------------------------------------------------------------------------
# 4. Exam Analytics Engine (Accuracy, Speed, Weaknesses, Recommendations)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExamAnswerObservation:
    attempt_id: str
    subject_id: str | None
    subject_name: str
    chapter_id: str | None
    chapter_title: str
    concept_id: str | None
    concept_title: str | None
    is_correct: bool
    attempted: bool
    marks_awarded: float
    max_marks: float
    time_spent_seconds: int


@dataclass(frozen=True, slots=True)
class ExamAttemptHistoryInput:
    attempt_id: str
    title: str
    category: str
    submitted_at_iso: str
    raw_score: float
    max_score: float
    accuracy_pct: float
    avg_seconds_per_question: float


@dataclass(frozen=True, slots=True)
class WeaknessBucket:
    entity_id: str | None
    name: str
    attempts: int
    correct: int
    accuracy_pct: float
    avg_seconds: float
    severity: str  # critical | needs_focus | developing


@dataclass(frozen=True, slots=True)
class ExamAnalyticsSummary:
    exam_code: str
    total_attempts: int
    total_questions_answered: int
    overall_accuracy_pct: float
    average_seconds_per_question: float
    target_seconds_per_question: int
    pacing_status: str
    weak_subjects: tuple[WeaknessBucket, ...]
    weak_chapters: tuple[WeaknessBucket, ...]
    weak_concepts: tuple[WeaknessBucket, ...]
    performance_history: tuple[ExamAttemptHistoryInput, ...]
    improvement_recommendations: tuple[str, ...]


def _aggregate_weakness(
    rows: list[tuple[str | None, str, bool, int]],
    *,
    accuracy_threshold: float = 70.0,
    limit: int = 6,
) -> tuple[WeaknessBucket, ...]:
    grouped: dict[tuple[str | None, str], list[tuple[bool, int]]] = {}
    for eid, name, is_correct, secs in rows:
        if not name:
            continue
        grouped.setdefault((eid, name), []).append((is_correct, max(0, secs)))

    buckets: list[WeaknessBucket] = []
    for (eid, name), items in grouped.items():
        total = len(items)
        correct = sum(1 for ok, _ in items if ok)
        acc = round((correct / total) * 100.0, 1) if total else 0.0
        avg_s = round(sum(s for _, s in items) / total, 1) if total else 0.0
        if acc < accuracy_threshold:
            severity = "critical" if acc < 45.0 else ("needs_focus" if acc < 60.0 else "developing")
            buckets.append(
                WeaknessBucket(
                    entity_id=eid,
                    name=name,
                    attempts=total,
                    correct=correct,
                    accuracy_pct=acc,
                    avg_seconds=avg_s,
                    severity=severity,
                )
            )
    buckets.sort(key=lambda b: (b.accuracy_pct, -b.attempts, b.name))
    return tuple(buckets[:limit])


def compute_exam_analytics(
    *,
    exam_code: str,
    observations: list[ExamAnswerObservation],
    history: list[ExamAttemptHistoryInput],
) -> ExamAnalyticsSummary:
    """Compute accuracy, speed, pacing diagnosis, weak areas, and improvement advice."""
    target_sec = EXAM_TARGET_SECONDS_PER_QUESTION.get(exam_code, 120)
    answered = [obs for obs in observations if obs.attempted]
    total_answered = len(answered)
    correct_count = sum(1 for obs in answered if obs.is_correct)
    accuracy_pct = round((correct_count / total_answered) * 100.0, 1) if total_answered > 0 else 0.0

    timed = [obs.time_spent_seconds for obs in answered if obs.time_spent_seconds > 0]
    avg_sec = round(sum(timed) / len(timed), 1) if timed else 0.0

    if total_answered == 0:
        pacing = "insufficient_data"
    elif avg_sec <= target_sec and accuracy_pct >= 75.0:
        pacing = "fast_accurate"
    elif avg_sec <= target_sec * 1.15 and accuracy_pct >= 65.0:
        pacing = "on_pace_accurate"
    elif avg_sec > 0 and avg_sec < target_sec * 0.7 and accuracy_pct < 60.0:
        pacing = "rushing_errors"
    elif avg_sec > target_sec * 1.15 and accuracy_pct >= 70.0:
        pacing = "slow_accurate"
    else:
        pacing = "slow_needs_drill"

    weak_subjects = _aggregate_weakness(
        [(o.subject_id, o.subject_name, o.is_correct, o.time_spent_seconds) for o in answered]
    )
    weak_chapters = _aggregate_weakness(
        [(o.chapter_id, o.chapter_title, o.is_correct, o.time_spent_seconds) for o in answered]
    )
    weak_concepts = _aggregate_weakness(
        [
            (o.concept_id, o.concept_title or "", o.is_correct, o.time_spent_seconds)
            for o in answered
            if o.concept_title
        ]
    )

    recs: list[str] = []
    if total_answered == 0:
        recs.append(
            f"Complete at least one {exam_code.replace('_', ' ')} chapter drill or timed mock "
            "to unlock personalized speed, accuracy, and weak-concept diagnostics."
        )
    else:
        if pacing == "rushing_errors":
            recs.append(
                f"You average {avg_sec:.0f}s/question (target {target_sec}s) with {accuracy_pct:.1f}% accuracy. "
                "Slow down to verify signs, units, and negative-marking risk before locking answers."
            )
        elif pacing in {"slow_accurate", "slow_needs_drill"}:
            recs.append(
                f"Your average pace ({avg_sec:.0f}s/question) exceeds the {target_sec}s benchmark. "
                "Practice 15-minute timed chapter sprints and review high-yield formula sheets."
            )
        elif pacing in {"fast_accurate", "on_pace_accurate"}:
            recs.append(
                f"Strong pacing at {avg_sec:.0f}s/question with {accuracy_pct:.1f}% accuracy. "
                "Increase exposure to hard difficulty and verified multi-concept PYQs."
            )

        if weak_chapters:
            top_ch = weak_chapters[0]
            recs.append(
                f"Prioritize chapter '{top_ch.name}' ({top_ch.accuracy_pct:.1f}% accuracy across "
                f"{top_ch.attempts} attempts) with step-by-step solutions and formula revision."
            )
        if weak_concepts:
            top_co = weak_concepts[0]
            recs.append(
                f"Targeted concept remediation needed for '{top_co.name}' "
                f"({top_co.accuracy_pct:.1f}% accuracy)."
            )
        if exam_code in {"JEE_MAIN", "JEE_ADVANCED", "NEET"} and accuracy_pct < 65.0:
            recs.append(
                "Negative marking is eroding raw score: skip uncertain items rather than guessing "
                "unless at least two options are eliminated."
            )

    sorted_history = tuple(sorted(history, key=lambda h: h.submitted_at_iso))
    return ExamAnalyticsSummary(
        exam_code=exam_code,
        total_attempts=len(history),
        total_questions_answered=total_answered,
        overall_accuracy_pct=accuracy_pct,
        average_seconds_per_question=avg_sec,
        target_seconds_per_question=target_sec,
        pacing_status=pacing,
        weak_subjects=weak_subjects,
        weak_chapters=weak_chapters,
        weak_concepts=weak_concepts,
        performance_history=sorted_history,
        improvement_recommendations=tuple(recs),
    )


# ---------------------------------------------------------------------------
# 5. Exam Revision Plan Generator
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RevisionChapterCandidate:
    chapter_id: str
    chapter_title: str
    subject_name: str
    weightage_pct: float
    priority_tier: str
    student_accuracy_pct: float | None
    verified_pyq_count: int


def generate_exam_revision_schedule(
    *,
    exam_code: str,
    start_date: date,
    target_exam_date: date,
    daily_minutes: int,
    chapters: list[RevisionChapterCandidate],
    max_days: int = 14,
) -> list[dict[str, Any]]:
    """Build a deterministic day-by-day revision plan balancing weak + high-yield chapters."""
    days_available = max(1, min(max_days, (target_exam_date - start_date).days + 1))

    # Score chapters by urgency: lower accuracy + higher weightage + higher priority tier
    def _urgency(ch: RevisionChapterCandidate) -> float:
        acc_gap = 100.0 - (ch.student_accuracy_pct if ch.student_accuracy_pct is not None else 55.0)
        tier_bonus = PRIORITY_RANK.get(ch.priority_tier, 1) * 15.0
        return acc_gap * 1.2 + ch.weightage_pct * 2.5 + tier_bonus

    ranked = sorted(chapters, key=_urgency, reverse=True)
    schedule: list[dict[str, Any]] = []

    for day_idx in range(days_available):
        day_date = start_date + timedelta(days=day_idx)
        day_num = day_idx + 1
        blocks: list[dict[str, Any]] = []

        is_mock_day = (day_num % 5 == 0) or (day_idx == days_available - 1 and days_available >= 3)
        if is_mock_day:
            mock_mins = max(30, int(daily_minutes * 0.65))
            review_mins = max(15, daily_minutes - mock_mins)
            blocks.append(
                {
                    "activity": "timed_mock",
                    "title": f"{exam_code.replace('_', ' ')} Timed Full/Section Mock",
                    "minutes": mock_mins,
                    "chapter_id": None,
                    "focus_note": "Simulate real exam timing and negative-marking discipline.",
                }
            )
            blocks.append(
                {
                    "activity": "error_log_review",
                    "title": "Post-Mock Detailed Solution & Mistake Analysis",
                    "minutes": review_mins,
                    "chapter_id": None,
                    "focus_note": "Review every incorrect and skipped question step-by-step.",
                }
            )
        elif ranked:
            primary = ranked[day_idx % len(ranked)]
            secondary = ranked[(day_idx + 1) % len(ranked)] if len(ranked) > 1 else primary
            formula_mins = max(15, int(daily_minutes * 0.25))
            drill_mins = max(20, int(daily_minutes * 0.45))
            pyq_mins = max(15, daily_minutes - formula_mins - drill_mins)

            blocks.append(
                {
                    "activity": "formula_revision",
                    "title": f"Formula & Key Concept Sheet: {primary.chapter_title}",
                    "minutes": formula_mins,
                    "chapter_id": primary.chapter_id,
                    "focus_note": f"{primary.subject_name} · {primary.priority_tier.replace('_', ' ')} ({primary.weightage_pct:.1f}% weightage)",
                }
            )
            blocks.append(
                {
                    "activity": "chapter_practice",
                    "title": f"Focused Practice Drill: {primary.chapter_title}",
                    "minutes": drill_mins,
                    "chapter_id": primary.chapter_id,
                    "focus_note": (
                        f"Current accuracy {primary.student_accuracy_pct:.1f}% — focus on accuracy before speed."
                        if primary.student_accuracy_pct is not None
                        else "Baseline accuracy check with step-by-step hints."
                    ),
                }
            )
            pyq_label = (
                f"Verified PYQ Set ({secondary.verified_pyq_count} verified): {secondary.chapter_title}"
                if secondary.verified_pyq_count > 0
                else f"Topic Reinforcement: {secondary.chapter_title}"
            )
            blocks.append(
                {
                    "activity": "pyq_drill" if secondary.verified_pyq_count > 0 else "topic_practice",
                    "title": pyq_label,
                    "minutes": pyq_mins,
                    "chapter_id": secondary.chapter_id,
                    "focus_note": f"Spaced reinforcement across {secondary.subject_name}.",
                }
            )
        else:
            blocks.append(
                {
                    "activity": "baseline_diagnostic",
                    "title": f"{exam_code.replace('_', ' ')} Baseline Practice & Formula Review",
                    "minutes": daily_minutes,
                    "chapter_id": None,
                    "focus_note": "Map syllabus chapters to generate chapter-specific drills.",
                }
            )

        schedule.append(
            {
                "day_number": day_num,
                "date": day_date.isoformat(),
                "total_minutes": sum(int(b["minutes"]) for b in blocks),
                "blocks": blocks,
            }
        )

    return schedule
