"use client";

import type {
  BilingualMode,
  BilingualPreviewResponse,
  LanguageCapabilityOut,
  STTResponseOut,
  VoiceProviderStatusOut,
} from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import { useState } from "react";
import { MathText } from "@/components/math-text";
import {
  previewBilingualExplanation,
  transcribeVoiceStt,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/language-context";
import {
  resolveModalityFallbackClient,
  verifyClientNotationPreservation,
} from "@/lib/multilingual-helpers";

interface BilingualNotationLabTabProps {
  capabilities: LanguageCapabilityOut[];
  voiceStatus: VoiceProviderStatusOut | null;
}

const STEM_SAMPLES = [
  {
    id: "physics",
    label: "Physics · Kinematics & Force",
    text: "By Newton's Second Law, force equals mass times acceleration: $F = ma$. With Earth's gravity 9.8 m/s^2, kinetic energy is $K = \\frac{1}{2}mv^2$ and momentum is $p = mv$.",
  },
  {
    id: "chemistry",
    label: "Chemistry · Stoichiometry & Avogadro",
    text: "In a balanced oxidation reaction $2H_2 + O_2 \\rightarrow 2H_2O$ (2H2 + O2 -> 2H2O), 1 mol contains 6.022 × 10^23 mol^-1 molecules and neutralization of H2SO4 with NaOH yields NaCl-type salts.",
  },
  {
    id: "math",
    label: "Mathematics · Calculus & Quadratic",
    text: "The derivative of $f(x) = x^2 + 3x$ is $\\frac{df}{dx} = 2x + 3$, and roots of $ax^2 + bx + c = 0$ satisfy $$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$.",
  },
];

export function BilingualNotationLabTab({
  capabilities,
  voiceStatus,
}: BilingualNotationLabTabProps) {
  const { token } = useAuth();
  const { preferences } = useLanguage();

  const [sourceText, setSourceText] = useState(STEM_SAMPLES[0].text);
  const [explanationLang, setExplanationLang] = useState(
    preferences.preferred_explanation_language === "en"
      ? "hi"
      : preferences.preferred_explanation_language
  );
  const [subtitleLang, setSubtitleLang] = useState(
    preferences.preferred_subtitle_language
  );
  const [voiceLang, setVoiceLang] = useState(
    preferences.preferred_voice_language
  );
  const [bilingualMode, setBilingualMode] = useState<BilingualMode>(
    preferences.bilingual_explanation_mode
  );
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [preview, setPreview] = useState<BilingualPreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // STT verification state
  const [sttHint, setSttHint] = useState("");
  const [sttResult, setSttResult] = useState<STTResponseOut | null>(null);
  const [sttLoading, setSttLoading] = useState(false);
  const [sttError, setSttError] = useState<string | null>(null);

  const localNotationReport = verifyClientNotationPreservation(
    sourceText,
    preview?.rendered_text ?? sourceText
  );

  async function handleRunPreview() {
    setLoadingPreview(true);
    setPreviewError(null);
    try {
      const res = await previewBilingualExplanation({
        source_text: sourceText,
        explanation_language: explanationLang,
        subtitle_language: subtitleLang,
        voice_language: voiceLang,
        bilingual_mode: bilingualMode,
      });
      setPreview(res);
    } catch {
      // Deterministic client-side preview fallback when API server is offline in preview
      const expRes = resolveModalityFallbackClient(
        explanationLang,
        "explanation",
        capabilities
      );
      const subRes = resolveModalityFallbackClient(
        subtitleLang,
        "subtitle",
        capabilities
      );
      const voxRes = resolveModalityFallbackClient(
        voiceLang,
        "voice",
        capabilities
      );
      const report = verifyClientNotationPreservation(sourceText, sourceText);
      const rendered =
        bilingualMode === "side_by_side"
          ? `[Target (${expRes.effective_language.toUpperCase()}) · STEM notation preserved]\n${sourceText}\n\n[English STEM Reference]\n${sourceText}`
          : `[Bilingual STEM · ${expRes.effective_language.toUpperCase()} + English terms]\n${sourceText}`;

      setPreview({
        rendered_text: rendered,
        bilingual_mode: bilingualMode,
        explanation_resolution: expRes,
        subtitle_resolution: subRes,
        voice_resolution: voxRes,
        speakable_math_text: sourceText
          .replace(/\$\$/g, "")
          .replace(/\$/g, "")
          .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "$1 divided by $2")
          .replace(/\\sqrt\{([^}]+)\}/g, "square root of $1"),
        notation_report: report,
        matched_glossary_terms: [],
        tts_provider_configured: Boolean(voiceStatus?.elevenlabs_configured),
        stt_provider_configured: Boolean(voiceStatus?.elevenlabs_configured),
      });
      setPreviewError(
        "Live API unreachable; displaying deterministic client-side notation & fallback analysis."
      );
    } finally {
      setLoadingPreview(false);
    }
  }

  async function handleTestStt() {
    setSttLoading(true);
    setSttError(null);
    const voxRes = resolveModalityFallbackClient(
      voiceLang,
      "voice",
      capabilities
    );
    if (!token) {
      setSttResult({
        stt_available: false,
        transcript: sttHint.trim() || null,
        confidence: null,
        requested_language: voiceLang,
        effective_language: voxRes.effective_language,
        fallback_applied: voxRes.fallback_applied,
        provider: "unauthenticated_preview",
        latency_ms: 0,
        audio_seconds: 0,
        is_fallback: true,
        fallback_mode: "text_input",
        limitation_notice:
          "Sign in to invoke /api/v1/voice/stt. When ElevenLabs Scribe API credentials are absent, typed answer input remains the truthful fallback.",
      });
      setSttLoading(false);
      return;
    }

    try {
      const res = await transcribeVoiceStt(token, {
        language_code: voiceLang,
        browser_transcript_hint: sttHint.trim() || null,
      });
      setSttResult(res);
    } catch (err) {
      setSttError(
        err instanceof Error
          ? err.message
          : "STT request failed; typed input fallback remains active."
      );
    } finally {
      setSttLoading(false);
    }
  }

  const activeReport = preview?.notation_report ?? localNotationReport;

  return (
    <section
      className="space-y-6"
      aria-label="Bilingual explanation, notation preservation, and voice lab"
    >
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Input & Controls */}
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 lg:col-span-6">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Bilingual Explanation & Notation Preservation Lab
            </h2>
            <p className="text-xs text-slate-600">
              Test how mathematical LaTeX, SI units, scientific notation, and
              chemical formulas stay 100% intact across localized and bilingual
              STEM explanations.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {STEM_SAMPLES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setSourceText(s.text)}
                className="whitespace-nowrap shrink-0 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
              >
                {s.label}
              </button>
            ))}
          </div>

          <label className="block text-xs font-medium text-slate-700">
            Source STEM Explanation (LaTeX $...$ / SI Units / Chemical Formulas)
            <textarea
              rows={4}
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-xs font-medium text-slate-700">
              Explanation Language
              <select
                value={explanationLang}
                onChange={(e) => setExplanationLang(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              >
                {capabilities.map((c) => (
                  <option key={c.language_code} value={c.language_code}>
                    {c.display_name} ({c.language_code})
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-xs font-medium text-slate-700">
              Bilingual Strategy
              <select
                value={bilingualMode}
                onChange={(e) =>
                  setBilingualMode(e.target.value as BilingualMode)
                }
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              >
                <option value="bilingual_stem_en">
                  Bilingual STEM (English terms preserved)
                </option>
                <option value="side_by_side">Side-by-Side (Target + EN)</option>
                <option value="monolingual">Monolingual Target Script</option>
              </select>
            </label>

            <label className="block text-xs font-medium text-slate-700">
              Voice (TTS / STT) Language
              <select
                value={voiceLang}
                onChange={(e) => setVoiceLang(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              >
                {capabilities.map((c) => (
                  <option key={c.language_code} value={c.language_code}>
                    {c.display_name} ({c.language_code})
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-xs font-medium text-slate-700">
              Subtitle Language
              <select
                value={subtitleLang}
                onChange={(e) => setSubtitleLang(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              >
                {capabilities.map((c) => (
                  <option key={c.language_code} value={c.language_code}>
                    {c.display_name} ({c.language_code})
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button
            type="button"
            disabled={loadingPreview || sourceText.trim().length < 5}
            onClick={() => void handleRunPreview()}
            className="whitespace-nowrap shrink-0 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800 disabled:opacity-50"
          >
            {loadingPreview
              ? "Auditing & Rendering..."
              : "Generate Bilingual & Notation Preview"}
          </button>

          {previewError && (
            <p className="text-xs text-amber-800">{previewError}</p>
          )}
        </div>

        {/* Right: Rendered Output & Notation Verification */}
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 lg:col-span-6">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-semibold text-slate-900">
              KaTeX Rendered Output & Notation Audit
            </h3>
            <StatusBadge
              tone={activeReport.all_preserved ? "healthy" : "degraded"}
            >
              {activeReport.all_preserved
                ? "Notation 100% Intact"
                : "Notation Warning"}
            </StatusBadge>
          </div>

          <div
            className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 text-sm leading-relaxed text-slate-900 whitespace-pre-wrap"
            dir={
              capabilities.find((c) => c.language_code === explanationLang)?.rtl
                ? "rtl"
                : "ltr"
            }
          >
            <MathText text={preview?.rendered_text ?? sourceText} />
          </div>

          {/* Preservation Scores */}
          <div className="grid grid-cols-2 gap-3 text-xs tabular-nums">
            <div className="rounded-lg border border-slate-200 p-3">
              <div className="text-slate-500">Math Preservation</div>
              <div className="mt-1 text-lg font-bold text-slate-900">
                {activeReport.math_preservation_score.toFixed(1)}%
              </div>
              <div className="text-slate-600">
                {activeReport.math_expressions.length} LaTeX block(s) detected
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <div className="text-slate-500">Science / SI / Chem</div>
              <div className="mt-1 text-lg font-bold text-slate-900">
                {activeReport.science_notation_score.toFixed(1)}%
              </div>
              <div className="text-slate-600">
                {activeReport.si_unit_values.length +
                  activeReport.scientific_notations.length +
                  activeReport.chemical_formulas.length}{" "}
                scientific token(s)
              </div>
            </div>
          </div>

          {preview && (
            <div className="space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
              <div>
                <span className="font-semibold text-slate-800">
                  Speakable Math Narration:{" "}
                </span>
                {preview.speakable_math_text}
              </div>
              <div>
                <span className="font-semibold text-slate-800">
                  Voice Resolution:{" "}
                </span>
                {preview.voice_resolution.fallback_applied
                  ? preview.voice_resolution.fallback_reason
                  : `Direct ${preview.voice_resolution.effective_language.toUpperCase()} via ${preview.voice_resolution.provider || "voice adapter"}`}
              </div>
              {preview.matched_glossary_terms.length > 0 && (
                <div>
                  <span className="font-semibold text-slate-800">
                    Matched Glossary Terms:{" "}
                  </span>
                  {preview.matched_glossary_terms
                    .map(
                      (g) =>
                        `${g.localized_term} (${g.english_term}${g.latex_symbol ? ` · ${g.latex_symbol}` : ""})`
                    )
                    .join(" · ")}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* TTS & STT Provider Capability & Honest Fallback Panel */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Speech-to-Text (STT) & Text-to-Speech (TTS) Capability Status
            </h3>
            <p className="text-xs text-slate-600">
              {voiceStatus?.honest_status_notice ??
                "Voice adapters run behind VoiceProviderInterface (ElevenLabs TTS + Scribe STT). When credentials are absent or a language is unverified, captions and text input serve as honest fallbacks."}
            </p>
          </div>
          <StatusBadge
            tone={voiceStatus?.elevenlabs_configured ? "healthy" : "degraded"}
          >
            {voiceStatus?.elevenlabs_configured
              ? "Provider Key Active"
              : "Provider Key Required"}
          </StatusBadge>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex-1 text-xs font-medium text-slate-700">
            Optional Browser Speech Hint / Fallback Check ({voiceLang.toUpperCase()})
            <input
              type="text"
              value={sttHint}
              onChange={(e) => setSttHint(e.target.value)}
              placeholder="e.g., What is the acceleration due to gravity?"
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            />
          </label>
          <button
            type="button"
            disabled={sttLoading}
            onClick={() => void handleTestStt()}
            className="whitespace-nowrap shrink-0 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
          >
            {sttLoading ? "Checking STT..." : "Test STT Capability & Fallback"}
          </button>
        </div>

        {sttError && <p className="text-xs text-rose-700">{sttError}</p>}
        {sttResult && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs text-slate-700 space-y-1">
            <div className="font-semibold text-slate-900">
              Provider: {sttResult.provider} · Effective Language:{" "}
              {sttResult.effective_language.toUpperCase()} · Fallback:{" "}
              {sttResult.is_fallback ? "Yes" : "No"}
            </div>
            {sttResult.transcript && (
              <div>Transcript: {sttResult.transcript}</div>
            )}
            {sttResult.limitation_notice && (
              <div className="text-amber-900">{sttResult.limitation_notice}</div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
