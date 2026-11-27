"use client";

import type {
  BilingualMode,
  LanguageModalityKey,
} from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  useLanguage,
  type LanguagePreferencesState,
} from "@/lib/language-context";
import {
  formatBilingualModeLabel,
  getCapabilityStatusMeta,
  isModalitySupportedOnCapability,
} from "@/lib/multilingual-helpers";

interface ModalityConfig {
  key: LanguageModalityKey;
  prefField: keyof Omit<LanguagePreferencesState, "bilingual_explanation_mode">;
  labelKey: string;
  fallbackLabel: string;
  description: string;
}

const MODALITIES: ModalityConfig[] = [
  {
    key: "ui",
    prefField: "ui_language",
    labelKey: "lang.modality.ui",
    fallbackLabel: "Interface (UI) Language",
    description:
      "Navigation, labels, and layout direction (switches to RTL automatically for Urdu while keeping KaTeX math LTR).",
  },
  {
    key: "explanation",
    prefField: "preferred_explanation_language",
    labelKey: "lang.modality.explanation",
    fallbackLabel: "AI Explanation Language",
    description:
      "Language used by AI Tutor, Homework Coach, and Concept Mastery explanations.",
  },
  {
    key: "voice",
    prefField: "preferred_voice_language",
    labelKey: "lang.modality.voice",
    fallbackLabel: "Voice (TTS / STT) Language",
    description:
      "Spoken narration and speech recognition language; falls back cleanly to captions or verified voice if unsupported.",
  },
  {
    key: "subtitle",
    prefField: "preferred_subtitle_language",
    labelKey: "lang.modality.subtitle",
    fallbackLabel: "Subtitle / Caption Language",
    description:
      "Synchronized classroom captions and live transcript language — independent from audio voice.",
  },
  {
    key: "question",
    prefField: "preferred_question_language",
    labelKey: "lang.modality.question",
    fallbackLabel: "Question Bank Language",
    description:
      "Preferred language for practice and exam stems; requires academic review before serving translated questions.",
  },
  {
    key: "answer",
    prefField: "preferred_answer_language",
    labelKey: "lang.modality.answer",
    fallbackLabel: "Answer & Note Input Language",
    description:
      "Language you prefer when writing answers, homework steps, or study notes.",
  },
];

const BILINGUAL_MODES: Array<{
  id: BilingualMode;
  summary: string;
}> = [
  {
    id: "bilingual_stem_en",
    summary:
      "Explains concepts in your chosen language while keeping CBSE/JEE/NEET English STEM terms and LaTeX formulas intact.",
  },
  {
    id: "side_by_side",
    summary:
      "Displays localized explanation alongside an English reference block for exam vocabulary alignment.",
  },
  {
    id: "monolingual",
    summary:
      "Uses target script prose with protected mathematical equations, SI units, and chemical formulas.",
  },
];

