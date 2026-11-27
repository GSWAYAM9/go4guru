"use client";

import type {
  GlossaryTermOut,
  LanguageQualityEvaluationOut,
  TranslationEntryOut,
  VoiceProviderStatusOut,
} from "@go4guru/contracts";
import { LoadingCard } from "@go4guru/ui";
import { useCallback, useEffect, useState } from "react";
import { BilingualNotationLabTab } from "@/components/languages/BilingualNotationLabTab";
import { CapabilityRegistryTab } from "@/components/languages/CapabilityRegistryTab";
import { GlossaryTerminologyTab } from "@/components/languages/GlossaryTerminologyTab";
import {
  LanguageHubHeader,
  type LanguageStudioTab,
} from "@/components/languages/LanguageHubHeader";
import { PreferencesMatrixTab } from "@/components/languages/PreferencesMatrixTab";
import { TranslationReviewEvalTab } from "@/components/languages/TranslationReviewEvalTab";
import {
  fetchVoiceProviderCapabilities,
  listLanguageQualityEvaluations,
  listMultilingualGlossary,
  listTranslationEntries,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/language-context";

const FALLBACK_GLOSSARY_PREVIEW: GlossaryTermOut[] = [
  {
    id: "seed-hi-force",
    concept_key: "force",
    subject_area: "physics",
    english_term: "Force",
    language_code: "hi",
    localized_term: "बल",
    transliteration: "bal",
    preserve_english_in_bilingual: true,
    latex_symbol: "$F = ma$",
    review_status: "approved",
    notes: "NCERT Class 9/11 standard",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "seed-hi-accel",
    concept_key: "acceleration",
    subject_area: "physics",
    english_term: "Acceleration",
    language_code: "hi",
    localized_term: "त्वरण",
    transliteration: "tvaran",
    preserve_english_in_bilingual: true,
    latex_symbol: "$a = \\frac{dv}{dt}$",
    review_status: "approved",
    notes: "Keep SI unit m/s^2 intact",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "seed-ta-force",
    concept_key: "force",
    subject_area: "physics",
    english_term: "Force",
    language_code: "ta",
    localized_term: "விசை",
    transliteration: "visai",
    preserve_english_in_bilingual: true,
    latex_symbol: "$F = ma$",
    review_status: "approved",
    notes: "Tamil STEM glossary",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "seed-bn-derivative",
    concept_key: "derivative",
    subject_area: "mathematics",
    english_term: "Derivative",
    language_code: "bn",
    localized_term: "অবকলজ",
    transliteration: "obokoloj",
    preserve_english_in_bilingual: true,
    latex_symbol: "$\\frac{dy}{dx}$",
    review_status: "approved",
    notes: "Calculus terminology",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "seed-te-photosynthesis",
    concept_key: "photosynthesis",
    subject_area: "biology",
    english_term: "Photosynthesis",
    language_code: "te",
    localized_term: "కిరణజన్య సంయోగక్రియ",
    transliteration: "kiranajanya samyogakriya",
    preserve_english_in_bilingual: true,
    latex_symbol: "$6CO_2 + 6H_2O \\rightarrow C_6H_{12}O_6 + 6O_2$",
    review_status: "approved",
    notes: "NCERT Class 10/11 Biology",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "seed-ur-momentum",
    concept_key: "momentum",
    subject_area: "physics",
    english_term: "Momentum",
    language_code: "ur",
    localized_term: "مومینٹم",
    transliteration: "momentum",
    preserve_english_in_bilingual: true,
    latex_symbol: "$p = mv$",
    review_status: "approved",
    notes: "RTL prose with LTR math",
    created_at: "2026-01-01T00:00:00Z",
  },
];

export default function LanguagesStudioPage() {
  const { token } = useAuth();
  const { capabilities, registrySource, loadingRegistry, refreshCapabilities } =
    useLanguage();

  const [activeTab, setActiveTab] = useState<LanguageStudioTab>("preferences");
  const [voiceStatus, setVoiceStatus] = useState<VoiceProviderStatusOut | null>(
    null
  );
  const [glossaryTerms, setGlossaryTerms] = useState<GlossaryTermOut[]>(
    FALLBACK_GLOSSARY_PREVIEW
  );
  const [loadingGlossary, setLoadingGlossary] = useState(false);
  const [translations, setTranslations] = useState<TranslationEntryOut[]>([]);
  const [evaluations, setEvaluations] = useState<
    LanguageQualityEvaluationOut[]
  >([]);

  const loadAuxiliaryData = useCallback(async () => {
    setLoadingGlossary(true);
    try {
      const [voiceRes, glossaryRes, evalRes] = await Promise.allSettled([
        fetchVoiceProviderCapabilities(),
        listMultilingualGlossary(),
        listLanguageQualityEvaluations(),
      ]);

      if (voiceRes.status === "fulfilled") {
        setVoiceStatus(voiceRes.value);
      }
      if (glossaryRes.status === "fulfilled" && glossaryRes.value.length > 0) {
        setGlossaryTerms(glossaryRes.value);
      }
      if (evalRes.status === "fulfilled") {
        setEvaluations(evalRes.value);
      }
    } finally {
      setLoadingGlossary(false);
    }

    if (token) {
      try {
        const trans = await listTranslationEntries(token);
        setTranslations(trans);
      } catch {
        setTranslations([]);
      }
    } else {
      setTranslations([]);
    }
  }, [token]);

  useEffect(() => {
    void loadAuxiliaryData();
  }, [loadAuxiliaryData]);

  async function handleRefreshAll() {
    await Promise.all([refreshCapabilities(), loadAuxiliaryData()]);
  }

  return (
    <main id="main-content" className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="space-y-6">
        <LanguageHubHeader
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          capabilities={capabilities}
          registrySource={registrySource}
          voiceConfigured={voiceStatus?.elevenlabs_configured ?? null}
        />

        {loadingRegistry && capabilities.length === 0 ? (
          <LoadingCard message="Loading Language Capability Registry..." />
        ) : (
          <div className="pt-1">
            {activeTab === "preferences" && <PreferencesMatrixTab />}
            {activeTab === "registry" && (
              <CapabilityRegistryTab
                capabilities={capabilities}
                onRefresh={refreshCapabilities}
              />
            )}
            {activeTab === "bilingual" && (
              <BilingualNotationLabTab
                capabilities={capabilities}
                voiceStatus={voiceStatus}
              />
            )}
            {activeTab === "glossary" && (
              <GlossaryTerminologyTab
                capabilities={capabilities}
                terms={glossaryTerms}
                loading={loadingGlossary}
                onRefresh={loadAuxiliaryData}
              />
            )}
            {activeTab === "review" && (
              <TranslationReviewEvalTab
                capabilities={capabilities}
                translations={translations}
                evaluations={evaluations}
                onRefreshAll={handleRefreshAll}
              />
            )}
          </div>
        )}
      </div>
    </main>
  );
}
