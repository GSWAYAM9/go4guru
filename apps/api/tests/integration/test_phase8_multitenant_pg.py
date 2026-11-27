"""PostgreSQL 18 integration & cross-tenant isolation tests for Phase 8 (F-003, F-036)."""

from __future__ import annotations

import pyotp
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from src.core.config import Settings
from src.main import create_app
from src.modules.identity.models import Role, User, UserRole

from tests.conftest import StubCheck
from tests.integration.test_phase1_e2e_pg import pg18_database_url  # noqa: F401


async def _create_mfa_school_admin(
    app, client: AsyncClient, *, email: str, password: str, display_name: str
) -> str:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "date_of_birth_year": 1982,
            "role": "student",
        },
    )
    assert reg.status_code == 201, reg.text
    async with app.state.db.session_factory() as db:
        role = await db.scalar(select(Role).where(Role.code == "school_admin"))
        user = await db.scalar(select(User).where(User.email == email))
        assert role is not None and user is not None
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()

    login1 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login1.status_code == 200
    tok1 = login1.json()["access_token"]

    setup = await client.post(
        "/api/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {tok1}"},
    )
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    totp = pyotp.TOTP(secret).now()
    verify = await client.post(
        "/api/v1/auth/mfa/verify",
        headers={"Authorization": f"Bearer {tok1}"},
        json={"code": totp},
    )
    assert verify.status_code == 200, verify.text
    return str(verify.json()["access_token"])