export function PreferencesMatrixTab() {
  const { user } = useAuth();
  const {
    capabilities,
    preferences,
    resolutions,
    savingPreferences,
    isRtl,
    uiCoveragePct,
    savePreferences,
    t,
  } = useLanguage();

  const [draft, setDraft] = useState<LanguagePreferencesState>(preferences);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setDraft(preferences);
  }, [preferences]);

  // Keep draft synced when preferences load from storage/server on initial mount.
  const isDirty =
    draft.ui_language !== preferences.ui_language ||
    draft.preferred_explanation_language !==
      preferences.preferred_explanation_language ||
    draft.preferred_voice_language !== preferences.preferred_voice_language ||
    draft.preferred_subtitle_language !==
      preferences.preferred_subtitle_language ||
    draft.preferred_question_language !==
      preferences.preferred_question_language ||
    draft.preferred_answer_language !== preferences.preferred_answer_language ||
    draft.bilingual_explanation_mode !== preferences.bilingual_explanation_mode;

  async function applyDraft(next: LanguagePreferencesState) {
    setDraft(next);
    setStatusMessage(null);
    setErrorMessage(null);
    const result = await savePreferences(next);
    if (result.error) {
      setErrorMessage(result.error);
    } else if (result.persistedToServer) {
      setStatusMessage(
        "Preferences saved to your profile and applied live across the workspace."
      );
    } else {
      setStatusMessage(
        "Applied immediately in this browser. Sign in to sync across devices."
      );
    }
  }

  function handleQuickUiSwitch(code: string) {
    const next = { ...draft, ui_language: code };
    void applyDraft(next);
  }

  const activeFallbacks = MODALITIES.filter(
    (m) => resolutions[m.key]?.fallback_applied
  );

  return (
    <section className="space-y-8" aria-label="Independent 6-modality language preferences">
      {/* Live UI Quick Switch Bar */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Live UI Localization Preview
            </h2>
            <p className="text-xs text-slate-600">
              Switch interface language instantly to verify script rendering,
              per-key English fallback ({uiCoveragePct}% translated), and Urdu
              RTL direction ({isRtl ? "RTL active" : "LTR active"}).
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { code: "en", label: "English" },
              { code: "hi", label: "हिन्दी (hi)" },
              { code: "bn", label: "বাংলা (bn)" },
              { code: "ta", label: "தமிழ் (ta)" },
              { code: "te", label: "తెలుగు (te)" },
              { code: "ur", label: "اردو (ur · RTL)" },
            ].map((item) => {
              const active = preferences.ui_language === item.code;
              return (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => handleQuickUiSwitch(item.code)}
                  className={`whitespace-nowrap shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    active
                      ? "bg-indigo-700 text-white"
                      : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-100"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 6 Independent Modality Cards */}
      <div className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Six Independent Language Dimensions
            </h2>
            <p className="text-sm text-slate-600">
              Each dimension resolves independently against the empirical
              Language Capability Registry. Unsupported combinations trigger an
              explicit fallback instead of failing silently.
            </p>
          </div>
          <button
            type="button"
            disabled={savingPreferences}
            onClick={() => void applyDraft(draft)}
            className="whitespace-nowrap shrink-0 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:opacity-50"
          >
            {savingPreferences
              ? "Saving..."
              : `${t("languages.save_preferences", "Save Language Preferences")}${isDirty ? " •" : ""}`}
          </button>
        </div>

        {statusMessage && (
          <p
            role="status"
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900"
          >
            {statusMessage}
          </p>
        )}
        {errorMessage && (
          <p
            role="alert"
            className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-900"
          >
            {errorMessage}
          </p>
        )}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {MODALITIES.map((mod) => {
            const currentCode = draft[mod.prefField];
            const res = resolutions[mod.key];
            const selectedCap = capabilities.find(
              (c) => c.language_code === currentCode
            );
            const statusMeta = getCapabilityStatusMeta(
              selectedCap?.capability_status
            );

            return (
              <div
                key={mod.key}
                className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
              >
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <label
                      htmlFor={`modality-${mod.key}`}
                      className="text-sm font-semibold text-slate-900"
                    >
                      {t(mod.labelKey, mod.fallbackLabel)}
                    </label>
                    <StatusBadge
                      tone={res?.fallback_applied ? "degraded" : statusMeta.tone}
                    >
                      {res?.fallback_applied
                        ? `Fallback → ${res.effective_language.toUpperCase()}`
                        : statusMeta.label}
                    </StatusBadge>
                  </div>

                  <p className="text-xs leading-relaxed text-slate-600">
                    {mod.description}
                  </p>

                  <select
                    id={`modality-${mod.key}`}
                    value={currentCode}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        [mod.prefField]: e.target.value,
                      }))
                    }
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
                  >
                    {capabilities.map((cap) => {
                      const supported = isModalitySupportedOnCapability(
                        cap,
                        mod.key
                      );
                      return (
                        <option
                          key={cap.language_code}
                          value={cap.language_code}
                        >
                          {cap.display_name} — {cap.native_name} (
                          {cap.language_code})
                          {supported ? "" : " [Fallback Required]"}
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div className="mt-3 border-t border-slate-100 pt-2.5 text-xs text-slate-600">
                  {res?.fallback_applied ? (
                    <p className="text-amber-800">{res.fallback_reason}</p>
                  ) : (
                    <p>
                      Effective:{" "}
                      <span className="font-medium text-slate-900">
                        {res?.effective_language.toUpperCase()}
                      </span>{" "}
                      · Provider:{" "}
                      <span className="font-medium text-slate-800">
                        {res?.provider || "Built-in catalog"}
                      </span>
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bilingual STEM Mode */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Bilingual STEM Terminology Strategy
          </h3>
          <p className="text-xs text-slate-600">
            Choose how technical physics, chemistry, biology, and mathematics
            terms appear alongside localized explanations.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {BILINGUAL_MODES.map((m) => {
            const active = draft.bilingual_explanation_mode === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() =>
                  setDraft((prev) => ({
                    ...prev,
                    bilingual_explanation_mode: m.id,
                  }))
                }
                className={`rounded-lg border p-3.5 text-left transition ${
                  active
                    ? "border-indigo-600 bg-indigo-50/60"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                }`}
              >
                <div className="text-sm font-semibold text-slate-900">
                  {formatBilingualModeLabel(m.id)}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {m.summary}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Fallback Audit Panel */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-5 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-900">
            Deterministic Language Fallback Diagnostics
          </h3>
          <span className="text-xs text-slate-500">
            {user ? `Profile sync: ${user.email}` : "Guest preview (local browser state)"}
          </span>
        </div>
        {activeFallbacks.length === 0 ? (
          <p className="text-xs text-emerald-800">
            All 6 selected modalities are directly supported for your active
            languages without fallback.
          </p>
        ) : (
          <ul className="space-y-1.5 text-xs text-amber-900">
            {activeFallbacks.map((m) => (
              <li key={m.key}>
                <strong className="font-semibold">{m.fallbackLabel}:</strong>{" "}
                {resolutions[m.key]?.fallback_reason}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
