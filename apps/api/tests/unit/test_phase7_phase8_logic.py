"""Pure-stdlib unit tests for Phase 7 & Phase 8 core security, grading, quota, and tenant logic.

Runnable directly with `python3 -m unittest` OR `pytest` without requiring PG18/FastAPI.
"""

from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.billing.logic import evaluate_entitlement_quota, merge_plan_entitlements
from src.modules.identity.parent_logic import (
    generate_consent_verification_code,
    hash_consent_verification_code,
    sanitize_parent_privacy_settings,
    verify_consent_verification_code,
)
from src.modules.organization.logic import (
    is_resource_in_tenant,
    is_tenant_access_allowed,
    merge_tenant_config,
    normalize_tenant_slug,
    render_org_report_csv,
)
from src.modules.teacher.logic import (
    compute_ai_grading_draft,
    render_safe_csv_report,
    sanitize_csv_cell,
    validate_teacher_override_score,
)


class TestPhase7ParentConsentAndPrivacy(unittest.TestCase):
    def test_consent_code_hashing_and_verification(self) -> None:
        code = generate_consent_verification_code()
        self.assertEqual(len(code), 8)
        salt = f"{uuid4()}:{uuid4()}"
        digest = hash_consent_verification_code(code, salt=salt)
        self.assertTrue(verify_consent_verification_code(code.lower(), salt=salt, expected_hash=digest))
        self.assertFalse(verify_consent_verification_code("WRONGCOD", salt=salt, expected_hash=digest))
        self.assertFalse(verify_consent_verification_code(code, salt="other-salt", expected_hash=digest))

    def test_raw_ai_transcripts_hard_locked_off(self) -> None:
        # Even if client explicitly requests allow_raw_ai_transcripts=True, policy MUST force False.
        sanitized = sanitize_parent_privacy_settings(
            {"allow_raw_ai_transcripts": True, "share_weak_topics": False}
        )
        self.assertFalse(sanitized["allow_raw_ai_transcripts"])
        self.assertFalse(sanitized["share_weak_topics"])
        self.assertTrue(sanitized["share_learning_summary"])


class TestPhase7TeacherGradingAndCsv(unittest.TestCase):
    def test_ai_grading_draft_and_teacher_override_bounds(self) -> None:
        empty_draft = compute_ai_grading_draft(
            response_text="   ",
            instructions="Solve quadratic equation",
            max_marks=20.0,
        )
        self.assertEqual(empty_draft.suggested_score, 0.0)
        self.assertEqual(empty_draft.rubric_band, "missing")

        detailed = compute_ai_grading_draft(
            response_text=(
                "Step 1: Using quadratic formula x = (-b +- sqrt(b^2 - 4ac)) / 2a. "
                "Step 2: Substitute a = 1, b = -5, c = 6 therefore discriminant = 25 - 24 = 1. "
                "Hence roots are x = 3 and x = 2."
            ),
            instructions="Solve quadratic equation using discriminant formula and show steps.",
            max_marks=20.0,
        )
        self.assertGreater(detailed.suggested_score, 10.0)
        self.assertLessEqual(detailed.suggested_score, 20.0)

        self.assertEqual(validate_teacher_override_score(score=18.5, max_marks=20.0), 18.5)
        with self.assertRaises(ValueError):
            validate_teacher_override_score(score=21.0, max_marks=20.0)
        with self.assertRaises(ValueError):
            validate_teacher_override_score(score=-1.0, max_marks=20.0)

    def test_csv_formula_injection_neutralized(self) -> None:
        self.assertEqual(sanitize_csv_cell("=HYPERLINK(\"http://evil\")"), "'=HYPERLINK(\"http://evil\")")
        self.assertEqual(sanitize_csv_cell("+cmd|' /C calc'!A0"), "'+cmd|' /C calc'!A0")
        self.assertEqual(sanitize_csv_cell("Normal Student"), "Normal Student")
        csv_text = render_safe_csv_report(
            ["Student", "Score"],
            [["=1+1", 19.5], ["@SUM(A1:A2)", 15.0]],
        )
        self.assertIn("'=1+1,19.5", csv_text)
        self.assertIn("'@SUM(A1:A2),15.0", csv_text)


class TestPhase8MultiTenantAndEntitlements(unittest.TestCase):
    def test_cross_tenant_isolation_policy(self) -> None:
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Tenant A admin may access Tenant A
        self.assertTrue(
            is_tenant_access_allowed(
                caller_roles=("school_admin",),
                caller_tenant_id=tenant_a,
                target_tenant_id=tenant_a,
            )
        )
        # Tenant A admin MUST be blocked from Tenant B
        self.assertFalse(
            is_tenant_access_allowed(
                caller_roles=("school_admin",),
                caller_tenant_id=tenant_a,
                target_tenant_id=tenant_b,
                active_membership_tenant_ids={tenant_a},
            )
        )
        # Caller with active membership in Tenant B is allowed for Tenant B, denied for Tenant A
        self.assertTrue(
            is_tenant_access_allowed(
                caller_roles=("school_admin",),
                caller_tenant_id=None,
                target_tenant_id=tenant_b,
                active_membership_tenant_ids={tenant_b},
            )
        )
        self.assertFalse(
            is_tenant_access_allowed(
                caller_roles=("school_admin",),
                caller_tenant_id=None,
                target_tenant_id=tenant_a,
                active_membership_tenant_ids={tenant_b},
            )
        )
        # Platform admin has cross-tenant administration rights
        self.assertTrue(
            is_tenant_access_allowed(
                caller_roles=("platform_admin",),
                caller_tenant_id=None,
                target_tenant_id=tenant_b,
            )
        )
        # Child resource boundary check
        self.assertTrue(is_resource_in_tenant(resource_tenant_id=tenant_a, target_tenant_id=tenant_a))
        self.assertFalse(is_resource_in_tenant(resource_tenant_id=tenant_b, target_tenant_id=tenant_a))
        self.assertFalse(is_resource_in_tenant(resource_tenant_id=None, target_tenant_id=tenant_a))

    def test_slug_config_and_org_csv(self) -> None:
        self.assertEqual(normalize_tenant_slug("  Delhi Public School — North! "), "delhi-public-school-north")
        with self.assertRaises(ValueError):
            normalize_tenant_slug("!!")
        merged = merge_tenant_config({"allow_ai_tutor": False}, {"allow_parent_portal": False})
        self.assertFalse(merged["allow_ai_tutor"])
        self.assertFalse(merged["allow_parent_portal"])
        self.assertTrue(merged["allow_homework_ai"])
        csv_out = render_org_report_csv(["Org", "School"], [["=EVIL()", "DPS North"]])
        self.assertIn("'=EVIL(),DPS North", csv_out)

    def test_subscription_entitlements_and_quota_enforcement(self) -> None:
        merged = merge_plan_entitlements(
            {"ai_tutor": True, "live_classroom": False},
            {"live_classroom": True},
        )
        self.assertTrue(merged["live_classroom"])

        ok = evaluate_entitlement_quota(
            subscription_status="active", resource="students", used=149, limit=150
        )
        self.assertTrue(ok.allowed)

        full = evaluate_entitlement_quota(
            subscription_status="active", resource="students", used=150, limit=150
        )
        self.assertFalse(full.allowed)
        self.assertIn("limit reached", full.reason or "")

        cancelled = evaluate_entitlement_quota(
            subscription_status="cancelled", resource="branches", used=0, limit=2
        )
        self.assertFalse(cancelled.allowed)
        self.assertIn("cancelled", cancelled.reason or "")


if __name__ == "__main__":
    unittest.main()
