"""FastAPI router for Phase 10 Multilingual Learning Expansion (/api/v1/languages/* & /api/v1/voice/stt)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_current_user,
    get_db_session,
    require_permissions,
)
from src.core.config import Settings, get_settings
from src.modules.classroom.multilingual_schemas import (
    BilingualPreviewRequest,
    BilingualPreviewResponse,
    GlossaryTermCreateRequest,
    GlossaryTermOut,
    LanguageCapabilityDetailOut,
    LanguageCapabilityPatchRequest,
    LanguageQualityEvaluationOut,
    LanguageQualityRunRequest,
    STTRequestBody,
    STTResponseOut,
    TranslationEntryCreateRequest,
    TranslationEntryOut,
    TranslationReviewRequest,
    UiLocalizationBundleOut,
    UserLanguagePreferencesOut,
    UserLanguagePreferencesUpdateRequest,
    VoiceProviderStatusOut,
)
from src.modules.classroom.multilingual_service import MultilingualService

languages_router = APIRouter(prefix="/api/v1/languages", tags=["languages"])
voice_multilingual_router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


def _get_runtime_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", get_settings())


@languages_router.get("/capabilities", response_model=list[LanguageCapabilityDetailOut])
async def get_language_capabilities(
    capability_status: str | None = None,
    tts_only: bool = False,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> list[LanguageCapabilityDetailOut]:
    """List truthful empirical capabilities, provider matrices, testing status & limitations."""
    return await MultilingualService(db, settings).list_capabilities(
        capability_status=capability_status,
        tts_only=tts_only,
    )


@languages_router.patch(
    "/capabilities/{language_code}",
    response_model=LanguageCapabilityDetailOut,
)
async def patch_language_capability(
    language_code: str,
    payload: LanguageCapabilityPatchRequest,
    caller: AuthenticatedUser = Depends(require_permissions("multilingual:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> LanguageCapabilityDetailOut:
    """Update Language Capability Registry metadata (platform_admin only)."""
    return await MultilingualService(db, settings).patch_capability(
        language_code, payload, caller
    )


@languages_router.get("/preferences", response_model=UserLanguagePreferencesOut)
async def get_my_language_preferences(
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> UserLanguagePreferencesOut:
    """Get caller's 6 independent language preferences + deterministic fallback resolutions."""
    return await MultilingualService(db, settings).get_my_preferences(caller)


@languages_router.put("/preferences", response_model=UserLanguagePreferencesOut)
async def update_my_language_preferences(
    payload: UserLanguagePreferencesUpdateRequest,
    caller: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> UserLanguagePreferencesOut:
    """Update any of the 6 independent language dimensions & bilingual explanation mode."""
    return await MultilingualService(db, settings).update_my_preferences(payload, caller)


@languages_router.get("/ui-bundle/{language_code}", response_model=UiLocalizationBundleOut)
async def get_ui_localization_bundle_endpoint(
    language_code: str,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> UiLocalizationBundleOut:
    """Fetch localized UI dictionary with per-key English fallback & honest coverage."""
    return await MultilingualService(db, settings).get_ui_bundle(language_code)


@languages_router.get("/glossary", response_model=list[GlossaryTermOut])
async def list_multilingual_glossary(
    language_code: str | None = None,
    subject_area: str | None = None,
    query: str | None = None,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> list[GlossaryTermOut]:
    """Search canonical multilingual STEM glossary terms."""
    return await MultilingualService(db, settings).list_glossary(
        language_code=language_code,
        subject_area=subject_area,
        query=query,
    )


@languages_router.post(
    "/glossary",
    response_model=GlossaryTermOut,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_multilingual_glossary_term(
    payload: GlossaryTermCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("multilingual:translate")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> GlossaryTermOut:
    """Create or update a canonical STEM glossary term."""
    return await MultilingualService(db, settings).upsert_glossary_term(payload, caller)


@languages_router.post("/bilingual-preview", response_model=BilingualPreviewResponse)
async def preview_bilingual_explanation_endpoint(
    payload: BilingualPreviewRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> BilingualPreviewResponse:
    """Preview bilingual STEM formatting, notation preservation, math-to-speech & fallbacks."""
    return await MultilingualService(db, settings).preview_bilingual_explanation(payload)


@languages_router.get("/translations", response_model=list[TranslationEntryOut])
async def list_translation_entries(
    target_language_code: str | None = None,
    status_filter: str | None = None,
    resource_type: str | None = None,
    caller: AuthenticatedUser = Depends(require_permissions("multilingual:read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> list[TranslationEntryOut]:
    """List translation entries and notation/terminology audit warnings."""
    _ = caller
    return await MultilingualService(db, settings).list_translations(
        target_language_code=target_language_code,
        status_filter=status_filter,
        resource_type=resource_type,
    )


@languages_router.post(
    "/translations",
    response_model=TranslationEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_translation_entry(
    payload: TranslationEntryCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("multilingual:translate")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> TranslationEntryOut:
    """Submit a translation with automated notation preservation & terminology QA checks."""
    return await MultilingualService(db, settings).submit_translation(payload, caller)


@languages_router.post(
    "/translations/{entry_id}/review",
    response_model=TranslationEntryOut,
)
async def review_translation_entry(
    entry_id: UUID,
    payload: TranslationReviewRequest,
    caller: AuthenticatedUser = Depends(require_permissions("multilingual:review")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> TranslationEntryOut:
    """Academic reviewer decision on a translation entry (enforces notation preservation gate)."""
    return await MultilingualService(db, settings).review_translation(entry_id, payload, caller)


@languages_router.get("/evaluations", response_model=list[LanguageQualityEvaluationOut])
async def list_language_quality_evaluations(
    language_code: str | None = None,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> list[LanguageQualityEvaluationOut]:
    """List empirical language quality evaluation history."""
    return await MultilingualService(db, settings).list_evaluations(
        language_code=language_code
    )


@languages_router.post(
    "/evaluations/run",
    response_model=LanguageQualityEvaluationOut,
    status_code=status.HTTP_201_CREATED,
)
async def run_language_quality_evaluation(
    payload: LanguageQualityRunRequest,
    caller: AuthenticatedUser = Depends(require_permissions("multilingual:review")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> LanguageQualityEvaluationOut:
    """Run deterministic script, math/science notation & terminology QA suite for a language."""
    return await MultilingualService(db, settings).run_quality_evaluation(payload, caller)


@voice_multilingual_router.get("/capabilities", response_model=VoiceProviderStatusOut)
async def get_voice_provider_capabilities(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> VoiceProviderStatusOut:
    """Return honest TTS & STT provider configuration status and verified languages."""
    return await MultilingualService(db, settings).get_voice_provider_status()


@voice_multilingual_router.post("/stt", response_model=STTResponseOut)
async def transcribe_voice_stt(
    payload: STTRequestBody,
    caller: AuthenticatedUser = Depends(require_permissions("voice:tts")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(_get_runtime_settings),  # noqa: B008
) -> STTResponseOut:
    """Capability-gated Speech-to-Text endpoint with transparent fallback diagnostics."""
    return await MultilingualService(db, settings).transcribe_stt(payload, caller)