async def test_phase8_multitenant_onboarding_and_cross_tenant_isolation(
    pg18_database_url: str,  # noqa: F811
) -> None:
    settings = Settings(database_url=pg18_database_url)
    app = create_app(settings_override=settings)
    transport = ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        app.state.redis = StubCheck()  # type: ignore[assignment]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            admin_a = await _create_mfa_school_admin(
                app,
                client,
                email="admin.alpha@example.com",
                password="AdminPassword!123",
                display_name="Alpha Admin",
            )
            admin_b = await _create_mfa_school_admin(
                app,
                client,
                email="admin.beta@example.com",
                password="AdminPassword!123",
                display_name="Beta Admin",
            )

            # Register a student for enrollment tests
            stu_reg = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p8.student@example.com",
                    "password": "StudentPassword!123",
                    "display_name": "Tenant A Student",
                    "date_of_birth_year": 2009,
                    "role": "student",
                },
            )
            assert stu_reg.status_code == 201

            # --- Onboard Tenant A & Tenant B ---
            org_a_resp = await client.post(
                "/api/v1/org/organizations",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={
                    "slug": "alpha-schools",
                    "name": "Alpha Public Schools",
                    "organization_type": "school_group",
                    "contact_email": "admin.alpha@example.com",
                    "plan_code": "school_starter",
                },
            )
            assert org_a_resp.status_code == 201, org_a_resp.text
            org_a_id = org_a_resp.json()["id"]

            org_b_resp = await client.post(
                "/api/v1/org/organizations",
                headers={"Authorization": f"Bearer {admin_b}"},
                json={
                    "slug": "beta-academy",
                    "name": "Beta Coaching Academy",
                    "organization_type": "coaching_institute",
                    "contact_email": "admin.beta@example.com",
                    "plan_code": "school_growth",
                },
            )
            assert org_b_resp.status_code == 201, org_b_resp.text
            org_b_id = org_b_resp.json()["id"]

            # --- Provision School, Branch, Academic Year, Batch, Enrollment, Assessment in Tenant A ---
            school_a = await client.post(
                f"/api/v1/org/organizations/{org_a_id}/schools",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={"code": "ALPHA-01", "name": "Alpha North Campus", "board_code": "CBSE", "city": "Delhi"},
            )
            assert school_a.status_code == 201
            school_a_id = school_a.json()["id"]

            branch_a = await client.post(
                f"/api/v1/org/organizations/{org_a_id}/branches",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={"school_id": school_a_id, "code": "BR-N", "name": "North Wing"},
            )
            assert branch_a.status_code == 201
            branch_a_id = branch_a.json()["id"]

            ay_a = await client.post(
                f"/api/v1/org/organizations/{org_a_id}/academic-years",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={
                    "school_id": school_a_id,
                    "label": "2026-27",
                    "starts_on": "2026-04-01",
                    "ends_on": "2027-03-31",
                    "is_current": True,
                },
            )
            assert ay_a.status_code == 201
            ay_a_id = ay_a.json()["id"]

            batch_a = await client.post(
                f"/api/v1/org/organizations/{org_a_id}/batches",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={
                    "school_id": school_a_id,
                    "branch_id": branch_a_id,
                    "academic_year_id": ay_a_id,
                    "name": "Class 11 JEE Alpha",
                    "grade_label": "Class 11",
                    "section_name": "A",
                    "exam_track": "jee_main",
                },
            )
            assert batch_a.status_code == 201
            batch_a_id = batch_a.json()["id"]

            enroll_a = await client.post(
                f"/api/v1/org/organizations/{org_a_id}/batches/{batch_a_id}/enrollments",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={"student_email": "p8.student@example.com", "roll_no": "ALP-01"},
            )
            assert enroll_a.status_code == 201

            asmt_a = await client.post(
                f"/api/v1/org/organizations/{org_a_id}/assessments",
                headers={"Authorization": f"Bearer {admin_a}"},
                json={
                    "school_id": school_a_id,
                    "batch_id": batch_a_id,
                    "title": "Alpha Term 1 Common Test",
                    "kind": "test",
                    "max_marks": 100,
                },
            )
            assert asmt_a.status_code == 201

            report_a = await client.get(
                f"/api/v1/org/organizations/{org_a_id}/reports",
                headers={"Authorization": f"Bearer {admin_a}"},
            )
            assert report_a.status_code == 200
            assert report_a.json()["schools_count"] == 1
            assert report_a.json()["students_count"] == 1

            # --- EXHAUSTIVE CROSS-TENANT ISOLATION TESTS (Admin B -> Tenant A MUST BE 403) ---
            assert (
                await client.get(
                    f"/api/v1/org/organizations/{org_a_id}/schools",
                    headers={"Authorization": f"Bearer {admin_b}"},
                )
            ).status_code == 403

            assert (
                await client.post(
                    f"/api/v1/org/organizations/{org_a_id}/schools",
                    headers={"Authorization": f"Bearer {admin_b}"},
                    json={"code": "INTRUDER", "name": "Unauthorized School"},
                )
            ).status_code == 403

            assert (
                await client.get(
                    f"/api/v1/org/organizations/{org_a_id}/members",
                    headers={"Authorization": f"Bearer {admin_b}"},
                )
            ).status_code == 403

            assert (
                await client.get(
                    f"/api/v1/org/organizations/{org_a_id}/batches/{batch_a_id}/enrollments",
                    headers={"Authorization": f"Bearer {admin_b}"},
                )
            ).status_code == 403

            assert (
                await client.get(
                    f"/api/v1/org/organizations/{org_a_id}/reports",
                    headers={"Authorization": f"Bearer {admin_b}"},
                )
            ).status_code == 403

            assert (
                await client.patch(
                    f"/api/v1/org/organizations/{org_a_id}/config",
                    headers={"Authorization": f"Bearer {admin_b}"},
                    json={"allow_ai_tutor": False},
                )
            ).status_code == 403

            assert (
                await client.get(
                    f"/api/v1/billing/tenants/{org_a_id}/subscription",
                    headers={"Authorization": f"Bearer {admin_b}"},
                )
            ).status_code == 403

            # Cross-tenant foreign key injection attempt (Tenant B tries attaching branch to Tenant A school_id)
            fk_inject = await client.post(
                f"/api/v1/org/organizations/{org_b_id}/branches",
                headers={"Authorization": f"Bearer {admin_b}"},
                json={"school_id": school_a_id, "code": "HIJACK", "name": "Hijack Branch"},
            )
            assert fk_inject.status_code == 403

            # Verify Tenant B list_organizations only returns Tenant B
            org_list_b = await client.get(
                "/api/v1/org/organizations",
                headers={"Authorization": f"Bearer {admin_b}"},
            )
            assert org_list_b.status_code == 200
            returned_ids = {o["id"] for o in org_list_b.json()}
            assert org_b_id in returned_ids
            assert org_a_id not in returned_ids
