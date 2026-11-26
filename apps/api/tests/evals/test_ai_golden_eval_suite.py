"""Automated CI Regression Gate running Phase 3 Golden Evaluation Dataset."""

from __future__ import annotations

import json

from src.modules.ai.evals import DEFAULT_DATASET_PATH, evaluate_golden_case


def test_phase3_golden_eval_dataset_passes_all_gates() -> None:
    """Every case in tests/evals/datasets/phase3_golden_eval_v1.jsonl MUST pass (0% regression)."""
    lines = [
        line.strip()
        for line in DEFAULT_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 10
    failures: list[str] = []
    for raw in lines:
        case = json.loads(raw)
        ok, _scores, err = evaluate_golden_case(case)
        if not ok:
            failures.append(f"{case['case_id']}: {err}")
    assert not failures, f"AI golden eval regressions detected: {failures}"
