"""Automated Golden Dataset AI Regression Evaluation Suite & Persistence (`F-021`)."""

from __future__ import annotations

import asyncio
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.modules.ai.models import AiEvalDataset, AiEvalResult, AiEvalRun
from src.modules.ai.pedagogy import build_pedagogical_plan, synthesize_grounded_fallback
from src.modules.ai.resolvers import classify_intent
from src.modules.ai.safety import evaluate_input_safety, scrub_pii_text
from src.modules.ai.schemas import (
    AiEvalRunResponse,
    AnonymizedStudentContext,
    CurriculumContext,
    TeachingMode,
)
from src.modules.ai.verifier import (
    verify_chemical_equation,
    verify_math_expression,
    verify_physics_units,
)

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "evals"
    / "datasets"
    / "phase3_golden_eval_v1.jsonl"
)


def evaluate_golden_case(case: dict[str, Any]) -> tuple[bool, dict[str, Any], str | None]:
    """Run deterministic correctness, anti-spoiler, and safety gates on one eval case."""
    cat = str(case.get("category", ""))

    if cat == "math_verification":
        res = verify_math_expression(str(case["prompt"]).replace("Solve", "").strip())
        passed = bool(res.verified == bool(case["expect_verified"]))
        exp_sub = case.get("expected_contains")
        if (
            passed
            and exp_sub
            and (not res.computed_value or str(exp_sub) not in res.computed_value)
        ):
            passed = False
        return (
            passed,
            {"verified": res.verified, "computed": res.computed_value},
            None if passed else f"Expected {exp_sub}, got {res.computed_value}",
        )

    if cat == "science_verification":
        if "equation" in case:
            res = verify_chemical_equation(str(case["equation"]))
        else:
            res = verify_physics_units(str(case["lhs_unit"]), str(case["rhs_unit"]))
        passed = bool(res.verified == bool(case["expect_verified"]))
        return (
            passed,
            {"verified": res.verified, "details": res.details},
            None if passed else f"Expected verified={case['expect_verified']}, got {res.verified}",
        )

    if cat == "pedagogy_anti_spoiler":
        prompt = str(case["prompt"])
        mode = cast(TeachingMode, str(case.get("mode", "socratic")))
        intent = classify_intent(prompt, requested_mode=mode)
        stu_ctx = AnonymizedStudentContext()
        curr_ctx = CurriculumContext()
        plan = build_pedagogical_plan(
            intent=intent,
            mode_override=mode,
            student_ctx=stu_ctx,
            curriculum_ctx=curr_ctx,
        )
        verif = verify_math_expression(prompt)
        out = synthesize_grounded_fallback(
            plan=plan,
            intent=intent,
            curriculum_ctx=curr_ctx,
            chunks=[],
            query=prompt,
            verif=verif,
            provider_errors=[],
        )
        spoiler_ok = plan.spoiler_guard == bool(case.get("expect_spoiler_guard", True))
        forbidden = case.get("forbidden_spoiler")
        if forbidden and str(forbidden) in out.answer_markdown:
            spoiler_ok = False
        return (
            spoiler_ok,
            {"spoiler_guard": plan.spoiler_guard, "mode": plan.mode},
            None if spoiler_ok else "Spoiler guard failed or leaked forbidden answer.",
        )

    if cat == "safety_redteam":
        prompt = str(case["prompt"])
        if case.get("expect_pii_scrubbed"):
            scrubbed = scrub_pii_text(prompt)
            passed = "test@example.com" not in scrubbed and "9876543210" not in scrubbed
            return (
                passed,
                {"pii_scrubbed": passed},
                None if passed else "PII remained after scrubbing.",
            )
        verdict = evaluate_input_safety(prompt, is_minor=True)
        expected_action = str(case["expect_safety_action"])
        passed = verdict.action == expected_action
        return (
            passed,
            {"action": verdict.action, "reason": verdict.reason_code},
            None if passed else f"Expected {expected_action}, got {verdict.action}",
        )

    return False, {}, f"Unknown evaluation category: {cat}"


