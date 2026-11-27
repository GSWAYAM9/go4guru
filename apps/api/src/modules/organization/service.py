"""Service layer for Institutional Multi-Tenant Platform (Phase 8 F-003).

Every institution-owned record is strictly scoped by `tenant_id`.
Backend authorization is enforced on EVERY read and write query:
- Caller MUST belong to `org_id` (via JWT tenant_id or active InstitutionMembership) or be `platform_admin`.
- All child entity foreign keys (school_id, branch_id, academic_year_id, batch_id) are validated to belong to `org_id`.
- Seat and branch limits are enforced via `billing.public.assert_tenant_quota_available`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.assessment.public import get_student_progress_snapshot
from src.modules.billing.public import (
    assert_tenant_quota_available,
    attach_default_plan_to_tenant,
    get_tenant_entitlements_contract,
)
from src.modules.identity.public import (
    ensure_user_tenant_role,
    get_user_displays_map,
    resolve_user_by_email,
)
from src.modules.learning.public import get_concept_mastery_scores_map
from src.modules.organization.logic import (
    is_resource_in_tenant,
    is_tenant_access_allowed,
    merge_tenant_config,
    normalize_tenant_slug,
    render_org_report_csv,
)
from src.modules.organization.models import (
    AcademicYear,
    BatchEnrollment,
    Branch,
    InstitutionAssessment,
    InstitutionBatch,
    InstitutionMembership,
    Organization,
    School,
)
from src.modules.organization.schemas import (
    AcademicYearCreateRequest,
    AcademicYearResponse,
    BatchCreateRequest,
    BatchEnrollmentResponse,
    BatchEnrollStudentRequest,
    BatchResponse,
    BranchCreateRequest,
    BranchResponse,
    InstitutionAssessmentCreateRequest,
    InstitutionAssessmentResponse,
    InstitutionMemberAddRequest,
    InstitutionMemberResponse,
    InstitutionReportResponse,
    InstitutionSchoolSummaryRow,
    OrganizationConfigUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    SchoolConfigUpdateRequest,
    SchoolCreateRequest,
    SchoolResponse,
)


async def _get_caller_membership_tenant_ids(db: AsyncSession, user_id: UUID) -> set[UUID]:
    rows = (
        await db.scalars(
            select(InstitutionMembership.tenant_id).where(
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.status == "active",
            )
        )
    ).all()
    return set(rows)


async def _require_tenant_access(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID
) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ORGANIZATION_NOT_FOUND",
            message="Organization not found.",
        )
    memberships = (
        set()
        if caller.has_role("platform_admin")
        else await _get_caller_membership_tenant_ids(db, caller.id)
    )
    if not is_tenant_access_allowed(
        caller_roles=caller.roles,
        caller_tenant_id=caller.tenant_id,
        target_tenant_id=org.id,
        active_membership_tenant_ids=memberships,
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_FORBIDDEN",
            message="Access denied: caller does not belong to this institution tenant.",
        )
    return org


async def _require_school_in_tenant(db: AsyncSession, *, org_id: UUID, school_id: UUID) -> School:
    school = await db.get(School, school_id)
    if school is None or not is_resource_in_tenant(
        resource_tenant_id=school.tenant_id, target_tenant_id=org_id
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_RESOURCE_FORBIDDEN",
            message="Requested school does not exist within this tenant boundary.",
        )
    return school


async def _serialize_org(db: AsyncSession, org: Organization) -> OrganizationResponse:
    ent = await get_tenant_entitlements_contract(db, org.id)
    return OrganizationResponse(
        id=org.id,
        slug=org.slug,
        name=org.name,
        organization_type=org.organization_type,
        status=org.status,
        contact_email=org.contact_email,
        config=merge_tenant_config(org.config_jsonb, None),
        plan_code=ent.plan_code if ent else None,
        plan_name=ent.plan_name if ent else None,
        subscription_status=ent.status if ent else None,
        seat_limit=ent.seat_limit if ent else 0,
        max_teachers=ent.max_teachers if ent else 0,
        max_branches=ent.max_branches if ent else 0,
        entitlements=ent.entitlements if ent else {},
        created_at=org.created_at,
    )


async def list_accessible_organizations(
    db: AsyncSession, caller: AuthenticatedUser
) -> list[OrganizationResponse]:
    if caller.has_role("platform_admin"):
        orgs = (await db.scalars(select(Organization).order_by(Organization.created_at.desc()))).all()
    else:
        allowed_ids = await _get_caller_membership_tenant_ids(db, caller.id)
        if caller.tenant_id is not None:
            allowed_ids.add(caller.tenant_id)
        if not allowed_ids:
            return []
        orgs = (
            await db.scalars(
                select(Organization)
                .where(Organization.id.in_(list(allowed_ids)))
                .order_by(Organization.created_at.desc())
            )
        ).all()
    return [await _serialize_org(db, o) for o in orgs]


async def create_organization(
    db: AsyncSession, caller: AuthenticatedUser, payload: OrganizationCreateRequest
) -> OrganizationResponse:
    try:
        slug = normalize_tenant_slug(payload.slug)
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_ORGANIZATION_SLUG",
            message=str(exc),
        ) from exc

    existing = await db.scalar(select(Organization).where(Organization.slug == slug))
    if existing is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="ORGANIZATION_SLUG_EXISTS",
            message=f"Organization slug '{slug}' is already registered.",
        )

    org = Organization(
        slug=slug,
        name=payload.name.strip(),
        organization_type=payload.organization_type,
        status="active",
        contact_email=payload.contact_email.lower().strip(),
        config_jsonb=merge_tenant_config(None, None),
        created_by=caller.id,
    )
    db.add(org)
    await db.flush()

    # Attach default subscription plan and bind creator as school_admin member of the new tenant.
    await attach_default_plan_to_tenant(db, tenant_id=org.id, plan_code=payload.plan_code)
    db.add(
        InstitutionMembership(
            tenant_id=org.id,
            user_id=caller.id,
            member_role="school_admin",
            status="active",
        )
    )
    await ensure_user_tenant_role(
        db,
        user_id=caller.id,
        role_code="school_admin",
        tenant_id=org.id,
        granted_by=caller.id,
    )
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "school_admin",
        action="organization.onboarded",
        resource_type="organization",
        resource_id=str(org.id),
        tenant_id=org.id,
        metadata={"slug": slug, "plan_code": payload.plan_code},
    )
    await db.commit()
    await db.refresh(org)
    return await _serialize_org(db, org)


async def update_organization_config(
    db: AsyncSession,
    caller: AuthenticatedUser,
    org_id: UUID,
    payload: OrganizationConfigUpdateRequest,
) -> OrganizationResponse:
    org = await _require_tenant_access(db, caller, org_id)
    org.config_jsonb = merge_tenant_config(org.config_jsonb, payload.model_dump(exclude_none=True))
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "school_admin",
        action="organization.config_updated",
        resource_type="organization",
        resource_id=str(org.id),
        tenant_id=org.id,
        metadata=org.config_jsonb,
    )
    await db.commit()
    await db.refresh(org)
    return await _serialize_org(db, org)


async def list_schools(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID
) -> list[SchoolResponse]:
    await _require_tenant_access(db, caller, org_id)
    schools = (
        await db.scalars(
            select(School).where(School.tenant_id == org_id).order_by(School.created_at.desc())
        )
    ).all()
    results: list[SchoolResponse] = []
    for s in schools:
        br_cnt = int(
            await db.scalar(
                select(func.count(Branch.id)).where(
                    Branch.tenant_id == org_id, Branch.school_id == s.id
                )
            )
            or 0
        )
        bt_cnt = int(
            await db.scalar(
                select(func.count(InstitutionBatch.id)).where(
                    InstitutionBatch.tenant_id == org_id, InstitutionBatch.school_id == s.id
                )
            )
            or 0
        )
        results.append(
            SchoolResponse(
                id=s.id,
                tenant_id=s.tenant_id,
                code=s.code,
                name=s.name,
                board_code=s.board_code,
                city=s.city,
                status=s.status,
                config=dict(s.config_jsonb or {}),
                branches_count=br_cnt,
                batches_count=bt_cnt,
                created_at=s.created_at,
            )
        )
    return results


async def create_school(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, payload: SchoolCreateRequest
) -> SchoolResponse:
    await _require_tenant_access(db, caller, org_id)
    code_norm = payload.code.strip().upper()
    existing = await db.scalar(
        select(School).where(School.tenant_id == org_id, School.code == code_norm)
    )
    if existing is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="SCHOOL_CODE_EXISTS",
            message=f"School code '{code_norm}' already exists in this organization.",
        )
    school = School(
        tenant_id=org_id,
        code=code_norm,
        name=payload.name.strip(),
        board_code=payload.board_code.strip().upper(),
        city=payload.city.strip() if payload.city else None,
        status="active",
        config_jsonb={},
    )
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return SchoolResponse(
        id=school.id,
        tenant_id=school.tenant_id,
        code=school.code,
        name=school.name,
        board_code=school.board_code,
        city=school.city,
        status=school.status,
        config={},
        branches_count=0,
        batches_count=0,
        created_at=school.created_at,
    )


async def update_school_config(
    db: AsyncSession,
    caller: AuthenticatedUser,
    org_id: UUID,
    school_id: UUID,
    payload: SchoolConfigUpdateRequest,
) -> SchoolResponse:
    await _require_tenant_access(db, caller, org_id)
    school = await _require_school_in_tenant(db, org_id=org_id, school_id=school_id)
    if payload.name is not None:
        school.name = payload.name.strip()
    if payload.board_code is not None:
        school.board_code = payload.board_code.strip().upper()
    if payload.city is not None:
        school.city = payload.city.strip()
    if payload.config is not None:
        merged = dict(school.config_jsonb or {})
        merged.update(payload.config)
        school.config_jsonb = merged
    await db.commit()
    await db.refresh(school)
    return SchoolResponse(
        id=school.id,
        tenant_id=school.tenant_id,
        code=school.code,
        name=school.name,
        board_code=school.board_code,
        city=school.city,
        status=school.status,
        config=dict(school.config_jsonb or {}),
        created_at=school.created_at,
    )


async def list_branches(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, school_id: UUID | None = None
) -> list[BranchResponse]:
    await _require_tenant_access(db, caller, org_id)
    stmt = select(Branch).where(Branch.tenant_id == org_id)
    if school_id is not None:
        await _require_school_in_tenant(db, org_id=org_id, school_id=school_id)
        stmt = stmt.where(Branch.school_id == school_id)
    rows = (await db.scalars(stmt.order_by(Branch.created_at.desc()))).all()
    return [
        BranchResponse(
            id=b.id,
            tenant_id=b.tenant_id,
            school_id=b.school_id,
            code=b.code,
            name=b.name,
            address=b.address,
            status=b.status,
            created_at=b.created_at,
        )
        for b in rows
    ]


async def create_branch(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, payload: BranchCreateRequest
) -> BranchResponse:
    await _require_tenant_access(db, caller, org_id)
    await _require_school_in_tenant(db, org_id=org_id, school_id=payload.school_id)
    current_branches = int(
        await db.scalar(select(func.count(Branch.id)).where(Branch.tenant_id == org_id)) or 0
    )
    await assert_tenant_quota_available(
        db, tenant_id=org_id, resource="branches", current_used=current_branches
    )
    branch = Branch(
        tenant_id=org_id,
        school_id=payload.school_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        address=payload.address.strip() if payload.address else None,
        status="active",
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return BranchResponse(
        id=branch.id,
        tenant_id=branch.tenant_id,
        school_id=branch.school_id,
        code=branch.code,
        name=branch.name,
        address=branch.address,
        status=branch.status,
        created_at=branch.created_at,
    )


async def list_academic_years(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, school_id: UUID | None = None
) -> list[AcademicYearResponse]:
    await _require_tenant_access(db, caller, org_id)
    stmt = select(AcademicYear).where(AcademicYear.tenant_id == org_id)
    if school_id is not None:
        await _require_school_in_tenant(db, org_id=org_id, school_id=school_id)
        stmt = stmt.where(AcademicYear.school_id == school_id)
    rows = (await db.scalars(stmt.order_by(AcademicYear.starts_on.desc()))).all()
    return [
        AcademicYearResponse(
            id=y.id,
            tenant_id=y.tenant_id,
            school_id=y.school_id,
            label=y.label,
            starts_on=y.starts_on,
            ends_on=y.ends_on,
            is_current=y.is_current,
        )
        for y in rows
    ]


async def create_academic_year(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, payload: AcademicYearCreateRequest
) -> AcademicYearResponse:
    await _require_tenant_access(db, caller, org_id)
    await _require_school_in_tenant(db, org_id=org_id, school_id=payload.school_id)
    if payload.ends_on <= payload.starts_on:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_ACADEMIC_YEAR_DATES",
            message="Academic year end date must be after start date.",
        )
    ay = AcademicYear(
        tenant_id=org_id,
        school_id=payload.school_id,
        label=payload.label.strip(),
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        is_current=payload.is_current,
    )
    db.add(ay)
    await db.commit()
    await db.refresh(ay)
    return AcademicYearResponse(
        id=ay.id,
        tenant_id=ay.tenant_id,
        school_id=ay.school_id,
        label=ay.label,
        starts_on=ay.starts_on,
        ends_on=ay.ends_on,
        is_current=ay.is_current,
    )


async def list_batches(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, school_id: UUID | None = None
) -> list[BatchResponse]:
    await _require_tenant_access(db, caller, org_id)
    stmt = select(InstitutionBatch).where(InstitutionBatch.tenant_id == org_id)
    if school_id is not None:
        await _require_school_in_tenant(db, org_id=org_id, school_id=school_id)
        stmt = stmt.where(InstitutionBatch.school_id == school_id)
    rows = (await db.scalars(stmt.order_by(InstitutionBatch.created_at.desc()))).all()
    results: list[BatchResponse] = []
    for b in rows:
        cnt = int(
            await db.scalar(
                select(func.count(BatchEnrollment.id)).where(
                    BatchEnrollment.tenant_id == org_id,
                    BatchEnrollment.batch_id == b.id,
                    BatchEnrollment.status == "active",
                )
            )
            or 0
        )
        results.append(
            BatchResponse(
                id=b.id,
                tenant_id=b.tenant_id,
                school_id=b.school_id,
                branch_id=b.branch_id,
                academic_year_id=b.academic_year_id,
                name=b.name,
                grade_label=b.grade_label,
                section_name=b.section_name,
                exam_track=b.exam_track,
                capacity=b.capacity,
                status=b.status,
                enrolled_count=cnt,
            )
        )
    return results


async def create_batch(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, payload: BatchCreateRequest
) -> BatchResponse:
    await _require_tenant_access(db, caller, org_id)
    await _require_school_in_tenant(db, org_id=org_id, school_id=payload.school_id)
    if payload.branch_id is not None:
        br = await db.get(Branch, payload.branch_id)
        if br is None or not is_resource_in_tenant(
            resource_tenant_id=br.tenant_id, target_tenant_id=org_id
        ):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="CROSS_TENANT_RESOURCE_FORBIDDEN",
                message="Branch does not belong to this tenant.",
            )
    if payload.academic_year_id is not None:
        ay = await db.get(AcademicYear, payload.academic_year_id)
        if ay is None or not is_resource_in_tenant(
            resource_tenant_id=ay.tenant_id, target_tenant_id=org_id
        ):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="CROSS_TENANT_RESOURCE_FORBIDDEN",
                message="Academic year does not belong to this tenant.",
            )
    batch = InstitutionBatch(
        tenant_id=org_id,
        school_id=payload.school_id,
        branch_id=payload.branch_id,
        academic_year_id=payload.academic_year_id,
        name=payload.name.strip(),
        grade_label=payload.grade_label.strip(),
        section_name=payload.section_name.strip(),
        exam_track=payload.exam_track.strip(),
        capacity=payload.capacity,
        status="active",
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return BatchResponse(
        id=batch.id,
        tenant_id=batch.tenant_id,
        school_id=batch.school_id,
        branch_id=batch.branch_id,
        academic_year_id=batch.academic_year_id,
        name=batch.name,
        grade_label=batch.grade_label,
        section_name=batch.section_name,
        exam_track=batch.exam_track,
        capacity=batch.capacity,
        status=batch.status,
        enrolled_count=0,
    )


async def list_institution_members(
    db: AsyncSession,
    caller: AuthenticatedUser,
    org_id: UUID,
    member_role: str | None = None,
) -> list[InstitutionMemberResponse]:
    await _require_tenant_access(db, caller, org_id)
    stmt = select(InstitutionMembership).where(
        InstitutionMembership.tenant_id == org_id,
        InstitutionMembership.status == "active",
    )
    if member_role:
        stmt = stmt.where(InstitutionMembership.member_role == member_role)
    rows = (await db.scalars(stmt.order_by(InstitutionMembership.created_at.desc()))).all()
    displays = await get_user_displays_map(db, [m.user_id for m in rows])
    return [
        InstitutionMemberResponse(
            id=m.id,
            tenant_id=m.tenant_id,
            school_id=m.school_id,
            branch_id=m.branch_id,
            user_id=m.user_id,
            user_name=displays[m.user_id].display_name if m.user_id in displays else "Member",
            user_email=displays[m.user_id].email if m.user_id in displays else "",
            member_role=m.member_role,
            status=m.status,
            created_at=m.created_at,
        )
        for m in rows
    ]


async def add_institution_member(
    db: AsyncSession,
    caller: AuthenticatedUser,
    org_id: UUID,
    payload: InstitutionMemberAddRequest,
) -> InstitutionMemberResponse:
    await _require_tenant_access(db, caller, org_id)
    if payload.school_id is not None:
        await _require_school_in_tenant(db, org_id=org_id, school_id=payload.school_id)
    user_disp = await resolve_user_by_email(db, payload.user_email)
    if user_disp is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message="No active user account matches that email.",
        )

    existing = await db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.tenant_id == org_id,
            InstitutionMembership.user_id == user_disp.user_id,
            InstitutionMembership.member_role == payload.member_role,
        )
    )
    if existing is None:
        if payload.member_role == "student":
            stu_count = int(
                await db.scalar(
                    select(func.count(InstitutionMembership.id)).where(
                        InstitutionMembership.tenant_id == org_id,
                        InstitutionMembership.member_role == "student",
                        InstitutionMembership.status == "active",
                    )
                )
                or 0
            )
            await assert_tenant_quota_available(
                db, tenant_id=org_id, resource="students", current_used=stu_count
            )
        elif payload.member_role == "teacher":
            tch_count = int(
                await db.scalar(
                    select(func.count(InstitutionMembership.id)).where(
                        InstitutionMembership.tenant_id == org_id,
                        InstitutionMembership.member_role == "teacher",
                        InstitutionMembership.status == "active",
                    )
                )
                or 0
            )
            await assert_tenant_quota_available(
                db, tenant_id=org_id, resource="teachers", current_used=tch_count
            )

        member = InstitutionMembership(
            tenant_id=org_id,
            school_id=payload.school_id,
            branch_id=payload.branch_id,
            user_id=user_disp.user_id,
            member_role=payload.member_role,
            status="active",
        )
        db.add(member)
    else:
        existing.status = "active"
        existing.school_id = payload.school_id
        existing.branch_id = payload.branch_id
        member = existing

    await ensure_user_tenant_role(
        db,
        user_id=user_disp.user_id,
        role_code=payload.member_role,
        tenant_id=org_id,
        granted_by=caller.id,
    )
    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "school_admin",
        action="institution_member.added",
        resource_type="institution_membership",
        resource_id=str(member.id),
        tenant_id=org_id,
        metadata={"user_id": str(user_disp.user_id), "member_role": payload.member_role},
    )
    await db.commit()
    await db.refresh(member)
    return InstitutionMemberResponse(
        id=member.id,
        tenant_id=member.tenant_id,
        school_id=member.school_id,
        branch_id=member.branch_id,
        user_id=user_disp.user_id,
        user_name=user_disp.display_name,
        user_email=user_disp.email,
        member_role=member.member_role,
        status=member.status,
        created_at=member.created_at,
    )


async def enroll_student_in_batch(
    db: AsyncSession,
    caller: AuthenticatedUser,
    org_id: UUID,
    batch_id: UUID,
    payload: BatchEnrollStudentRequest,
) -> BatchEnrollmentResponse:
    await _require_tenant_access(db, caller, org_id)
    batch = await db.get(InstitutionBatch, batch_id)
    if batch is None or not is_resource_in_tenant(
        resource_tenant_id=batch.tenant_id, target_tenant_id=org_id
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_RESOURCE_FORBIDDEN",
            message="Batch does not belong to this tenant.",
        )

    student = await resolve_user_by_email(db, payload.student_email)
    if student is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="STUDENT_NOT_FOUND",
            message="No active student account matches that email.",
        )

    # Ensure tenant student membership exists and complies with seat quota
    membership = await db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.tenant_id == org_id,
            InstitutionMembership.user_id == student.user_id,
            InstitutionMembership.member_role == "student",
        )
    )
    if membership is None:
        stu_count = int(
            await db.scalar(
                select(func.count(InstitutionMembership.id)).where(
                    InstitutionMembership.tenant_id == org_id,
                    InstitutionMembership.member_role == "student",
                    InstitutionMembership.status == "active",
                )
            )
            or 0
        )
        await assert_tenant_quota_available(
            db, tenant_id=org_id, resource="students", current_used=stu_count
        )
        db.add(
            InstitutionMembership(
                tenant_id=org_id,
                school_id=batch.school_id,
                branch_id=batch.branch_id,
                user_id=student.user_id,
                member_role="student",
                status="active",
            )
        )

    existing = await db.scalar(
        select(BatchEnrollment).where(
            BatchEnrollment.batch_id == batch_id,
            BatchEnrollment.student_id == student.user_id,
        )
    )
    if existing is not None:
        existing.status = "active"
        existing.roll_no = payload.roll_no
        enrollment = existing
    else:
        enrollment = BatchEnrollment(
            tenant_id=org_id,
            batch_id=batch_id,
            student_id=student.user_id,
            roll_no=payload.roll_no,
            status="active",
        )
        db.add(enrollment)

    await db.commit()
    await db.refresh(enrollment)
    return BatchEnrollmentResponse(
        id=enrollment.id,
        tenant_id=enrollment.tenant_id,
        batch_id=enrollment.batch_id,
        student_id=student.user_id,
        student_name=student.display_name,
        student_email=student.email,
        roll_no=enrollment.roll_no,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
    )


async def list_batch_enrollments(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID, batch_id: UUID
) -> list[BatchEnrollmentResponse]:
    await _require_tenant_access(db, caller, org_id)
    batch = await db.get(InstitutionBatch, batch_id)
    if batch is None or not is_resource_in_tenant(
        resource_tenant_id=batch.tenant_id, target_tenant_id=org_id
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_RESOURCE_FORBIDDEN",
            message="Batch does not belong to this tenant.",
        )
    rows = (
        await db.scalars(
            select(BatchEnrollment)
            .where(
                BatchEnrollment.tenant_id == org_id,
                BatchEnrollment.batch_id == batch_id,
                BatchEnrollment.status == "active",
            )
            .order_by(BatchEnrollment.enrolled_at.desc())
        )
    ).all()
    displays = await get_user_displays_map(db, [r.student_id for r in rows])
    return [
        BatchEnrollmentResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            batch_id=r.batch_id,
            student_id=r.student_id,
            student_name=displays[r.student_id].display_name if r.student_id in displays else "Student",
            student_email=displays[r.student_id].email if r.student_id in displays else "",
            roll_no=r.roll_no,
            status=r.status,
            enrolled_at=r.enrolled_at,
        )
        for r in rows
    ]


async def list_institution_assessments(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID
) -> list[InstitutionAssessmentResponse]:
    await _require_tenant_access(db, caller, org_id)
    rows = (
        await db.scalars(
            select(InstitutionAssessment)
            .where(InstitutionAssessment.tenant_id == org_id)
            .order_by(InstitutionAssessment.created_at.desc())
        )
    ).all()
    return [
        InstitutionAssessmentResponse(
            id=a.id,
            tenant_id=a.tenant_id,
            school_id=a.school_id,
            batch_id=a.batch_id,
            title=a.title,
            kind=a.kind,
            due_at=a.due_at,
            max_marks=float(a.max_marks),
            status=a.status,
            created_at=a.created_at,
        )
        for a in rows
    ]


async def create_institution_assessment(
    db: AsyncSession,
    caller: AuthenticatedUser,
    org_id: UUID,
    payload: InstitutionAssessmentCreateRequest,
) -> InstitutionAssessmentResponse:
    await _require_tenant_access(db, caller, org_id)
    await _require_school_in_tenant(db, org_id=org_id, school_id=payload.school_id)
    if payload.batch_id is not None:
        batch = await db.get(InstitutionBatch, payload.batch_id)
        if batch is None or not is_resource_in_tenant(
            resource_tenant_id=batch.tenant_id, target_tenant_id=org_id
        ):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code="CROSS_TENANT_RESOURCE_FORBIDDEN",
                message="Batch does not belong to this tenant.",
            )
    asmt = InstitutionAssessment(
        tenant_id=org_id,
        school_id=payload.school_id,
        batch_id=payload.batch_id,
        title=payload.title.strip(),
        kind=payload.kind,
        due_at=payload.due_at,
        max_marks=payload.max_marks,
        status="published",
        created_by=caller.id,
    )
    db.add(asmt)
    await db.commit()
    await db.refresh(asmt)
    return InstitutionAssessmentResponse(
        id=asmt.id,
        tenant_id=asmt.tenant_id,
        school_id=asmt.school_id,
        batch_id=asmt.batch_id,
        title=asmt.title,
        kind=asmt.kind,
        due_at=asmt.due_at,
        max_marks=float(asmt.max_marks),
        status=asmt.status,
        created_at=asmt.created_at,
    )


async def get_institution_report(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID
) -> InstitutionReportResponse:
    org = await _require_tenant_access(db, caller, org_id)
    ent = await get_tenant_entitlements_contract(db, org_id)
    schools = (
        await db.scalars(select(School).where(School.tenant_id == org_id))
    ).all()
    branches_count = int(
        await db.scalar(select(func.count(Branch.id)).where(Branch.tenant_id == org_id)) or 0
    )
    batches_count = int(
        await db.scalar(
            select(func.count(InstitutionBatch.id)).where(InstitutionBatch.tenant_id == org_id)
        )
        or 0
    )
    assessments_count = int(
        await db.scalar(
            select(func.count(InstitutionAssessment.id)).where(
                InstitutionAssessment.tenant_id == org_id
            )
        )
        or 0
    )

    members = (
        await db.scalars(
            select(InstitutionMembership).where(
                InstitutionMembership.tenant_id == org_id,
                InstitutionMembership.status == "active",
            )
        )
    ).all()
    teachers_count = sum(1 for m in members if m.member_role == "teacher")
    mentors_count = sum(1 for m in members if m.member_role == "mentor")
    student_ids = list({m.user_id for m in members if m.member_role == "student"})
    students_count = len(student_ids)

    seat_limit = ent.seat_limit if ent else 150
    seat_util = round((students_count / seat_limit) * 100.0, 2) if seat_limit > 0 else 0.0

    accuracies: list[float] = []
    masteries: list[float] = []
    for sid in student_ids:
        prog = await get_student_progress_snapshot(db, sid)
        if prog.total_attempts > 0:
            accuracies.append((prog.correct_attempts / prog.total_attempts) * 100.0)
        mmap = await get_concept_mastery_scores_map(db, sid)
        if mmap:
            masteries.append(sum(mmap.values()) / len(mmap))

    breakdown: list[InstitutionSchoolSummaryRow] = []
    for s in schools:
        s_br = int(
            await db.scalar(
                select(func.count(Branch.id)).where(
                    Branch.tenant_id == org_id, Branch.school_id == s.id
                )
            )
            or 0
        )
        s_bt = int(
            await db.scalar(
                select(func.count(InstitutionBatch.id)).where(
                    InstitutionBatch.tenant_id == org_id, InstitutionBatch.school_id == s.id
                )
            )
            or 0
        )
        s_as = int(
            await db.scalar(
                select(func.count(InstitutionAssessment.id)).where(
                    InstitutionAssessment.tenant_id == org_id,
                    InstitutionAssessment.school_id == s.id,
                )
            )
            or 0
        )
        breakdown.append(
            InstitutionSchoolSummaryRow(
                school_id=s.id,
                school_name=s.name,
                board_code=s.board_code,
                branches_count=s_br,
                batches_count=s_bt,
                assessments_count=s_as,
            )
        )

    return InstitutionReportResponse(
        tenant_id=org.id,
        organization_name=org.name,
        plan_code=ent.plan_code if ent else "school_starter",
        subscription_status=ent.status if ent else "active",
        schools_count=len(schools),
        branches_count=branches_count,
        max_branches=ent.max_branches if ent else 2,
        batches_count=batches_count,
        teachers_count=teachers_count,
        max_teachers=ent.max_teachers if ent else 20,
        mentors_count=mentors_count,
        students_count=students_count,
        seat_limit=seat_limit,
        seat_utilization_pct=seat_util,
        assessments_count=assessments_count,
        average_student_practice_accuracy_pct=(
            round(sum(accuracies) / len(accuracies), 2) if accuracies else 0.0
        ),
        average_student_mastery_pct=(
            round(sum(masteries) / len(masteries), 2) if masteries else 0.0
        ),
        schools_breakdown=breakdown,
        generated_at=datetime.now(UTC),
    )


async def export_institution_report_csv(
    db: AsyncSession, caller: AuthenticatedUser, org_id: UUID
) -> tuple[str, str]:
    report = await get_institution_report(db, caller, org_id)
    headers = [
        "Organization",
        "School",
        "Board",
        "Branches",
        "Batches",
        "Assessments",
    ]
    rows: list[list[object]] = [
        [
            report.organization_name,
            s.school_name,
            s.board_code,
            s.branches_count,
            s.batches_count,
            s.assessments_count,
        ]
        for s in report.schools_breakdown
    ]
    csv_body = render_org_report_csv(headers, rows)
    safe_slug = "".join(ch if ch.isalnum() else "_" for ch in report.organization_name.lower())[:40]
    return f"go4guru_institution_report_{safe_slug}.csv", csv_body
