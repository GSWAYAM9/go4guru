import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AnalyticsPage from "@/app/analytics/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ attemptId: "att-1" }),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-jwt-token",
    user: {
      id: "u1",
      email: "student@example.com",
      display_name: "Test Student",
      roles: ["student"],
      permissions: ["analytics:read_own", "assessment:attempt", "quiz:attempt"],
      is_minor: false,
      mfa_enabled: false,
      mfa_verified: false,
      status: "active",
    },
    initializing: false,
    mfaRequired: false,
    clearSession: vi.fn(),
  }),
}));

describe("Phase 2 Analytics & Assessment UI States", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders real PostgreSQL analytics snapshot and empty learning events honestly", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          assessments_completed: 2,
          average_assessment_accuracy_pct: 75.0,
          practice_attempts: 4,
          practice_correct: 3,
          practice_accuracy_pct: 75.0,
          total_learning_events: 0,
          recent_events: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(screen.getAllByText("75%").length).toBe(2);
      expect(screen.getByText("3 / 4 correct")).toBeInTheDocument();
      expect(
        screen.getByText(/No Learning Events Recorded Yet/i)
      ).toBeInTheDocument();
    });
  });

  it("surfaces structured API error banner when analytics endpoint fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "ANALYTICS_DOWN",
            message: "Analytics store temporarily unavailable.",
            details: null,
            request_id: "req-phase2-err",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/ANALYTICS_DOWN/i);
      expect(screen.getByRole("alert")).toHaveTextContent(
        /Analytics store temporarily unavailable/i
      );
    });
  });
});
