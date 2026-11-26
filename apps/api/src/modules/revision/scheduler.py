"""SM-2+ Configurable Spaced Repetition Scheduler & Due-Revision Prioritization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class SpacedRepetitionConfig:
    min_ease_factor: float = 1.30
    default_ease_factor: float = 2.50
    max_interval_days: int = 180
    first_success_days: int = 1
    second_success_days: int = 6
    weak_concept_threshold: float = 60.0
    strong_concept_threshold: float = 80.0
    weak_interval_multiplier: float = 0.85
    strong_interval_multiplier: float = 1.10


DEFAULT_SR_CONFIG = SpacedRepetitionConfig()


@dataclass(frozen=True, slots=True)
class SM2ScheduleOutcome:
    repetitions: int
    interval_days: int
    ease_factor: float
    lapse_delta: int
    due_at: datetime


def schedule_sm2_plus(
    *,
    quality: int,
    previous_repetitions: int,
    previous_interval_days: int,
    previous_ease: float,
    concept_mastery_score: float | None = None,
    now: datetime | None = None,
    config: SpacedRepetitionConfig = DEFAULT_SR_CONFIG,
) -> SM2ScheduleOutcome:
    """Compute next review schedule via SM-2+ modulated by concept mastery band."""
    if quality < 0 or quality > 5:
        raise ValueError("SM-2 quality rating must be between 0 and 5.")
    ref_now = now or datetime.now(UTC)

    ef_delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ease = round(max(config.min_ease_factor, previous_ease + ef_delta), 3)

    if quality < 3:
        new_reps = 0
        new_interval = 1
        lapse_delta = 1
    else:
        lapse_delta = 0
        new_reps = previous_repetitions + 1
        if previous_repetitions == 0:
            new_interval = config.first_success_days
        elif previous_repetitions == 1:
            new_interval = config.second_success_days
        else:
            mastery_mod = 1.0
            if concept_mastery_score is not None:
                if concept_mastery_score < config.weak_concept_threshold:
                    mastery_mod = config.weak_interval_multiplier
                elif concept_mastery_score >= config.strong_concept_threshold:
                    mastery_mod = config.strong_interval_multiplier
            raw_days = round(max(1, previous_interval_days) * new_ease * mastery_mod)
            new_interval = max(1, min(config.max_interval_days, raw_days))

    due_at = ref_now + timedelta(days=new_interval)
    return SM2ScheduleOutcome(
        repetitions=new_reps,
        interval_days=new_interval,
        ease_factor=new_ease,
        lapse_delta=lapse_delta,
        due_at=due_at,
    )


def compute_due_priority_score(
    *,
    due_at: datetime,
    card_type: str,
    lapse_count: int,
    concept_mastery_score: float | None,
    now: datetime | None = None,
) -> float:
    """Rank due cards so overdue, lapsed, weak-concept, and missed-question items appear first."""
    ref_now = now or datetime.now(UTC)
    due_utc = due_at if due_at.tzinfo else due_at.replace(tzinfo=UTC)
    overdue_hours = max(0.0, (ref_now - due_utc).total_seconds() / 3600.0)
    overdue_days = overdue_hours / 24.0
    mastery_val = 50.0 if concept_mastery_score is None else concept_mastery_score

    score = (
        overdue_days * 12.0
        + max(0.0, 100.0 - mastery_val) * 0.6
        + lapse_count * 10.0
        + (18.0 if card_type == "missed_question" else 0.0)
    )
    return round(score, 2)
