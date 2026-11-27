"""FastAPI router for Institutional Multi-Tenant Platform (/api/v1/org/*)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
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
    OrganizationConfigUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    SchoolConfigUpdateRequest,
    SchoolCreateRequest,
    SchoolResponse,
)
from src.modules.organization.service import (
    add_institution_member,
    create_academic_year,
    create_batch,
    create_branch,
    create_institution_assessment,
    create_organization,
    create_school,
    enroll_student_in_batch,
    export_institution_report_csv,
    get_institution_report,
    list_academic_years,
    list_accessible_organizations,
    list_batch_enrollments,
    list_batches,
    list_branches,
    list_institution_assessments,
    list_institution_members,
    list_schools,
    update_organization_config,
    update_school_config,
)

organization_router = APIRouter(prefix="/api/v1/org", tags=["organization"])


@organization_router.get("/organizations", response_model=list[OrganizationResponse])
async def list_organizations_endpoint(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> list[OrganizationResponse]:
    return await list_accessible_organizations(db, caller)


@organization_router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization_endpoint(
    payload: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> OrganizationResponse:
    return await create_organization(db, caller, payload)


@organization_router.patch(
    "/organizations/{org_id}/config",
    response_model=OrganizationResponse,
)
async def update_org_config_endpoint(
    org_id: UUID,
    payload: OrganizationConfigUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> OrganizationResponse:
    return await update_organization_config(db, caller, org_id, payload)


@organization_router.get(
    "/organizations/{org_id}/schools",
    response_model=list[SchoolResponse],
)
async def list_schools_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> list[SchoolResponse]:
    return await list_schools(db, caller, org_id)


@organization_router.post(
    "/organizations/{org_id}/schools",
    response_model=SchoolResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_school_endpoint(
    org_id: UUID,
    payload: SchoolCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> SchoolResponse:
    return await create_school(db, caller, org_id, payload)


@organization_router.patch(
    "/organizations/{org_id}/schools/{school_id}",
    response_model=SchoolResponse,
)
async def update_school_endpoint(
    org_id: UUID,
    school_id: UUID,
    payload: SchoolConfigUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> SchoolResponse:
    return await update_school_config(db, caller, org_id, school_id, payload)


@organization_router.get(
    "/organizations/{org_id}/branches",
    response_model=list[BranchResponse],
)
async def list_branches_endpoint(
    org_id: UUID,
    school_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> list[BranchResponse]:
    return await list_branches(db, caller, org_id, school_id=school_id)


@organization_router.post(
    "/organizations/{org_id}/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch_endpoint(
    org_id: UUID,
    payload: BranchCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> BranchResponse:
    return await create_branch(db, caller, org_id, payload)


@organization_router.get(
    "/organizations/{org_id}/academic-years",
    response_model=list[AcademicYearResponse],
)
async def list_academic_years_endpoint(
    org_id: UUID,
    school_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> list[AcademicYearResponse]:
    return await list_academic_years(db, caller, org_id, school_id=school_id)


@organization_router.post(
    "/organizations/{org_id}/academic-years",
    response_model=AcademicYearResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_academic_year_endpoint(
    org_id: UUID,
    payload: AcademicYearCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> AcademicYearResponse:
    return await create_academic_year(db, caller, org_id, payload)


@organization_router.get(
    "/organizations/{org_id}/batches",
    response_model=list[BatchResponse],
)
async def list_batches_endpoint(
    org_id: UUID,
    school_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> list[BatchResponse]:
    return await list_batches(db, caller, org_id, school_id=school_id)


@organization_router.post(
    "/organizations/{org_id}/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_endpoint(
    org_id: UUID,
    payload: BatchCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> BatchResponse:
    return await create_batch(db, caller, org_id, payload)


@organization_router.get(
    "/organizations/{org_id}/members",
    response_model=list[InstitutionMemberResponse],
)
async def list_members_endpoint(
    org_id: UUID,
    member_role: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_staff")),  # noqa: B008
) -> list[InstitutionMemberResponse]:
    return await list_institution_members(db, caller, org_id, member_role=member_role)


@organization_router.post(
    "/organizations/{org_id}/members",
    response_model=InstitutionMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member_endpoint(
    org_id: UUID,
    payload: InstitutionMemberAddRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_staff")),  # noqa: B008
) -> InstitutionMemberResponse:
    return await add_institution_member(db, caller, org_id, payload)


@organization_router.get(
    "/organizations/{org_id}/batches/{batch_id}/enrollments",
    response_model=list[BatchEnrollmentResponse],
)
async def list_batch_enrollments_endpoint(
    org_id: UUID,
    batch_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_enrollments")),  # noqa: B008
) -> list[BatchEnrollmentResponse]:
    return await list_batch_enrollments(db, caller, org_id, batch_id)


@organization_router.post(
    "/organizations/{org_id}/batches/{batch_id}/enrollments",
    response_model=BatchEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_student_in_batch_endpoint(
    org_id: UUID,
    batch_id: UUID,
    payload: BatchEnrollStudentRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_enrollments")),  # noqa: B008
) -> BatchEnrollmentResponse:
    return await enroll_student_in_batch(db, caller, org_id, batch_id, payload)


@organization_router.get(
    "/organizations/{org_id}/assessments",
    response_model=list[InstitutionAssessmentResponse],
)
async def list_institution_assessments_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> list[InstitutionAssessmentResponse]:
    return await list_institution_assessments(db, caller, org_id)


@organization_router.post(
    "/organizations/{org_id}/assessments",
    response_model=InstitutionAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_institution_assessment_endpoint(
    org_id: UUID,
    payload: InstitutionAssessmentCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:manage_tenant")),  # noqa: B008
) -> InstitutionAssessmentResponse:
    return await create_institution_assessment(db, caller, org_id, payload)


@organization_router.get(
    "/organizations/{org_id}/reports",
    response_model=InstitutionReportResponse,
)
async def get_institution_report_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:view_reports")),  # noqa: B008
) -> InstitutionReportResponse:
    return await get_institution_report(db, caller, org_id)


@organization_router.get("/organizations/{org_id}/reports.csv")
async def export_institution_report_csv_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("org:view_reports")),  # noqa: B008
) -> Response:
    filename, csv_body = await export_institution_report_csv(db, caller, org_id)
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
