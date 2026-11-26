"""Unit tests for Phase 5 Multi-Signal Concept Mastery, Recommendations & SM-2+ Scheduling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from src.modules.learning.adaptive_engine import (
    ConceptEvidenceSample,
    build_adaptive_recommendations,
    compute_concept_mastery,
)
from src.modules.revision.scheduler import compute_due_priority_score, schedule_sm2_plus


def test_mastery_rewards_difficulty_and_independent_solving_over_hints() -> None:
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    cid = uuid4()

    # Student A: solves independently across hard & medium questions
    indep_samples = [
        ConceptEvidenceSample(
            cid, True, "hard", "numerical", 0, "practice", now - timedelta(days=3)
        ),
        ConceptEvidenceSample(
            cid, True, "medium", "mcq_single", 0, "assessment", now - timedelta(days=1)
        ),
        ConceptEvidenceSample(cid, True, "hard", "numerical", 0, "practice", now),
    ]
    # Student B: same hit count on easy questions using 2 hints each
    hinted_samples = [
        ConceptEvidenceSample(
            cid, True, "easy", "mcq_single", 2, "practice", now - timedelta(days=3)
        ),
        ConceptEvidenceSample(
            cid, True, "easy", "mcq_single", 2, "practice", now - timedelta(days=1)
        ),
        ConceptEvidenceSample(cid, True, "easy", "mcq_single", 2, "practice", now),
    ]

    m_indep = compute_concept_mastery(concept_id=cid, samples=indep_samples, now=now)
    m_hinted = compute_concept_mastery(concept_id=cid, samples=hinted_samples, now=now)

    assert m_indep.independent_solve_ratio == 1.0
    assert m_hinted.independent_solve_ratio == 0.0
    assert m_indep.mastery_score > m_hinted.mastery_score + 20.0
    assert m_indep.transfer_score > m_hinted.transfer_score


def test_mastery_retention_decay_improvement_slope_and_misconception_penalty() -> None:
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    cid = uuid4()

    recent_improving = [
        ConceptEvidenceSample(
            cid, False, "medium", "mcq_single", 0, "practice", now - timedelta(days=5)
        ),
        ConceptEvidenceSample(
            cid, False, "medium", "mcq_single", 0, "practice", now - timedelta(days=4)
        ),
        ConceptEvidenceSample(
            cid, True, "medium", "mcq_single", 0, "practice", now - timedelta(days=2)
        ),
        ConceptEvidenceSample(cid, True, "hard", "numerical", 0, "assessment", now),
    ]
    stale_declining = [
        ConceptEvidenceSample(
            cid, True, "medium", "mcq_single", 0, "practice", now - timedelta(days=60)
        ),
        ConceptEvidenceSample(
            cid, True, "medium", "mcq_single", 0, "practice", now - timedelta(days=59)
        ),
        ConceptEvidenceSample(
            cid, False, "medium", "mcq_single", 1, "practice", now - timedelta(days=1)
        ),
        ConceptEvidenceSample(cid, False, "hard", "numerical", 1, "assessment", now),
    ]

    m_up = compute_concept_mastery(concept_id=cid, samples=recent_improving, now=now)
    m_down = compute_concept_mastery(concept_id=cid, samples=stale_declining, now=now)
    m_with_misc = compute_concept_mastery(
        concept_id=cid,
        samples=recent_improving,
        unresolved_severities=["high"],
        now=now,
    )

    assert m_up.improvement_slope > 0.5
    assert m_down.improvement_slope < 0.5
    assert m_up.retention_score > m_down.retention_score
    assert m_up.mastery_score > m_down.mastery_score
    assert m_with_misc.active_misconception_penalty == 14.0
    assert m_with_misc.mastery_score < m_up.mastery_score


def test_prerequisite_remediation_and_advancement_recommendations() -> None:
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    prereq_id = uuid4()
    target_id = uuid4()
    mastered_id = uuid4()
    downstream_id = uuid4()

    m_prereq = compute_concept_mastery(
        concept_id=prereq_id,
        samples=[ConceptEvidenceSample(prereq_id, False, "easy", "mcq_single", 1, "practice", now)],
        now=now,
    )
    m_target = compute_concept_mastery(
        concept_id=target_id,
        samples=[
            ConceptEvidenceSample(target_id, False, "medium", "numerical", 0, "practice", now)
        ],
        now=now,
    )
    m_mastered = compute_concept_mastery(
        concept_id=mastered_id,
        samples=[
            ConceptEvidenceSample(
                mastered_id, True, "hard", "mcq_single", 0, "practice", now - timedelta(days=4)
            ),
            ConceptEvidenceSample(
                mastered_id, True, "hard", "numerical", 0, "assessment", now - timedelta(days=2)
            ),
            ConceptEvidenceSample(
                mastered_id, True, "hard", "numerical", 0, "practice", now - timedelta(days=1)
            ),
            ConceptEvidenceSample(mastered_id, True, "hard", "mcq_single", 0, "assessment", now),
            ConceptEvidenceSample(mastered_id, True, "hard", "numerical", 0, "practice", now),
        ],
        now=now,
    )
    assert m_mastered.band == "mastered"

    recs = build_adaptive_recommendations(
        mastery_by_concept={
            prereq_id: m_prereq,
            target_id: m_target,
            mastered_id: m_mastered,
        },
        prerequisites_of={target_id: (prereq_id,)},
        dependents_of={mastered_id: (downstream_id,)},
        unresolved_misconceptions_by_concept={target_id: 1},
        concept_titles={
            prereq_id: "Algebra Basics",
            target_id: "Quadratic Formula",
            mastered_id: "Linear Equations",
            downstream_id: "Systems of Equations",
        },
    )
    types_in_order = [(r.concept_id, r.item_type) for r in recs]
    assert types_in_order[0] == (prereq_id, "remediate_prerequisite")
    assert (target_id, "remediate_concept") in types_in_order
    assert (downstream_id, "advance") in types_in_order


def test_sm2_plus_scheduling_and_priority_queue() -> None:
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)

    # First two perfect reviews: 1d -> 6d -> modulated by concept mastery
    s1 = schedule_sm2_plus(
        quality=5,
        previous_repetitions=0,
        previous_interval_days=0,
        previous_ease=2.5,
        concept_mastery_score=50.0,
        now=now,
    )
    assert s1.interval_days == 1
    assert s1.repetitions == 1

    s2 = schedule_sm2_plus(
        quality=5,
        previous_repetitions=s1.repetitions,
        previous_interval_days=s1.interval_days,
        previous_ease=s1.ease_factor,
        concept_mastery_score=50.0,
        now=now,
    )
    assert s2.interval_days == 6

    s3_weak = schedule_sm2_plus(
        quality=4,
        previous_repetitions=s2.repetitions,
        previous_interval_days=s2.interval_days,
        previous_ease=s2.ease_factor,
        concept_mastery_score=45.0,
        now=now,
    )
    s3_strong = schedule_sm2_plus(
        quality=4,
        previous_repetitions=s2.repetitions,
        previous_interval_days=s2.interval_days,
        previous_ease=s2.ease_factor,
        concept_mastery_score=90.0,
        now=now,
    )
    assert s3_weak.interval_days < s3_strong.interval_days

    # Lapse quality=2 resets reps=0 and interval=1
    lapse = schedule_sm2_plus(
        quality=2,
        previous_repetitions=4,
        previous_interval_days=20,
        previous_ease=2.5,
        now=now,
    )
    assert lapse.repetitions == 0
    assert lapse.interval_days == 1
    assert lapse.lapse_delta == 1

    with pytest.raises(ValueError):
        schedule_sm2_plus(
            quality=7, previous_repetitions=0, previous_interval_days=0, previous_ease=2.5
        )

    p_missed_weak = compute_due_priority_score(
        due_at=now - timedelta(days=2),
        card_type="missed_question",
        lapse_count=2,
        concept_mastery_score=35.0,
        now=now,
    )
    p_concept_strong = compute_due_priority_score(
        due_at=now,
        card_type="concept",
        lapse_count=0,
        concept_mastery_score=85.0,
        now=now,
    )
    assert p_missed_weak > p_concept_strong
