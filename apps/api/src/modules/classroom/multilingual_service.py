"""Phase 10 Multilingual Learning Service (Registry, 6-Dimension Prefs, Glossary, Review & QA)."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.config import Settings
from src.core.errors import AppError
from src.modules.classroom.models import LanguageCapability
from src.modules.classroom.multilingual_logic import (
    GlossaryTermEntry,
    LanguageCapabilityRecord,
    LanguageEvaluationSample,
    ModalityResolution,
    audit_terminology_consistency,
    build_bilingual_explanation,
    get_ui_localization_bundle,
    resolve_all_six_preferences,
    resolve_language_for_modality,
    run_language_quality_suite,
    verify_notation_preservation,
)
from src.modules.classroom.multilingual_models import (
    LanguageQualityEvaluation,
    MultilingualGlossaryTerm,
    TranslationEntry,
)
from src.modules.classroom.multilingual_schemas import (
    BilingualPreviewRequest,
    BilingualPreviewResponse,
    GlossaryTermCreateRequest,
    GlossaryTermOut,
    LanguageCapabilityDetailOut,
    LanguageCapabilityPatchRequest,
    LanguageQualityEvaluationOut,
    LanguageQualityRunRequest,
    ModalityResolutionOut,
    NotationPreservationOut,
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
from src.modules.classroom.voice.provider import (
    ElevenLabsVoiceAdapter,
    log_stt_usage,
    normalize_math_for_speech,
)
from src.modules.identity.public import (
    get_user_language_preferences,
    update_user_language_preferences,
)

_EVAL_BASELINE_SAMPLES: tuple[tuple[str, str], ...] = (
    (
        "kinematics-equation",
        "Under constant acceleration, velocity satisfies $v^2 = u^2 + 2as$ with $g = 9.8 m/s^2$.",
    ),
    (
        "chemistry-stoichiometry",
        "Neutralization of H2SO4 with NaOH yields Na2SO4 and H2O: 2NaOH + H2SO4 -> Na2SO4 + 2H2O.",
    ),
    (
        "quadratic-formula",
        "For any quadratic equation $ax^2 + bx + c = 0$, the discriminant is $\\Delta = b^2 - 4ac$.",
    ),
)


class MultilingualService:
    """Authoritative multilingual capability, preference, glossary, review & QA service."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.voice_adapter = ElevenLabsVoiceAdapter(settings)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_record(row: LanguageCapability) -> LanguageCapabilityRecord:
        return LanguageCapabilityRecord(
            language_code=row.language_code,
            display_name=row.display_name,
            native_name=row.native_name,
            script_name=row.script_name,
            rtl=row.rtl,
            capability_status=row.capability_status,
            testing_status=row.testing_status,
            availability_status=row.availability_status,
            text_quality_tier=row.text_quality_tier,
            translation_status=row.translation_status,
            ui_supported=row.ui_supported,
            explanation_supported=row.explanation_supported,
            bilingual_supported=row.bilingual_supported,
            tts_supported=row.tts_supported,
            stt_supported=row.stt_supported,
            subtitle_supported=row.subtitle_supported,
            question_supported=row.question_supported,
            answer_supported=row.answer_supported,
            voice_provider=row.voice_provider,
            stt_provider=row.stt_provider,
            translation_provider=row.translation_provider,
            pronunciation_tier=row.pronunciation_tier,
            academic_review_status=row.academic_review_status,
            fallback_language_code=row.fallback_language_code,
            quality_score_pct=row.quality_score_pct,
            known_limitations=row.known_limitations,
            provider_matrix=dict(row.provider_matrix_jsonb or {}),
        )

    @staticmethod
    def _to_capability_out(row: LanguageCapability) -> LanguageCapabilityDetailOut:
        return LanguageCapabilityDetailOut(
            language_code=row.language_code,
            display_name=row.display_name,
            native_name=row.native_name,
            script_name=row.script_name,
            rtl=row.rtl,
            capability_status=row.capability_status,
            testing_status=row.testing_status,
            availability_status=row.availability_status,
            text_quality_tier=row.text_quality_tier,
            translation_status=row.translation_status,
            ui_supported=row.ui_supported,
            explanation_supported=row.explanation_supported,
            bilingual_supported=row.bilingual_supported,
            tts_supported=row.tts_supported,
            stt_supported=row.stt_supported,
            voice_provider=row.voice_provider,
            stt_provider=row.stt_provider,
            translation_provider=row.translation_provider,
            pronunciation_tier=row.pronunciation_tier,
            subtitle_supported=row.subtitle_supported,
            question_supported=row.question_supported,
            answer_supported=row.answer_supported,
            academic_review_status=row.academic_review_status,
            fallback_language_code=row.fallback_language_code,
            quality_score_pct=row.quality_score_pct,
            last_evaluated_at=row.last_evaluated_at,
            provider_matrix=dict(row.provider_matrix_jsonb or {}),
            known_limitations=row.known_limitations,
        )

    @staticmethod
    def _to_resolution_out(res: ModalityResolution) -> ModalityResolutionOut:
        return ModalityResolutionOut(
            modality=res.modality,
            requested_language=res.requested_language,
            effective_language=res.effective_language,
            fallback_applied=res.fallback_applied,
            fallback_reason=res.fallback_reason,
            capability_status=res.capability_status,
            availability_status=res.availability_status,
            testing_status=res.testing_status,
            rtl=res.rtl,
            provider=res.provider,
        )

    async def _load_capability_map(self) -> dict[str, LanguageCapabilityRecord]:
        rows = (await self.db.scalars(select(LanguageCapability))).all()
        return {r.language_code: self._to_record(r) for r in rows}

    async def _load_glossary_entries(
        self, language_code: str | None = None
    ) -> list[GlossaryTermEntry]:
        stmt = select(MultilingualGlossaryTerm)
        if language_code:
            stmt = stmt.where(MultilingualGlossaryTerm.language_code == language_code)
        rows = (await self.db.scalars(stmt)).all()
        return [
            GlossaryTermEntry(
                concept_key=r.concept_key,
                subject_area=r.subject_area,
                english_term=r.english_term,
                language_code=r.language_code,
                localized_term=r.localized_term,
                transliteration=r.transliteration,
                preserve_english_in_bilingual=r.preserve_english_in_bilingual,
                latex_symbol=r.latex_symbol,
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Language Capability Registry
    # ------------------------------------------------------------------
    async def list_capabilities(
        self,
        *,
        capability_status: str | None = None,
        tts_only: bool = False,
    ) -> list[LanguageCapabilityDetailOut]:
        stmt = select(LanguageCapability)
        if capability_status:
            stmt = stmt.where(LanguageCapability.capability_status == capability_status)
        if tts_only:
            stmt = stmt.where(LanguageCapability.tts_supported.is_(True))
        stmt = stmt.order_by(
            LanguageCapability.tts_supported.desc(),
            LanguageCapability.ui_supported.desc(),
            LanguageCapability.language_code.asc(),
        )
        rows = (await self.db.scalars(stmt)).all()
        return [self._to_capability_out(r) for r in rows]

    async def patch_capability(
        self,
        language_code: str,
        payload: LanguageCapabilityPatchRequest,
        caller: AuthenticatedUser,
    ) -> LanguageCapabilityDetailOut:
        _ = caller
        code = language_code.strip().lower()
        row = await self.db.get(LanguageCapability, code)
        if row is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LANGUAGE_NOT_FOUND",
                message=f"Language '{code}' is not in the Language Capability Registry.",
            )
        updates = payload.model_dump(exclude_unset=True)
        if "provider_matrix" in updates and updates["provider_matrix"] is not None:
            row.provider_matrix_jsonb = dict(updates.pop("provider_matrix"))
        for field, val in updates.items():
            setattr(row, field, val)
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_capability_out(row)

    # ------------------------------------------------------------------
    # 6 Independent User Language Preferences & Fallback Resolution
    # ------------------------------------------------------------------
    async def get_my_preferences(self, caller: AuthenticatedUser) -> UserLanguagePreferencesOut:
        prefs = await get_user_language_preferences(self.db, caller.id)
        cap_map = await self._load_capability_map()
        resolved = resolve_all_six_preferences(
            ui_language=prefs.ui_language,
            explanation_language=prefs.preferred_explanation_language,
            voice_language=prefs.preferred_voice_language,
            subtitle_language=prefs.preferred_subtitle_language,
            question_language=prefs.preferred_question_language,
            answer_language=prefs.preferred_answer_language,
            capabilities_by_code=cap_map,
        )
        return UserLanguagePreferencesOut(
            ui_language=prefs.ui_language,
            preferred_explanation_language=prefs.preferred_explanation_language,
            preferred_voice_language=prefs.preferred_voice_language,
            preferred_subtitle_language=prefs.preferred_subtitle_language,
            preferred_question_language=prefs.preferred_question_language,
            preferred_answer_language=prefs.preferred_answer_language,
            bilingual_explanation_mode=prefs.bilingual_explanation_mode,
            resolutions={k: self._to_resolution_out(v) for k, v in resolved.items()},
        )

    async def update_my_preferences(
        self,
        payload: UserLanguagePreferencesUpdateRequest,
        caller: AuthenticatedUser,
    ) -> UserLanguagePreferencesOut:
        cap_map = await self._load_capability_map()
        lang_fields = (
            "ui_language",
            "preferred_explanation_language",
            "preferred_voice_language",
            "preferred_subtitle_language",
            "preferred_question_language",
            "preferred_answer_language",
        )
        cleaned: dict[str, str | None] = {}
        raw = payload.model_dump(exclude_unset=True)
        for field in lang_fields:
            val = raw.get(field)
            if val is not None:
                norm = val.strip().lower()
                if cap_map and norm not in cap_map:
                    raise AppError(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        code="UNREGISTERED_LANGUAGE",
                        message=(
                            f"Language '{norm}' for '{field}' is not registered in the "
                            "Language Capability Registry."
                        ),
                    )
                cleaned[field] = norm

        prefs = await update_user_language_preferences(
            self.db,
            caller.id,
            ui_language=cleaned.get("ui_language"),
            preferred_explanation_language=cleaned.get("preferred_explanation_language"),
            preferred_voice_language=cleaned.get("preferred_voice_language"),
            preferred_subtitle_language=cleaned.get("preferred_subtitle_language"),
            preferred_question_language=cleaned.get("preferred_question_language"),
            preferred_answer_language=cleaned.get("preferred_answer_language"),
            bilingual_explanation_mode=raw.get("bilingual_explanation_mode"),
        )
        await self.db.commit()
        resolved = resolve_all_six_preferences(
            ui_language=prefs.ui_language,
            explanation_language=prefs.preferred_explanation_language,
            voice_language=prefs.preferred_voice_language,
            subtitle_language=prefs.preferred_subtitle_language,
            question_language=prefs.preferred_question_language,
            answer_language=prefs.preferred_answer_language,
            capabilities_by_code=cap_map,
        )
        return UserLanguagePreferencesOut(
            ui_language=prefs.ui_language,
            preferred_explanation_language=prefs.preferred_explanation_language,
            preferred_voice_language=prefs.preferred_voice_language,
            preferred_subtitle_language=prefs.preferred_subtitle_language,
            preferred_question_language=prefs.preferred_question_language,
            preferred_answer_language=prefs.preferred_answer_language,
            bilingual_explanation_mode=prefs.bilingual_explanation_mode,
            resolutions={k: self._to_resolution_out(v) for k, v in resolved.items()},
        )

    # ------------------------------------------------------------------
    # UI Localization Bundle (Merged with Approved DB Translation Entries)
    # ------------------------------------------------------------------
    async def get_ui_bundle(self, language_code: str) -> UiLocalizationBundleOut:
        code = language_code.strip().lower()
        bundle = get_ui_localization_bundle(code)
        # Overlay any approved ui_string translations from DB
        approved_rows = (
            await self.db.scalars(
                select(TranslationEntry).where(
                    TranslationEntry.resource_type == "ui_string",
                    TranslationEntry.target_language_code == code,
                    TranslationEntry.status == "approved",
                )
            )
        ).all()
        strings = dict(bundle["strings"])
        fallback_set = set(bundle["fallback_keys"])
        for row in approved_rows:
            if row.translated_text.strip():
                strings[row.resource_key] = row.translated_text.strip()
                fallback_set.discard(row.resource_key)

        total = len(strings)
        translated = max(0, total - len(fallback_set))
        return UiLocalizationBundleOut(
            requested_language=code,
            effective_language=bundle["effective_language"],
            rtl=bundle["rtl"],
            coverage_pct=round((translated / max(1, total)) * 100.0, 1),
            translated_key_count=translated,
            total_key_count=total,
            fallback_keys=sorted(fallback_set),
            strings=strings,
        )

    # ------------------------------------------------------------------
    # STEM Terminology Glossary
    # ------------------------------------------------------------------
    async def list_glossary(
        self,
        *,
        language_code: str | None = None,
        subject_area: str | None = None,
        query: str | None = None,
    ) -> list[GlossaryTermOut]:
        stmt = select(MultilingualGlossaryTerm)
        if language_code:
            stmt = stmt.where(
                MultilingualGlossaryTerm.language_code == language_code.strip().lower()
            )
        if subject_area:
            stmt = stmt.where(MultilingualGlossaryTerm.subject_area == subject_area.strip())
        stmt = stmt.order_by(
            MultilingualGlossaryTerm.subject_area.asc(),
            MultilingualGlossaryTerm.english_term.asc(),
            MultilingualGlossaryTerm.language_code.asc(),
        )
        rows = (await self.db.scalars(stmt)).all()
        q = (query or "").strip().lower()
        if q:
            rows = [
                r
                for r in rows
                if q in r.english_term.lower()
                or q in r.localized_term.lower()
                or q in r.concept_key.lower()
                or (r.transliteration and q in r.transliteration.lower())
            ]
        return [
            GlossaryTermOut(
                id=r.id,
                concept_key=r.concept_key,
                subject_area=r.subject_area,
                english_term=r.english_term,
                language_code=r.language_code,
                localized_term=r.localized_term,
                transliteration=r.transliteration,
                preserve_english_in_bilingual=r.preserve_english_in_bilingual,
                latex_symbol=r.latex_symbol,
                review_status=r.review_status,
                notes=r.notes,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def upsert_glossary_term(
        self,
        payload: GlossaryTermCreateRequest,
        caller: AuthenticatedUser,
    ) -> GlossaryTermOut:
        code = payload.language_code.strip().lower()
        cap = await self.db.get(LanguageCapability, code)
        if cap is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="UNREGISTERED_LANGUAGE",
                message=f"Language '{code}' is not registered in Language Capability Registry.",
            )
        existing = await self.db.scalar(
            select(MultilingualGlossaryTerm).where(
                MultilingualGlossaryTerm.concept_key == payload.concept_key.strip(),
                MultilingualGlossaryTerm.language_code == code,
            )
        )
        is_reviewer = "multilingual:review" in caller.permissions or "platform_admin" in caller.roles
        review_state = "approved" if is_reviewer else "in_review"
        now = datetime.now(UTC)

        if existing is not None:
            existing.subject_area = payload.subject_area.strip()
            existing.english_term = payload.english_term.strip()
            existing.localized_term = payload.localized_term.strip()
            existing.transliteration = payload.transliteration
            existing.preserve_english_in_bilingual = payload.preserve_english_in_bilingual
            existing.latex_symbol = payload.latex_symbol
            existing.notes = payload.notes
            existing.review_status = review_state
            if is_reviewer:
                existing.reviewed_by = caller.id
                existing.reviewed_at = now
            row = existing
        else:
            row = MultilingualGlossaryTerm(
                concept_key=payload.concept_key.strip(),
                subject_area=payload.subject_area.strip(),
                english_term=payload.english_term.strip(),
                language_code=code,
                localized_term=payload.localized_term.strip(),
                transliteration=payload.transliteration,
                preserve_english_in_bilingual=payload.preserve_english_in_bilingual,
                latex_symbol=payload.latex_symbol,
                review_status=review_state,
                reviewed_by=caller.id if is_reviewer else None,
                reviewed_at=now if is_reviewer else None,
                notes=payload.notes,
            )
            self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return GlossaryTermOut(
            id=row.id,
            concept_key=row.concept_key,
            subject_area=row.subject_area,
            english_term=row.english_term,
            language_code=row.language_code,
            localized_term=row.localized_term,
            transliteration=row.transliteration,
            preserve_english_in_bilingual=row.preserve_english_in_bilingual,
            latex_symbol=row.latex_symbol,
            review_status=row.review_status,
            notes=row.notes,
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # Bilingual Explanation & Notation Preservation Lab
    # ------------------------------------------------------------------
    async def preview_bilingual_explanation(
        self, payload: BilingualPreviewRequest
    ) -> BilingualPreviewResponse:
        cap_map = await self._load_capability_map()
        exp_res = resolve_language_for_modality(
            payload.explanation_language, "explanation", cap_map
        )
        sub_res = resolve_language_for_modality(payload.subtitle_language, "subtitle", cap_map)
        voice_res = resolve_language_for_modality(payload.voice_language, "voice", cap_map)

        glossary = await self._load_glossary_entries(exp_res.effective_language)
        preview = build_bilingual_explanation(
            source_text=payload.source_text,
            target_language_code=exp_res.effective_language,
            bilingual_mode=payload.bilingual_mode,
            glossary_terms=glossary,
        )
        rep = preview.notation_report
        speakable = normalize_math_for_speech(payload.source_text)
        return BilingualPreviewResponse(
            rendered_text=preview.rendered_text,
            bilingual_mode=preview.bilingual_mode,
            explanation_resolution=self._to_resolution_out(exp_res),
            subtitle_resolution=self._to_resolution_out(sub_res),
            voice_resolution=self._to_resolution_out(voice_res),
            speakable_math_text=speakable,
            notation_report=NotationPreservationOut(
                math_preserved=rep.math_preserved,
                science_preserved=rep.science_preserved,
                all_preserved=rep.all_preserved,
                math_preservation_score=rep.math_preservation_score,
                science_notation_score=rep.science_notation_score,
                math_expressions=list(rep.source_notations.math_expressions),
                scientific_notations=list(rep.source_notations.scientific_notations),
                si_unit_values=list(rep.source_notations.si_unit_values),
                chemical_formulas=list(rep.source_notations.chemical_formulas),
                missing_math=list(rep.missing_math),
                missing_science=list(rep.missing_science),
            ),
            matched_glossary_terms=[
                {
                    "concept_key": t.concept_key,
                    "subject_area": t.subject_area,
                    "english_term": t.english_term,
                    "localized_term": t.localized_term,
                    "transliteration": t.transliteration,
                    "latex_symbol": t.latex_symbol,
                }
                for t in preview.matched_terms
            ],
            tts_provider_configured=self.voice_adapter.is_configured(),
            stt_provider_configured=self.voice_adapter.is_configured(),
        )

    # ------------------------------------------------------------------
    # Translation Infrastructure & Review Workflow
    # ------------------------------------------------------------------
    async def list_translations(
        self,
        *,
        target_language_code: str | None = None,
        status_filter: str | None = None,
        resource_type: str | None = None,
    ) -> list[TranslationEntryOut]:
        stmt = select(TranslationEntry)
        if target_language_code:
            stmt = stmt.where(
                TranslationEntry.target_language_code == target_language_code.strip().lower()
            )
        if status_filter:
            stmt = stmt.where(TranslationEntry.status == status_filter.strip())
        if resource_type:
            stmt = stmt.where(TranslationEntry.resource_type == resource_type.strip())
        stmt = stmt.order_by(TranslationEntry.updated_at.desc()).limit(100)
        rows = (await self.db.scalars(stmt)).all()
        return [self._to_translation_out(r) for r in rows]

    async def submit_translation(
        self,
        payload: TranslationEntryCreateRequest,
        caller: AuthenticatedUser,
    ) -> TranslationEntryOut:
        code = payload.target_language_code.strip().lower()
        cap = await self.db.get(LanguageCapability, code)
        if cap is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="UNREGISTERED_LANGUAGE",
                message=f"Target language '{code}' is not in the Language Capability Registry.",
            )

        notations = verify_notation_preservation(payload.source_text, payload.translated_text)
        glossary = await self._load_glossary_entries(code)
        term_score, term_warnings = audit_terminology_consistency(
            source_text=payload.source_text,
            translated_text=payload.translated_text,
            target_language_code=code,
            glossary_terms=glossary,
        )
        warnings = list(term_warnings)
        if notations.missing_math:
            warnings.append(f"Missing LaTeX math: {', '.join(notations.missing_math)}")
        if notations.missing_science:
            warnings.append(f"Missing science/SI notation: {', '.join(notations.missing_science)}")

        quality = round(
            (notations.math_preservation_score * 0.45)
            + (notations.science_notation_score * 0.35)
            + (term_score * 0.20),
            2,
        )
        initial_status = "in_review" if notations.all_preserved else "needs_revision"

        existing = await self.db.scalar(
            select(TranslationEntry).where(
                TranslationEntry.resource_type == payload.resource_type,
                TranslationEntry.resource_key == payload.resource_key.strip(),
                TranslationEntry.target_language_code == code,
            )
        )
        if existing is not None:
            existing.source_language_code = payload.source_language_code.strip().lower()
            existing.source_text = payload.source_text
            existing.translated_text = payload.translated_text
            existing.bilingual_text = payload.bilingual_text
            existing.notation_preserved = notations.all_preserved
            existing.terminology_warnings_jsonb = warnings
            existing.status = initial_status
            existing.quality_score = quality
            existing.created_by = caller.id
            row = existing
        else:
            row = TranslationEntry(
                resource_type=payload.resource_type,
                resource_key=payload.resource_key.strip(),
                source_language_code=payload.source_language_code.strip().lower(),
                target_language_code=code,
                source_text=payload.source_text,
                translated_text=payload.translated_text,
                bilingual_text=payload.bilingual_text,
                notation_preserved=notations.all_preserved,
                terminology_warnings_jsonb=warnings,
                status=initial_status,
                quality_score=quality,
                created_by=caller.id,
            )
            self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_translation_out(row)

    async def review_translation(
        self,
        entry_id: UUID,
        payload: TranslationReviewRequest,
        caller: AuthenticatedUser,
    ) -> TranslationEntryOut:
        row = await self.db.get(TranslationEntry, entry_id)
        if row is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="TRANSLATION_NOT_FOUND",
                message="Translation entry not found.",
            )
        if payload.decision == "approved" and not row.notation_preserved:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="NOTATION_PRESERVATION_REQUIRED",
                message=(
                    "Cannot approve a translation with corrupted or missing mathematical/"
                    "scientific notation; request revision first."
                ),
            )
        row.status = payload.decision
        row.reviewed_by = caller.id
        row.reviewer_notes = payload.reviewer_notes
        row.reviewed_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_translation_out(row)

    @staticmethod
    def _to_translation_out(row: TranslationEntry) -> TranslationEntryOut:
        return TranslationEntryOut(
            id=row.id,
            resource_type=row.resource_type,
            resource_key=row.resource_key,
            source_language_code=row.source_language_code,
            target_language_code=row.target_language_code,
            source_text=row.source_text,
            translated_text=row.translated_text,
            bilingual_text=row.bilingual_text,
            notation_preserved=row.notation_preserved,
            terminology_warnings=list(row.terminology_warnings_jsonb or []),
            status=row.status,
            quality_score=row.quality_score,
            reviewer_notes=row.reviewer_notes,
            reviewed_at=row.reviewed_at,
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # Language Quality Evaluation Suites
    # ------------------------------------------------------------------
    async def list_evaluations(
        self, *, language_code: str | None = None
    ) -> list[LanguageQualityEvaluationOut]:
        stmt = select(LanguageQualityEvaluation)
        if language_code:
            stmt = stmt.where(
                LanguageQualityEvaluation.language_code == language_code.strip().lower()
            )
        stmt = stmt.order_by(LanguageQualityEvaluation.evaluated_at.desc()).limit(60)
        rows = (await self.db.scalars(stmt)).all()
        return [self._to_eval_out(r) for r in rows]

    async def run_quality_evaluation(
        self,
        payload: LanguageQualityRunRequest,
        caller: AuthenticatedUser,
    ) -> LanguageQualityEvaluationOut:
        code = payload.language_code.strip().lower()
        cap_row = await self.db.get(LanguageCapability, code)
        if cap_row is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LANGUAGE_NOT_FOUND",
                message=f"Language '{code}' is not in the Language Capability Registry.",
            )
        cap_rec = self._to_record(cap_row)
        glossary = await self._load_glossary_entries(code)

        if payload.samples:
            samples = [
                LanguageEvaluationSample(
                    sample_id=s.sample_id,
                    source_text=s.source_text,
                    candidate_text=s.candidate_text,
                )
                for s in payload.samples
            ]
        else:
            # Generate deterministic bilingual benchmark samples for this language
            samples = []
            for sid, src_text in _EVAL_BASELINE_SAMPLES:
                rendered = build_bilingual_explanation(
                    source_text=src_text,
                    target_language_code=code,
                    bilingual_mode="bilingual_stem_en",
                    glossary_terms=glossary,
                ).rendered_text
                samples.append(
                    LanguageEvaluationSample(
                        sample_id=sid,
                        source_text=src_text,
                        candidate_text=rendered,
                    )
                )

        result = run_language_quality_suite(
            capability=cap_rec,
            modality=payload.modality,
            samples=samples,
            glossary_terms=glossary,
        )
        now = datetime.now(UTC)
        eval_row = LanguageQualityEvaluation(
            language_code=code,
            modality=payload.modality,
            provider_name=payload.provider_name,
            test_suite_version="phase10-v1",
            script_fidelity_score=result.script_fidelity_score,
            math_preservation_score=result.math_preservation_score,
            science_notation_score=result.science_notation_score,
            terminology_accuracy_score=result.terminology_accuracy_score,
            fluency_score=result.fluency_score,
            overall_score=result.overall_score,
            passed=result.passed,
            sample_count=result.sample_count,
            findings_jsonb=list(result.findings),
            evaluated_by=caller.id,
            evaluated_at=now,
        )
        self.db.add(eval_row)

        # Update honest registry evaluation metadata
        cap_row.quality_score_pct = result.overall_score
        cap_row.last_evaluated_at = now
        if result.passed and cap_row.testing_status == "pending":
            cap_row.testing_status = "partial"
        elif not result.passed:
            cap_row.testing_status = "failed"

        await self.db.commit()
        await self.db.refresh(eval_row)
        return self._to_eval_out(eval_row)

    @staticmethod
    def _to_eval_out(row: LanguageQualityEvaluation) -> LanguageQualityEvaluationOut:
        return LanguageQualityEvaluationOut(
            id=row.id,
            language_code=row.language_code,
            modality=row.modality,
            provider_name=row.provider_name,
            test_suite_version=row.test_suite_version,
            script_fidelity_score=row.script_fidelity_score,
            math_preservation_score=row.math_preservation_score,
            science_notation_score=row.science_notation_score,
            terminology_accuracy_score=row.terminology_accuracy_score,
            fluency_score=row.fluency_score,
            overall_score=row.overall_score,
            passed=row.passed,
            sample_count=row.sample_count,
            findings=list(row.findings_jsonb or []),
            evaluated_at=row.evaluated_at,
        )

    # ------------------------------------------------------------------
    # Speech-to-Text (STT) Capability & Voice Provider Truthful Status
    # ------------------------------------------------------------------
    async def get_voice_provider_status(self) -> VoiceProviderStatusOut:
        rows = (await self.db.scalars(select(LanguageCapability))).all()
        tts_langs = sorted([r.language_code for r in rows if r.tts_supported])
        stt_langs = sorted([r.language_code for r in rows if r.stt_supported])
        configured = self.voice_adapter.is_configured()
        notice = (
            "ElevenLabs TTS and Scribe STT credentials are active for verified languages only; "
            "unverified languages degrade to synchronized subtitles and text input."
            if configured
            else (
                "ELEVENLABS_API_KEY is not configured; live cloud TTS/STT audio is inactive and "
                "all sessions transparently degrade to timed subtitles and keyboard/Web Speech input."
            )
        )
        return VoiceProviderStatusOut(
            elevenlabs_configured=configured,
            tts_model_id=self.voice_adapter.model_id,
            stt_model_id="scribe_v1",
            verified_tts_languages=tts_langs,
            verified_stt_languages=stt_langs,
            honest_status_notice=notice,
        )

    async def transcribe_stt(
        self, payload: STTRequestBody, caller: AuthenticatedUser
    ) -> STTResponseOut:
        cap_map = await self._load_capability_map()
        req_lang = payload.language_code.strip().lower()
        cap = cap_map.get(req_lang)

        if cap is None or not cap.stt_supported:
            fallback_lang = "en"
            reason = (
                f"Speech-to-Text is not verified/enabled for '{req_lang}' in the Language "
                "Capability Registry; falling back to English STT capability or keyboard input."
            )
            if payload.browser_transcript_hint and payload.browser_transcript_hint.strip():
                return STTResponseOut(
                    stt_available=True,
                    transcript=payload.browser_transcript_hint.strip(),
                    confidence=0.65,
                    requested_language=req_lang,
                    effective_language=req_lang,
                    fallback_applied=True,
                    provider="browser_web_speech_unverified",
                    latency_ms=0,
                    audio_seconds=0.0,
                    is_fallback=True,
                    fallback_mode="browser_speech_recognition",
                    limitation_notice=reason,
                )
            return STTResponseOut(
                stt_available=False,
                transcript=None,
                confidence=None,
                requested_language=req_lang,
                effective_language=fallback_lang,
                fallback_applied=True,
                provider="language_capability_registry",
                latency_ms=0,
                audio_seconds=0.0,
                is_fallback=True,
                fallback_mode="text_input_required",
                limitation_notice=reason,
            )

        audio_bytes: bytes | None = None
        if payload.audio_base64:
            try:
                audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
            except Exception as exc:
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    code="INVALID_AUDIO_ENCODING",
                    message="audio_base64 must be valid base64-encoded audio bytes.",
                ) from exc

        res = await self.voice_adapter.transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=payload.mime_type,
            language_code=req_lang,
            browser_transcript_hint=payload.browser_transcript_hint,
        )
        await log_stt_usage(
            self.db,
            user_id=caller.id,
            classroom_session_id=payload.classroom_session_id,
            res=res,
        )
        await self.db.commit()
        return STTResponseOut(
            stt_available=res.stt_available,
            transcript=res.transcript,
            confidence=res.confidence,
            requested_language=req_lang,
            effective_language=res.language_code,
            fallback_applied=res.is_fallback,
            provider=res.provider,
            latency_ms=res.latency_ms,
            audio_seconds=res.audio_seconds,
            is_fallback=res.is_fallback,
            fallback_mode=res.fallback_mode,
            limitation_notice=res.limitation_notice,
        )
