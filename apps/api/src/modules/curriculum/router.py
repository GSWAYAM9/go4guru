"""HTTP API endpoints for the 11-level versioned curriculum hierarchy."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_db_session,
    get_optional_user,
    require_permissions,
)
from src.modules.curriculum.schemas import (
    AcademicSessionCreate,
    AcademicSessionOut,
    BoardCreate,
    BoardOut,
    BookCreate,
    ChapterCreate,
    ConceptCreate,
    CurriculumTreeResponse,
    CurriculumVersionCreate,
    CurriculumVersionOut,
    ExamTrackOut,
    GradeOut,
    LearningObjectiveCreate,
    PrerequisiteCreate,
    PrerequisiteNode,
    SectionCreate,
    SubjectCreate,
    SubjectOut,
    TopicCreate,
)
from src.modules.curriculum.service import CurriculumService

curriculum_router = APIRouter(prefix="/api/v1/curriculum", tags=["curriculum"])


@curriculum_router.get("/boards", response_model=list[BoardOut])
async def list_boards(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[BoardOut]:
    rows = await CurriculumService(db).list_boards()
    return [BoardOut(id=r.id, code=r.code, name=r.name, country=r.country) for r in rows]


@curriculum_router.post("/boards", response_model=BoardOut, status_code=status.HTTP_201_CREATED)
async def create_board(
    payload: BoardCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> BoardOut:
    r = await CurriculumService(db).create_board(payload, caller)
    return BoardOut(id=r.id, code=r.code, name=r.name, country=r.country)


@curriculum_router.get("/sessions", response_model=list[AcademicSessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[AcademicSessionOut]:
    rows = await CurriculumService(db).list_sessions()
    return [
        AcademicSessionOut(
            id=r.id,
            code=r.code,
            starts_on=r.starts_on,
            ends_on=r.ends_on,
            is_active=r.is_active,
        )
        for r in rows
    ]


@curriculum_router.post(
    "/sessions", response_model=AcademicSessionOut, status_code=status.HTTP_201_CREATED
)
async def create_session(
    payload: AcademicSessionCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AcademicSessionOut:
    r = await CurriculumService(db).create_session(payload, caller)
    return AcademicSessionOut(
        id=r.id,
        code=r.code,
        starts_on=r.starts_on,
        ends_on=r.ends_on,
        is_active=r.is_active,
    )


@curriculum_router.get("/grades", response_model=list[GradeOut])
async def list_grades(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[GradeOut]:
    rows = await CurriculumService(db).list_grades()
    return [GradeOut(id=r.id, number=r.number, label=r.label) for r in rows]


@curriculum_router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[SubjectOut]:
    rows = await CurriculumService(db).list_subjects()
    return [SubjectOut(id=r.id, code=r.code, name=r.name, discipline=r.discipline) for r in rows]


@curriculum_router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> SubjectOut:
    r = await CurriculumService(db).create_subject(payload, caller)
    return SubjectOut(id=r.id, code=r.code, name=r.name, discipline=r.discipline)


@curriculum_router.get("/exam-tracks", response_model=list[ExamTrackOut])
async def list_exam_tracks(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ExamTrackOut]:
    rows = await CurriculumService(db).list_exam_tracks()
    return [ExamTrackOut(id=r.id, code=r.code, name=r.name) for r in rows]


@curriculum_router.get("/versions", response_model=list[CurriculumVersionOut])
async def list_versions(
    include_drafts: bool = False,
    caller: AuthenticatedUser | None = Depends(get_optional_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[CurriculumVersionOut]:
    allow_drafts = bool(
        include_drafts
        and caller is not None
        and caller.has_permission("curriculum:write")
        and (not caller.requires_mfa or caller.mfa_verified)
    )
    rows = await CurriculumService(db).list_versions(include_drafts=allow_drafts)
    return [
        CurriculumVersionOut(
            id=r.id,
            board_id=r.board_id,
            academic_session_id=r.academic_session_id,
            version_tag=r.version_tag,
            status=r.status,
            published_at=r.published_at,
        )
        for r in rows
    ]


@curriculum_router.post(
    "/versions", response_model=CurriculumVersionOut, status_code=status.HTTP_201_CREATED
)
async def create_version(
    payload: CurriculumVersionCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> CurriculumVersionOut:
    r = await CurriculumService(db).create_version(payload, caller)
    return CurriculumVersionOut(
        id=r.id,
        board_id=r.board_id,
        academic_session_id=r.academic_session_id,
        version_tag=r.version_tag,
        status=r.status,
        published_at=r.published_at,
    )


@curriculum_router.post("/versions/{version_id}/publish", response_model=CurriculumVersionOut)
async def publish_version(
    version_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:publish")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> CurriculumVersionOut:
    r = await CurriculumService(db).publish_version(version_id, caller)
    return CurriculumVersionOut(
        id=r.id,
        board_id=r.board_id,
        academic_session_id=r.academic_session_id,
        version_tag=r.version_tag,
        status=r.status,
        published_at=r.published_at,
    )


@curriculum_router.post(
    "/books", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def create_book(
    payload: BookCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    b = await CurriculumService(db).create_book(payload, caller)
    return {"id": str(b.id), "title": b.title}


@curriculum_router.post(
    "/chapters", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def create_chapter(
    payload: ChapterCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    ch = await CurriculumService(db).create_chapter(payload, caller)
    return {"id": str(ch.id), "title": ch.title}


@curriculum_router.post(
    "/sections", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def create_section(
    payload: SectionCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    sec = await CurriculumService(db).create_section(payload)
    return {"id": str(sec.id), "title": sec.title}


@curriculum_router.post(
    "/topics", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def create_topic(
    payload: TopicCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    tp = await CurriculumService(db).create_topic(payload)
    return {"id": str(tp.id), "title": tp.title}


@curriculum_router.post(
    "/concepts", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def create_concept(
    payload: ConceptCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    cp = await CurriculumService(db).create_concept(payload)
    return {"id": str(cp.id), "code": cp.code, "title": cp.title}


@curriculum_router.post(
    "/learning-objectives", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def create_learning_objective(
    payload: LearningObjectiveCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    lo = await CurriculumService(db).create_learning_objective(payload)
    return {"id": str(lo.id), "bloom_level": lo.bloom_level}


@curriculum_router.post(
    "/prerequisites", response_model=PrerequisiteNode, status_code=status.HTTP_201_CREATED
)
async def add_prerequisite(
    payload: PrerequisiteCreate,
    caller: AuthenticatedUser = Depends(require_permissions("curriculum:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> PrerequisiteNode:
    return await CurriculumService(db).add_prerequisite(payload)


@curriculum_router.get("/tree", response_model=CurriculumTreeResponse | None)
async def get_curriculum_tree(
    version_id: UUID | None = None,
    grade_id: UUID | None = None,
    subject_id: UUID | None = None,
    include_drafts: bool = False,
    caller: AuthenticatedUser | None = Depends(get_optional_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> CurriculumTreeResponse | None:
    allow_drafts = bool(
        include_drafts
        and caller is not None
        and caller.has_permission("curriculum:write")
        and (not caller.requires_mfa or caller.mfa_verified)
    )
    return await CurriculumService(db).get_tree(
        version_id=version_id,
        grade_id=grade_id,
        subject_id=subject_id,
        include_drafts=allow_drafts,
    )