async def run_golden_evaluation_suite(
    db: AsyncSession,
    caller: AuthenticatedUser | None = None,
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    provider: str = "grounded_fallback",
    model_id: str = "deterministic-v1",
    prompt_version: str = "v3.1.0",
) -> AiEvalRunResponse:
    """Load versioned JSONL golden dataset, execute all gates, and persist results to DB."""
    raw_bytes = await asyncio.to_thread(dataset_path.read_bytes)
    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    cases = [json.loads(line) for line in raw_bytes.decode("utf-8").splitlines() if line.strip()]

    ds_name = "phase3_golden_eval"
    ds_ver = "v1"
    dataset = await db.scalar(
        select(AiEvalDataset).where(AiEvalDataset.name == ds_name, AiEvalDataset.version == ds_ver)
    )
    if dataset is None:
        dataset = AiEvalDataset(
            name=ds_name,
            version=ds_ver,
            category="comprehensive_phase3",
            item_count=len(cases),
            dataset_sha256=sha256_hex,
        )
        db.add(dataset)
        await db.flush()

    results_rows: list[tuple[str, bool, dict[str, Any], str | None]] = []
    category_stats: dict[str, dict[str, int]] = {}
    for c in cases:
        cid = str(c["case_id"])
        cat = str(c.get("category", "unknown"))
        passed, scores, err = evaluate_golden_case(c)
        results_rows.append((cid, passed, scores, err))
        bucket = category_stats.setdefault(cat, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if passed:
            bucket["passed"] += 1

    total = len(results_rows)
    passed_cnt = sum(1 for _, ok, _, _ in results_rows if ok)
    pass_rate = round((passed_cnt / total) * 100.0, 2) if total else 0.0

    run = AiEvalRun(
        dataset_id=dataset.id,
        provider=provider,
        model_id=model_id,
        prompt_version=prompt_version,
        total_items=total,
        passed_items=passed_cnt,
        pass_rate_pct=Decimal(str(pass_rate)),
        metrics_jsonb={"by_category": category_stats, "dataset_sha256": sha256_hex},
        status="completed",
        triggered_by=caller.id if caller else None,
    )
    db.add(run)
    await db.flush()

    for cid, ok, scores, err in results_rows:
        db.add(
            AiEvalResult(
                eval_run_id=run.id,
                case_id=cid,
                passed=ok,
                scores_jsonb=scores,
                failure_reason=err,
            )
        )

    await db.commit()
    await db.refresh(run)
    return AiEvalRunResponse(
        id=run.id,
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        provider=run.provider,
        model_id=run.model_id,
        prompt_version=run.prompt_version,
        total_items=run.total_items,
        passed_items=run.passed_items,
        pass_rate_pct=float(run.pass_rate_pct),
        metrics=dict(run.metrics_jsonb),
        created_at=run.created_at,
    )


async def list_eval_runs(db: AsyncSession) -> list[AiEvalRunResponse]:
    rows = (
        await db.scalars(select(AiEvalRun).order_by(AiEvalRun.created_at.desc()).limit(25))
    ).all()
    if not rows:
        return []
    ds_map = {d.id: d for d in (await db.scalars(select(AiEvalDataset))).all()}
    out: list[AiEvalRunResponse] = []
    for r in rows:
        ds = ds_map.get(r.dataset_id)
        out.append(
            AiEvalRunResponse(
                id=r.id,
                dataset_name=ds.name if ds else "phase3_golden_eval",
                dataset_version=ds.version if ds else "v1",
                provider=r.provider,
                model_id=r.model_id,
                prompt_version=r.prompt_version,
                total_items=r.total_items,
                passed_items=r.passed_items,
                pass_rate_pct=float(r.pass_rate_pct),
                metrics=dict(r.metrics_jsonb),
                created_at=r.created_at,
            )
        )
    return out
