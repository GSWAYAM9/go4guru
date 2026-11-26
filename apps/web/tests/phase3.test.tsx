import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import TutorPage from "@/app/tutor/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-jwt-token",
    user: {
      id: "u1",
      email: "student@example.com",
      display_name: "Test Student",
      roles: ["student"],
      permissions: ["ai:chat"],
      is_minor: true,
      mfa_enabled: false,
      mfa_verified: false,
      status: "active",
    },
    initializing: false,
    mfaRequired: false,
    clearSession: vi.fn(),
  }),
}));

describe("Phase 3 Grounded AI Tutor UI", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("displays provider capabilities without secrets, verified turn badges, and citations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      // listAiSessions
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "sess-1",
              session_type: "tutor",
              title: "Algebra Doubt",
              teaching_mode: "step_by_step",
              language_code: "en",
              curriculum_context: {
                board_code: "CBSE",
                grade_number: 10,
                subject_id: null,
                subject_name: "Mathematics",
                discipline: "mathematics",
                chapter_id: null,
                chapter_title: null,
                topic_id: null,
                topic_title: null,
                concept_id: null,
                concept_title: null,
                learning_objectives: [],
                prerequisites: [],
              },
              context_summary: null,
              status: "active",
              created_at: "2026-11-26T16:00:00Z",
              updated_at: "2026-11-26T16:00:00Z",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      // fetchAiModels
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            primary_provider: "auto",
            providers: [
              {
                provider: "gemini",
                configured: false,
                fast_model: "gemini-2.5-flash",
                reasoning_model: "gemini-2.5-pro",
                circuit_state: "closed",
                notes: "Gemini",
              },
              {
                provider: "grounded_fallback",
                configured: true,
                fast_model: "deterministic-v1",
                reasoning_model: "deterministic-v1",
                circuit_state: "closed",
                notes: "Fallback",
              },
            ],
            daily_turn_limit: 60,
            rpm_limit: 15,
            supported_languages: ["en", "hi"],
            known_limitations: [
              "Only external providers with configured backend keys run live LLM inference.",
              "Non-symbolic qualitative answers are marked unverified.",
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      // fetchAiUsage
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            turns_used_today: 1,
            daily_turn_limit: 60,
            turns_remaining_today: 59,
            estimated_cost_usd_today: 0,
            rpm_limit: 15,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      // fetchSubjects
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      // listAiMessages
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "m-1",
              role: "assistant",
              content_markdown: "Verified Result: $x = 3$",
              intent: "step_by_step",
              pedagogical_mode: "step_by_step",
              spoiler_guard: false,
              citations: [
                {
                  chunk_id: "c-1",
                  document_id: "d-1",
                  hierarchy_path: "CBSE > Class 10 > Algebra",
                  section_title: "Linear Equations",
                  language_code: "en",
                  excerpt: "Isolate variable x cleanly.",
                  source_attribution: "Go4Guru Original",
                  score: 0.032,
                },
              ],
              follow_up_questions: ["Try a quadratic?"],
              generated_practice: [],
              verification_status: "verified",
              verification_summary: {},
              provider_used: "grounded_fallback",
              model_used: "deterministic-v1",
              prompt_version: "prompt_solver_v3.1",
              is_fallback: true,
              safety_verdict: "allow",
              tokens_in: 40,
              tokens_out: 25,
              latency_ms: 18,
              created_at: "2026-11-26T16:00:01Z",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<TutorPage />);

    await waitFor(() => {
      expect(screen.getByText(/gemini: key not set/i)).toBeInTheDocument();
      expect(screen.getByText("verified")).toBeInTheDocument();
      expect(screen.getByText("Grounded Fallback")).toBeInTheDocument();
      expect(
        screen.getByText(/\[CBSE > Class 10 > Algebra\]/i)
      ).toBeInTheDocument();
      expect(screen.getByText("Try a quadratic?")).toBeInTheDocument();
    });
  });

  it("renders structured 403 parent isolation or network error banner", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "PERMISSION_DENIED",
            message: "Parents cannot view raw student AI transcripts.",
            details: {},
            request_id: "req-par-403",
          },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<TutorPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/PERMISSION_DENIED/i);
      expect(screen.getByRole("alert")).toHaveTextContent(
        /Parents cannot view raw student AI transcripts/i
      );
    });
  });
});
