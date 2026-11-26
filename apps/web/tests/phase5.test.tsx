import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AdaptiveMasteryPage from "@/app/adaptive/page";
import RevisionPage from "@/app/revision/page";

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
      permissions: ["learning:adaptive_read", "revision:manage", "notifications:read_own"],
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

describe("Phase 5 Adaptive Mastery & Spaced Repetition UI", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders multi-signal concept mastery breakdown, misconception card, and recommendations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            concepts: [
              {
                concept_id: "c1",
                concept_code: "QUAD_DISC",
                concept_title: "Quadratic Discriminant",
                subject_name: "Mathematics",
                chapter_title: "Quadratic Equations",
                mastery_score: 38.5,
                confidence: 0.4,
                retention_score: 0.72,
                independent_solve_ratio: 0.0,
                transfer_score: 0.25,
                improvement_slope: 0.4,
                difficulty_weighted_accuracy: 0.2,
                band: "novice",
                attempts_count: 2,
                last_practiced_at: "2026-11-27T01:00:00Z",
                next_review_due_at: "2026-11-28T01:00:00Z",
                breakdown: {},
                evidence_summary: {},
              },
            ],
            weak_concepts: [
              {
                concept_id: "c1",
                concept_code: "QUAD_DISC",
                concept_title: "Quadratic Discriminant",
                subject_name: "Mathematics",
                chapter_title: "Quadratic Equations",
                mastery_score: 38.5,
                confidence: 0.4,
                retention_score: 0.72,
                independent_solve_ratio: 0.0,
                transfer_score: 0.25,
                improvement_slope: 0.4,
                difficulty_weighted_accuracy: 0.2,
                band: "novice",
                attempts_count: 2,
                last_practiced_at: "2026-11-27T01:00:00Z",
                next_review_due_at: "2026-11-28T01:00:00Z",
                breakdown: {},
                evidence_summary: {},
              },
            ],
            mastered_concepts: [],
            unresolved_misconceptions: [
              {
                id: "m1",
                concept_id: "c1",
                concept_title: "Quadratic Discriminant",
                question_id: null,
                misconception_code: "SIGN_ERR",
                title: "Dropped negative in 4ac",
                description: "Verify sign before square root.",
                severity: "high",
                occurrence_count: 2,
                last_observed_at: "2026-11-27T01:00:00Z",
                resolved_at: null,
              },
            ],
            recommendations: [
              {
                concept_id: "c0",
                concept_title: "Linear Expressions",
                item_type: "remediate_prerequisite",
                priority_score: 121.0,
                reason: "Strengthen prerequisite Linear Expressions before remediating Quadratic Discriminant.",
                action_route: "/practice",
              },
            ],
            algorithm_version: "phase5_multi_signal_v1",
            limitations_note: "Uses authored difficulty labels until cohort calibration.",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "n1",
              notification_type: "weak_concept_alert",
              title: "Needs Remediation: Quadratic Discriminant",
              body: "Mastery 38.5/100.",
              action_url: "/adaptive",
              is_read: false,
              read_at: null,
              metadata: {},
              created_at: "2026-11-27T01:00:00Z",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<AdaptiveMasteryPage />);
    await waitFor(() =>
      expect(screen.getByTestId("mastery-card-QUAD_DISC")).toBeInTheDocument()
    );
    expect(screen.getByText(/remediate_prerequisite/i)).toBeInTheDocument();
    expect(screen.getByText(/Dropped negative in 4ac/i)).toBeInTheDocument();
    expect(screen.getByText(/phase5_multi_signal_v1/i)).toBeInTheDocument();
  });

  it("renders SM-2+ due revision deck, analytics KPIs, and study planner", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const sampleCard = {
      id: "fc-1",
      card_type: "missed_question",
      concept_id: "c1",
      concept_title: "Linear Equations",
      subject_id: null,
      source_question_id: "q1",
      language_code: "en",
      front_markdown: "Solve $2x + 4 = 10$",
      back_markdown: "Option B ($x = 3$)",
      hint_markdown: "Subtract 4 from both sides.",
      tags: ["easy", "practice"],
      due_at: "2026-11-27T01:00:00Z",
      interval_days: 0,
      ease_factor: 2.3,
      repetitions: 0,
      lapse_count: 1,
      last_quality: null,
      last_reviewed_at: null,
      priority_score: 52.5,
      is_due: true,
    };

    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([sampleCard]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([sampleCard]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            total_flashcards: 1,
            due_now_count: 1,
            mastered_cards_count: 0,
            lapsed_cards_count: 1,
            missed_question_cards_count: 1,
            total_reviews: 0,
            average_quality: 0,
            retention_success_rate_pct: 0,
            active_plan_completion_pct: 0,
            by_card_type: { missed_question: 1 },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<RevisionPage />);
    await waitFor(() =>
      expect(screen.getByText(/Due Revision Queue \(1\)/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/Missed-Q Cards/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Reveal Answer/i })
    ).toBeEnabled();
  });
});
