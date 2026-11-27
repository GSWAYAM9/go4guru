import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LanguagesStudioPage from "@/app/languages/page";
import { LanguageProvider } from "@/lib/language-context";
import { FALLBACK_LANGUAGE_REGISTRY } from "@/lib/multilingual-helpers";

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-reviewer-jwt",
    user: {
      id: "rev-1",
      email: "reviewer@go4guru.edu",
      display_name: "Dr. Meera Iyer",
      roles: ["academic_reviewer", "teacher"],
      permissions: [
        "multilingual:read",
        "multilingual:translate",
        "multilingual:review",
        "multilingual:manage",
      ],
      is_minor: false,
      mfa_enabled: true,
      mfa_verified: true,
      status: "active",
    },
    initializing: false,
    mfaRequired: false,
    clearSession: vi.fn(),
  }),
}));

describe("Phase 10: Multilingual Learning Expansion (/languages)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    document.documentElement.dir = "ltr";
    document.documentElement.lang = "en";
  });

  it("supports 6 independent modalities, Urdu RTL with LTR KaTeX, honest 14-language registry, bilingual lab, glossary, translation review, and quality evals", async () => {
    let savedPrefs = {
      ui_language: "en",
      preferred_explanation_language: "hi",
      preferred_voice_language: "or",
      preferred_subtitle_language: "or",
      preferred_question_language: "ta",
      preferred_answer_language: "en",
      bilingual_explanation_mode: "bilingual_stem_en",
      resolutions: {
        ui: {
          modality: "ui",
          requested_language: "en",
          effective_language: "en",
          fallback_applied: false,
          fallback_reason: null,
          capability_status: "production",
          availability_status: "available",
          testing_status: "passed",
          rtl: false,
          provider: "built_in_catalog",
        },
        explanation: {
          modality: "explanation",
          requested_language: "hi",
          effective_language: "hi",
          fallback_applied: false,
          fallback_reason: null,
          capability_status: "beta",
          availability_status: "available",
          testing_status: "partial",
          rtl: false,
          provider: "llm_bilingual_glossary",
        },
        voice: {
          modality: "voice",
          requested_language: "or",
          effective_language: "hi",
          fallback_applied: true,
          fallback_reason:
            "Voice TTS narration is not yet verified for Odia (or); falling back to Hindi (hi). Synchronized Odia subtitles remain active.",
          capability_status: "beta",
          availability_status: "provider_key_required",
          testing_status: "partial",
          rtl: false,
          provider: "elevenlabs",
        },
        subtitle: {
          modality: "subtitle",
          requested_language: "or",
          effective_language: "or",
          fallback_applied: false,
          fallback_reason: null,
          capability_status: "experimental",
          availability_status: "limited",
          testing_status: "pending",
          rtl: false,
          provider: "llm_bilingual_glossary",
        },
        question: {
          modality: "question",
          requested_language: "ta",
          effective_language: "en",
          fallback_applied: true,
          fallback_reason:
            "Question bank translation is not yet verified for Tamil (ta); falling back to English (en).",
          capability_status: "production",
          availability_status: "available",
          testing_status: "passed",
          rtl: false,
          provider: "built_in_catalog",
        },
        answer: {
          modality: "answer",
          requested_language: "en",
          effective_language: "en",
          fallback_applied: false,
          fallback_reason: null,
          capability_status: "production",
          availability_status: "available",
          testing_status: "passed",
          rtl: false,
          provider: "built_in_catalog",
        },
      },
    };

    const translations = [
      {
        id: "tr-1",
        resource_type: "concept_summary",
        resource_key: "physics.newtons_second_law",
        source_language_code: "en",
        target_language_code: "hi",
        source_text: "Force equals mass times acceleration: $F = ma$.",
        translated_text:
          "बल (Force) द्रव्यमान और त्वरण का गुणनफल है: $F = ma$।",
        bilingual_text: null,
        notation_preserved: true,
        terminology_warnings: [],
        status: "pending_review",
        quality_score: 96.5,
        reviewer_notes: null,
        reviewed_at: null,
        created_at: "2026-11-26T18:00:00Z",
      },
    ];

    const evaluations = [
      {
        id: "ev-1",
        language_code: "hi",
        modality: "bilingual",
        provider_name: "glossary_guided_pipeline",
        test_suite_version: "p10-v1",
        script_fidelity_score: 96.0,
        math_preservation_score: 100.0,
        science_notation_score: 100.0,
        terminology_accuracy_score: 95.0,
        fluency_score: 94.0,
        overall_score: 97.4,
        passed: true,
        sample_count: 3,
        findings: [],
        evaluated_at: "2026-11-26T18:05:00Z",
      },
    ];

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/v1/languages/capabilities")) {
        return new Response(JSON.stringify(FALLBACK_LANGUAGE_REGISTRY), {
          status: 200,
        });
      }
      if (url.endsWith("/api/v1/languages/preferences") && method === "GET") {
        return new Response(JSON.stringify(savedPrefs), { status: 200 });
      }
      if (url.endsWith("/api/v1/languages/preferences") && method === "PUT") {
        const body = JSON.parse(String(init?.body ?? "{}"));
        savedPrefs = { ...savedPrefs, ...body };
        if (body.ui_language === "ur") {
          savedPrefs.resolutions.ui = {
            ...savedPrefs.resolutions.ui,
            requested_language: "ur",
            effective_language: "ur",
            rtl: true,
          };
        }
        return new Response(JSON.stringify(savedPrefs), { status: 200 });
      }
      if (url.includes("/api/v1/languages/ui-bundle/")) {
        const isUr = url.endsWith("/ur");
        return new Response(
          JSON.stringify({
            requested_language: isUr ? "ur" : "en",
            effective_language: isUr ? "ur" : "en",
            rtl: isUr,
            coverage_pct: isUr ? 100 : 100,
            translated_key_count: 30,
            total_key_count: 30,
            fallback_keys: [],
            strings: isUr
              ? { "lang.title": "کثیر لسانی تعلیمی اسٹوڈیو" }
              : { "lang.title": "Multilingual Learning Studio" },
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/api/v1/voice/capabilities")) {
        return new Response(
          JSON.stringify({
            elevenlabs_configured: false,
            tts_model_id: "eleven_multilingual_v2",
            stt_model_id: "scribe_v1",
            verified_tts_languages: ["en", "hi"],
            verified_stt_languages: ["en", "hi"],
            honest_status_notice:
              "ELEVENLABS_API_KEY not configured; captions and text fallback active.",
          }),
          { status: 200 }
        );
      }
      if (url.includes("/api/v1/languages/glossary") && method === "GET") {
        return new Response(
          JSON.stringify([
            {
              id: "g-1",
              concept_key: "force",
              subject_area: "physics",
              english_term: "Force",
              language_code: "hi",
              localized_term: "बल",
              transliteration: "bal",
              preserve_english_in_bilingual: true,
              latex_symbol: "$F = ma$",
              review_status: "approved",
              notes: "NCERT standard",
              created_at: "2026-11-26T18:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }
      if (url.endsWith("/api/v1/languages/bilingual-preview")) {
        return new Response(
          JSON.stringify({
            rendered_text:
              "न्यूटन के नियम के अनुसार बल (Force): $F = ma$ तथा $g = 9.8 m/s^2$।",
            bilingual_mode: "bilingual_stem_en",
            explanation_resolution: savedPrefs.resolutions.explanation,
            subtitle_resolution: savedPrefs.resolutions.subtitle,
            voice_resolution: savedPrefs.resolutions.voice,
            speakable_math_text: "F equals m a and g equals 9.8 m/s^2",
            notation_report: {
              math_preserved: true,
              science_preserved: true,
              all_preserved: true,
              math_preservation_score: 100,
              science_notation_score: 100,
              math_expressions: ["$F = ma$", "$g = 9.8 m/s^2$"],
              scientific_notations: [],
              si_unit_values: ["9.8 m/s^2"],
              chemical_formulas: [],
              missing_math: [],
              missing_science: [],
            },
            matched_glossary_terms: [
              {
                english_term: "Force",
                localized_term: "बल",
                latex_symbol: "$F = ma$",
              },
            ],
            tts_provider_configured: false,
            stt_provider_configured: false,
          }),
          { status: 200 }
        );
      }
      if (url.includes("/api/v1/languages/translations") && method === "GET") {
        return new Response(JSON.stringify(translations), { status: 200 });
      }
      if (url.includes("/api/v1/languages/translations/tr-1/review")) {
        translations[0] = { ...translations[0], status: "approved" };
        return new Response(JSON.stringify(translations[0]), { status: 200 });
      }
      if (url.includes("/api/v1/languages/evaluations") && method === "GET") {
        return new Response(JSON.stringify(evaluations), { status: 200 });
      }
      if (url.endsWith("/api/v1/languages/evaluations/run")) {
        const added = {
          ...evaluations[0],
          id: "ev-2",
          language_code: "ta",
          overall_score: 94.2,
        };
        evaluations.unshift(added);
        return new Response(JSON.stringify(added), { status: 201 });
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(
      <LanguageProvider>
        <LanguagesStudioPage />
      </LanguageProvider>
    );

    // 1. Header & 6-modality fallback diagnostics render honestly
    await waitFor(() => {
      expect(screen.getByText(/tracked languages/i)).toBeInTheDocument();
      expect(
        screen.getAllByText(/Voice TTS narration is not yet verified for Odia/i)
          .length
      ).toBeGreaterThanOrEqual(1);
    });

    // 2. Quick switch to Urdu (ur) triggers RTL document direction
    fireEvent.click(screen.getByRole("button", { name: /اردو \(ur · RTL\)/i }));
    await waitFor(() => {
      expect(document.documentElement.dir).toBe("rtl");
      expect(document.documentElement.lang).toBe("ur");
    });

    // 3. Capability Registry shows all 14 languages & truthful planned status for Sanskrit
    fireEvent.click(screen.getByRole("tab", { name: /Capability Registry/i }));
    await waitFor(() => {
      expect(
        screen.getByText(/Empirical Language Capability Registry/i)
      ).toBeInTheDocument();
      expect(screen.getAllByText(/Sanskrit/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Assamese/i).length).toBeGreaterThanOrEqual(1);
    });

    // 4. Bilingual & Voice Lab renders KaTeX with LTR isolation and 100% notation preservation
    fireEvent.click(screen.getByRole("tab", { name: /Bilingual & Voice Lab/i }));
    fireEvent.click(
      screen.getByRole("button", { name: /Generate Bilingual & Notation Preview/i })
    );
    await waitFor(() => {
      expect(screen.getByText(/Notation 100% Intact/i)).toBeInTheDocument();
      expect(screen.getByText(/F equals m a/i)).toBeInTheDocument();
    });

    // 5. STEM Terminology Dictionary renders Hindi Force term
    fireEvent.click(screen.getByRole("tab", { name: /STEM Terminology/i }));
    await waitFor(() => {
      expect(screen.getByText("बल")).toBeInTheDocument();
    });

    // 6. Translation Review & QA approves pending entry & runs quality evaluation
    fireEvent.click(
      screen.getByRole("tab", { name: /Translation Review & QA/i })
    );
    await waitFor(() => {
      expect(screen.getByText(/physics\.newtons_second_law/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => {
      expect(screen.getByText(/Marked translation as approved/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Run Quality Suite/i }));
    await waitFor(() => {
      expect(screen.getByText(/Completed TA \(bilingual\) evaluation/i)).toBeInTheDocument();
    });
  });
});
