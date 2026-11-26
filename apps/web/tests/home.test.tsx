import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import { MathText } from "@/components/math-text";

describe("HomePage Phase 1 FoundationStatus", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders truthful error banner when backend API is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch")
    );

    render(<HomePage />);
    expect(
      screen.getByText(
        /Curriculum-Grounded Learning, Question Bank & Guided Practice/i
      )
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /NETWORK_UNREACHABLE/i
      );
    });
  });

  it("renders degraded dependency check and domain modules when API responds 503", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            status: "degraded",
            service: "go4guru-api",
            version: "0.1.0",
            environment: "test",
            phase: "phase_1_core_learning_platform",
            checks: {
              postgres: { status: "up", error: null },
              redis: { status: "down", error: "ConnectionRefusedError" },
            },
            timestamp: "2026-11-26T15:00:00Z",
          }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            service: "go4guru-api",
            version: "0.1.0",
            environment: "test",
            api_prefix: "/api/v1",
            ws_prefix: "/ws/v1",
            phase: "phase_1_core_learning_platform",
            modules: [
              {
                name: "identity",
                status: "implemented",
                planned_phase: "Phase 1",
              },
              {
                name: "curriculum",
                status: "implemented",
                planned_phase: "Phase 1",
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Degraded (503)")).toBeInTheDocument();
      expect(screen.getByText("ConnectionRefusedError")).toBeInTheDocument();
      expect(screen.getByText("identity")).toBeInTheDocument();
      expect(screen.getByText("curriculum")).toBeInTheDocument();
    });
  });

  it("renders KaTeX math safely without executing script tags in prose", () => {
    const { container } = render(
      <MathText text={'Solve $x^2 + 1 = 5$ <script>alert("xss")</script>'} />
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container.textContent).toContain('<script>alert("xss")</script>');
  });
});
