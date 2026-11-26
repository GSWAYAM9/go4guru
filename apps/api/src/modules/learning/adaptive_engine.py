"""Transparent, Configurable Multi-Signal Concept Mastery & Adaptive Recommendation Engine."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

MasteryBand = Literal["novice", "developing", "proficient", "mastered"]


@dataclass(frozen=True, slots=True)
class AdaptiveMasteryConfig:
    """Explicit pedagogical weights & thresholds documented in PHASE_5_ALGORITHM_AND_LIMITATIONS."""

    difficulty_weights: dict[str, float] = field(
        default_factory=lambda: {
            "easy": 0.80,
            "medium": 1.00,
            "hard": 1.25,
            "olympiad": 1.40,
            "advanced": 1.40,
        }
    )
    hint_penalty_per_hint: float = 0.25
    min_assisted_credit: float = 0.25
    retention_half_life_days: float = 21.0
    spacing_bonus_per_day: float = 0.05
    max_spacing_bonus: float = 0.15
    confidence_full_attempts: float = 5.0
    confidence_base_factor: float = 0.55
    weight_accuracy: float = 0.45
    weight_retention: float = 0.20
    weight_transfer: float = 0.15
    weight_improvement: float = 0.10
    weight_independence: float = 0.10
    weak_mastery_threshold: float = 60.0
    advancement_mastery_threshold: float = 80.0
    advancement_min_independence: float = 0.65
    advancement_min_attempts: int = 3
    misconception_penalties: dict[str, float] = field(
        default_factory=lambda: {"low": 4.0, "medium": 8.0, "high": 14.0}
    )
    max_misconception_penalty: float = 28.0


DEFAULT_MASTERY_CONFIG = AdaptiveMasteryConfig()


@dataclass(frozen=True, slots=True)
class ConceptEvidenceSample:
    """Normalized question attempt signal mapped to one concept."""

    concept_id: UUID
    is_correct: bool
    difficulty: str
    question_type: str
    hints_used_count: int
    source_context: str  # "practice" | "assessment"
    attempted_at: datetime


@dataclass(frozen=True, slots=True)
class ConceptMasteryComputation:
    concept_id: UUID
    mastery_score: float
    confidence: float
    retention_score: float
    independent_solve_ratio: float
    transfer_score: float
    improvement_slope: float
    difficulty_weighted_accuracy: float
    band: MasteryBand
    attempts_count: int
    correct_count: int
    independent_correct_count: int
    assisted_correct_count: int
    active_misconception_penalty: float
    last_practiced_at: datetime | None
    next_review_due_at: datetime | None
    breakdown: dict[str, float | int | str]


def classify_mastery_band(
    mastery_score: float,
    *,
    confidence: float,
    independent_ratio: float,
    config: AdaptiveMasteryConfig = DEFAULT_MASTERY_CONFIG,
) -> MasteryBand:
    if (
        mastery_score >= config.advancement_mastery_threshold
        and confidence >= 0.60
        and independent_ratio >= config.advancement_min_independence
    ):
        return "mastered"
    if mastery_score >= config.weak_mastery_threshold:
        return "proficient"
    if mastery_score >= 40.0:
        return "developing"
    return "novice"


def compute_concept_mastery(
    *,
    concept_id: UUID,
    samples: list[ConceptEvidenceSample],
    unresolved_severities: list[str] | None = None,
    now: datetime | None = None,
    config: AdaptiveMasteryConfig = DEFAULT_MASTERY_CONFIG,
) -> ConceptMasteryComputation:
    """Compute multi-signal mastery from attempt history (time spent never inflates score)."""
    ref_now = now or datetime.now(UTC)
    if not samples:
        return ConceptMasteryComputation(
            concept_id=concept_id,
            mastery_score=0.0,
            confidence=0.0,
            retention_score=0.0,
            independent_solve_ratio=0.0,
            transfer_score=0.0,
            improvement_slope=0.5,
            difficulty_weighted_accuracy=0.0,
            band="novice",
            attempts_count=0,
            correct_count=0,
            independent_correct_count=0,
            assisted_correct_count=0,
            active_misconception_penalty=0.0,
            last_practiced_at=None,
            next_review_due_at=ref_now,
            breakdown={
                "weighted_accuracy": 0.0,
                "retention_score": 0.0,
                "transfer_score": 0.0,
                "improvement_slope": 0.5,
                "independent_solve_ratio": 0.0,
                "confidence": 0.0,
                "misconception_penalty": 0.0,
                "formula_note": "No attempts recorded yet.",
            },
        )

    ordered = sorted(samples, key=lambda s: s.attempted_at)
    n = len(ordered)

    weighted_num = 0.0
    weighted_den = 0.0
    correct_count = 0
    independent_correct = 0
    assisted_correct = 0
    correct_qtypes: set[str] = set()
    correct_contexts: set[str] = set()
    correct_days: set[str] = set()
    last_success_ts: datetime | None = None
    attempt_credits: list[float] = []

    for item in ordered:
        diff_w = config.difficulty_weights.get(item.difficulty.lower(), 1.0)
        weighted_den += diff_w
        if item.is_correct:
            correct_count += 1
            if item.hints_used_count <= 0:
                credit = 1.0
                independent_correct += 1
                last_success_ts = item.attempted_at
            else:
                credit = max(
                    config.min_assisted_credit,
                    1.0 - config.hint_penalty_per_hint * item.hints_used_count,
                )
                assisted_correct += 1
                if last_success_ts is None:
                    last_success_ts = item.attempted_at
            weighted_num += diff_w * credit
            attempt_credits.append(credit)
            correct_qtypes.add(item.question_type)
            correct_contexts.add(item.source_context)
            correct_days.add(item.attempted_at.date().isoformat())
        else:
            attempt_credits.append(0.0)

    s_acc = (weighted_num / weighted_den) if weighted_den > 0 else 0.0
    indep_ratio = (independent_correct / correct_count) if correct_count > 0 else 0.0

    # Retention decay + multi-day spacing bonus
    if last_success_ts is None:
        s_ret = 0.15 if correct_count > 0 else 0.0
    else:
        ts_utc = last_success_ts if last_success_ts.tzinfo else last_success_ts.replace(tzinfo=UTC)
        age_days = max(0.0, (ref_now - ts_utc).total_seconds() / 86400.0)
        lam = math.log(2.0) / max(1.0, config.retention_half_life_days)
        recency_decay = math.exp(-lam * age_days)
        spacing_bonus = min(
            config.max_spacing_bonus,
            max(0, len(correct_days) - 1) * config.spacing_bonus_per_day,
        )
        s_ret = min(1.0, 0.85 * recency_decay + spacing_bonus)

    # Transfer across formats and practice vs assessment contexts
    if correct_count == 0:
        s_xfer = 0.0
    else:
        type_factor = min(1.0, len(correct_qtypes) / 2.0)
        context_factor = 1.0 if len(correct_contexts) >= 2 else 0.65
        s_xfer = 0.5 * type_factor + 0.5 * context_factor

    # Improvement trend slope across chronological halves
    if n < 2:
        s_imp = 0.5
        slope_delta = 0.0
    else:
        mid = n // 2
        prior_avg = sum(attempt_credits[:mid]) / max(1, mid)
        recent_avg = sum(attempt_credits[mid:]) / max(1, n - mid)
        slope_delta = recent_avg - prior_avg
        s_imp = max(0.0, min(1.0, 0.5 + 0.5 * slope_delta))

    confidence = min(1.0, n / max(1.0, config.confidence_full_attempts))
    raw_composite = 100.0 * (
        config.weight_accuracy * s_acc
        + config.weight_retention * s_ret
        + config.weight_transfer * s_xfer
        + config.weight_improvement * s_imp
        + config.weight_independence * indep_ratio
    )

    penalty = sum(
        config.misconception_penalties.get(sev.lower(), 8.0)
        for sev in (unresolved_severities or [])
    )
    penalty = min(config.max_misconception_penalty, penalty)

    damped = raw_composite * (
        config.confidence_base_factor + (1.0 - config.confidence_base_factor) * confidence
    )
    mastery_score = round(max(0.0, min(100.0, damped - penalty)), 2)

    band = classify_mastery_band(
        mastery_score,
        confidence=confidence,
        independent_ratio=indep_ratio,
        config=config,
    )

    last_practiced = ordered[-1].attempted_at
    review_interval_days = (
        1 if mastery_score < 40 else 3 if mastery_score < 60 else 7 if mastery_score < 80 else 14
    )
    next_due = (last_practiced if last_practiced.tzinfo else last_practiced.replace(tzinfo=UTC)) + (
        timedelta(days=review_interval_days)
    )

    return ConceptMasteryComputation(
        concept_id=concept_id,
        mastery_score=mastery_score,
        confidence=round(confidence, 2),
        retention_score=round(s_ret, 2),
        independent_solve_ratio=round(indep_ratio, 2),
        transfer_score=round(s_xfer, 2),
        improvement_slope=round(s_imp, 2),
        difficulty_weighted_accuracy=round(s_acc, 2),
        band=band,
        attempts_count=n,
        correct_count=correct_count,
        independent_correct_count=independent_correct,
        assisted_correct_count=assisted_correct,
        active_misconception_penalty=round(penalty, 2),
        last_practiced_at=last_practiced,
        next_review_due_at=next_due,
        breakdown={
            "weighted_accuracy": round(s_acc, 3),
            "retention_score": round(s_ret, 3),
            "transfer_score": round(s_xfer, 3),
            "improvement_slope": round(s_imp, 3),
            "slope_delta": round(slope_delta, 3),
            "independent_solve_ratio": round(indep_ratio, 3),
            "confidence": round(confidence, 3),
            "misconception_penalty": round(penalty, 2),
            "distinct_correct_days": len(correct_days),
            "distinct_correct_types": len(correct_qtypes),
        },
    )


@dataclass(frozen=True, slots=True)
class AdaptiveRecommendation:
    concept_id: UUID
    item_type: str  # remediate_prerequisite|remediate_concept|review_missed|advance
    priority_score: float
    reason: str
    action_route: str


def build_adaptive_recommendations(
    *,
    mastery_by_concept: dict[UUID, ConceptMasteryComputation],
    prerequisites_of: dict[UUID, tuple[UUID, ...]],
    dependents_of: dict[UUID, tuple[UUID, ...]],
    unresolved_misconceptions_by_concept: dict[UUID, int],
    concept_titles: dict[UUID, str],
    config: AdaptiveMasteryConfig = DEFAULT_MASTERY_CONFIG,
) -> list[AdaptiveRecommendation]:
    """Generate deterministic, prerequisite-aware remediation & advancement actions."""
    recs: list[AdaptiveRecommendation] = []
    seen_pairs: set[tuple[UUID, str]] = set()

    def _add(rec: AdaptiveRecommendation) -> None:
        key = (rec.concept_id, rec.item_type)
        if key not in seen_pairs:
            seen_pairs.add(key)
            recs.append(rec)

    # 1. Inspect weak / decaying / misconception-heavy concepts & check prerequisites first
    for cid, m in mastery_by_concept.items():
        title = concept_titles.get(cid, "Selected Concept")
        misc_cnt = unresolved_misconceptions_by_concept.get(cid, 0)
        is_weak = (
            m.mastery_score < config.weak_mastery_threshold
            or misc_cnt > 0
            or m.retention_score < 0.65
        )
        if is_weak:
            # Traverse prerequisite concepts first
            for pid in prerequisites_of.get(cid, ()):
                pm = mastery_by_concept.get(pid)
                p_title = concept_titles.get(pid, "Prerequisite Concept")
                if pm is None or pm.mastery_score < config.weak_mastery_threshold:
                    score = 125.0 - (pm.mastery_score if pm else 20.0) * 0.2
                    _add(
                        AdaptiveRecommendation(
                            concept_id=pid,
                            item_type="remediate_prerequisite",
                            priority_score=round(score, 2),
                            reason=(
                                f"Strengthen prerequisite '{p_title}' before remediating '{title}'."
                            ),
                            action_route="/practice",
                        )
                    )

            priority = min(
                105.0,
                90.0
                - m.mastery_score * 0.5
                + misc_cnt * 12.0
                + (1.0 - m.independent_solve_ratio) * 10.0,
            )
            reason_parts = [f"Mastery {m.mastery_score:.1f}/100 ({m.band})"]
            if m.independent_solve_ratio < 0.6 and m.attempts_count > 0:
                reason_parts.append("high hint dependency detected")
            if misc_cnt > 0:
                reason_parts.append(f"{misc_cnt} active misconception(s)")
            if m.retention_score < 0.65 and m.attempts_count > 0:
                reason_parts.append("retention decay overdue for review")

            _add(
                AdaptiveRecommendation(
                    concept_id=cid,
                    item_type="remediate_concept",
                    priority_score=round(priority, 2),
                    reason=f"Remediate '{title}': {', '.join(reason_parts)}.",
                    action_route="/practice",
                )
            )
            if m.correct_count < m.attempts_count:
                _add(
                    AdaptiveRecommendation(
                        concept_id=cid,
                        item_type="review_missed",
                        priority_score=round(priority - 3.0, 2),
                        reason=f"Review missed-question flashcards for '{title}'.",
                        action_route="/revision",
                    )
                )

        # 2. Advancement logic for mastered concepts
        if m.band == "mastered":
            downstream = dependents_of.get(cid, ())
            unlocked = False
            for did in downstream:
                dm = mastery_by_concept.get(did)
                if dm is None or dm.mastery_score < config.advancement_mastery_threshold:
                    d_title = concept_titles.get(did, "Next Concept")
                    _add(
                        AdaptiveRecommendation(
                            concept_id=did,
                            item_type="advance",
                            priority_score=64.0,
                            reason=(
                                f"Mastered '{title}' ({m.mastery_score:.1f}/100, "
                                f"{int(m.independent_solve_ratio * 100)}% independent): "
                                f"advance to '{d_title}'."
                            ),
                            action_route="/practice",
                        )
                    )
                    unlocked = True
            if not unlocked:
                _add(
                    AdaptiveRecommendation(
                        concept_id=cid,
                        item_type="advance",
                        priority_score=52.0,
                        reason=(
                            f"Mastered '{title}' independently: challenge yourself with "
                            "hard/exam problems."
                        ),
                        action_route="/quizzes",
                    )
                )

    recs.sort(key=lambda r: r.priority_score, reverse=True)
    return recs
