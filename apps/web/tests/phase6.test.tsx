import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HomeworkPage from "@/app/homework/page";

const mockRouter = { push: vi.fn(), replace: vi.fn() };
let mockUserRoles = ["student"];

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-jwt-token",
    user: {
      id: "student-1",
      email: "student@example.com",
      display_name: "Aarav Student",
      roles: mockUserRoles,
      permissions: ["homework:manage_own"],
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

function makeSampleSubmission(overrides: Record<string, unknown> = {}) {
  return {
    id: "sub-1",
    student_id: "student-1",
    title: "Linear Equations Q4",
    selected_subject: "auto",
    detected_subject: "mathematics",
    subject_confidence: 0.94,
    language_code: "en",
    status: "feedback_ready",
    page_count: 1,
    retry_count: 0,
    needs_ocr_review: false,
    failure_reason: null,
    files: [
      {
        id: "file-1",
        page_no: 1,
        original_filename: "algebra_q4.jpg",
        mime_type: "image/jpeg",
        detected_format: "jpeg",
        size_bytes: 184200,
        sha256: "abc123",
        exif_stripped: true,
        pdf_page_count: null,
        scan_status: "clean",
        download_url: "/api/v1/homework/submissions/sub-1/files/file-1",
        created_at: "2026-11-26T10:00:00Z",
      },
    ],
    ocr_pages: [
      {
        id: "ocr-1",
        page_no: 1,
        ocr_provider: "gemini_vision",
        extracted_text: "Solve 2x + 4 = 10\nStep 1: 2x = 14\nStep 2: x = 7",
        extracted_latex: null,
        handwriting_detected: true,
        handwriting_supported: true,
        confidence: 0.91,
        needs_review: false,
        student_corrected_text: null,
        effective_text: "Solve 2x + 4 = 10\nStep 1: 2x = 14\nStep 2: x = 7",
        warnings: [],
      },
    ],
    latest_evaluation: {
      id: "eval-1",
      attempt_no: 1,
      subject_area: "mathematics",
      detected_question: "Solve 2x + 4 = 10",
      student_work_summary: "2 step(s) extracted for Mathematics evaluation.",
      extracted_steps: [
        { step_no: 1, content: "2x = 14", expression: "2x = 14" },
        { step_no: 2, content: "x = 7", expression: "x = 7" },
      ],
      step_evaluations: [
        {
          step_no: 1,
          student_work: "2x = 14",
          status: "incorrect",
          explanation: "This step is not algebraically equivalent to the original equation.",
          error_categories: ["algebra"],
          verifier_note: "Expected equivalence with 2x + 4 = 10",
        },
      ],
      error_classifications: [
        {
          subject_area: "mathematics",
          category: "algebra",
          severity: "high",
          step_no: 1,
          summary: "Algebraic manipulation mismatch in Step 1.",
          guidance: "Perform the identical inverse operation on both sides of the equation.",
        },
      ],
      overall_status: "needs_correction",
      feedback_summary: "Detected 1 area(s) to improve in your mathematics solution.",
      strengths: ["Attempted structured line-by-line mathematics work."],
      unlocked_hints: [
        {
          level: 1,
          stage: "conceptual_nudge",
          title: "Level 1 — Identify the Inverse Operation",
          content_markdown: "Look at +4 on the left side. What inverse operation cancels +4?",
          spoiler_checked: true,
        },
      ],
      current_hint_level_unlocked: 1,
      max_hint_level: 3,
      has_more_hints: true,
      solution_revealed: false,
      complete_solution_markdown: null,
      verifier_results: { engine: "sympy_math", checks: [] },
      validation_report: {
        passed: true,
        spoiler_guard_passed: true,
        taxonomy_valid: true,
        verifier_agreement: "verified",
        safety_passed: true,
        confidence_adjusted: false,
        issues: [],
      },
      revision_recommendations: [
        {
          topic_title: "Targeted Algebra Practice",
          reason: "Reinforce inverse operations across linear equations.",
          recommended_action: "guided_practice",
          action_route: "/practice",
          priority: "high",
          error_categories: ["algebra"],
        },
      ],
      confidence: 0.88,
      confidence_band: "high",
      provider_used: "deterministic_subject_engine",
      model_id: "sympy-math-evaluator-v1",
      is_fallback: true,
      safety_verdict: "allow",
      created_at: "2026-11-26T10:00:05Z",
    },
    evaluation_history: [],
    created_at: "2026-11-26T10:00:00Z",
    updated_at: "2026-11-26T10:00:05Z",
    ...overrides,
  };
}

describe("Phase 6 Homework AI Workspace UI", () => {
  afterEach(() => {
    mockUserRoles = ["student"];
    vi.restoreAllMocks();
  });

  it("renders subject-aware evaluation, keeps complete solution hidden by default, and unlocks graduated hints on click", async () => {
    const sample = makeSampleSubmission();
    sample.evaluation_history = [sample.latest_evaluation];

    const unlockedLevel2 = {
      ...sample.latest_evaluation,
      current_hint_level_unlocked: 2,
      unlocked_hints: [
        ...sample.latest_evaluation.unlocked_hints,
        {
          level: 2,
          stage: "method_scaffold",
          title: "Level 2 — Balance Both Sides",
          content_markdown: "Subtract 4 from both sides before dividing by 2.",
          spoiler_checked: true,
        },
      ],
    };

    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "sub-1",
              title: "Linear Equations Q4",
              selected_subject: "auto",
              detected_subject: "mathematics",
              subject_confidence: 0.94,
              language_code: "en",
              status: "feedback_ready",
              page_count: 1,
              retry_count: 0,
              needs_ocr_review: false,
              latest_overall_status: "needs_correction",
              latest_confidence: 0.88,
              error_count: 1,
              created_at: "2026-11-26T10:00:00Z",
              updated_at: "2026-11-26T10:00:05Z",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(sample), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(unlockedLevel2), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    render(<HomeworkPage />);

    await waitFor(() =>
      expect(screen.getByText(/Solve 2x \+ 4 = 10/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/Algebraic manipulation mismatch in Step 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Level 1 — Identify the Inverse Operation/i)).toBeInTheDocument();
    // Anti-spoiler check: complete solution is NOT revealed by default
    expect(screen.queryByText(/Revealed Complete Solution/i)).not.toBeInTheDocument();

    // Unlock Hint Level 2
    fireEvent.click(screen.getByRole("button", { name: /Unlock Hint Level 2/i }));
    await waitFor(() =>
      expect(screen.getByText(/Level 2 — Balance Both Sides/i)).toBeInTheDocument()
    );

    // Revision recommendation link is shown
    expect(screen.getByText(/Targeted Algebra Practice/i)).toBeInTheDocument();
  });

  it("supports student retry submission and shows errors resolved progress", async () => {
    const sample = makeSampleSubmission();
    sample.evaluation_history = [sample.latest_evaluation];

    const attempt2Eval = {
      ...sample.latest_evaluation,
      id: "eval-2",
      attempt_no: 2,
      overall_status: "correct",
      error_classifications: [],
      step_evaluations: [
        {
          step_no: 1,
          student_work: "2x = 6",
          status: "correct",
          explanation: "Equivalent algebraic transformation verified.",
          error_categories: [],
          verifier_note: "x = [3]",
        },
      ],
      feedback_summary: "All verified mathematical steps are algebraically consistent. Great precision!",
    };

    const retriedSubmission = makeSampleSubmission({
      status: "completed",
      retry_count: 1,
      latest_evaluation: attempt2Eval,
      evaluation_history: [attempt2Eval, sample.latest_evaluation],
    });

    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "sub-1",
              title: "Linear Equations Q4",
              selected_subject: "auto",
              detected_subject: "mathematics",
              subject_confidence: 0.94,
              language_code: "en",
              status: "feedback_ready",
              page_count: 1,
              retry_count: 0,
              needs_ocr_review: false,
              latest_overall_status: "needs_correction",
              latest_confidence: 0.88,
              error_count: 1,
              created_at: "2026-11-26T10:00:00Z",
              updated_at: "2026-11-26T10:00:05Z",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(sample), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(retriedSubmission), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    render(<HomeworkPage />);
    await waitFor(() =>
      expect(screen.getByLabelText(/Your revised solution steps/i)).toBeInTheDocument()
    );

    fireEvent.change(screen.getByLabelText(/Your revised solution steps/i), {
      target: { value: "Step 1: 2x = 6\nStep 2: x = 3" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Submit Revised Attempt/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/Progress: 1 error\(s\) resolved across 2 attempts/i)
      ).toBeInTheDocument()
    );
    expect(screen.getByText(/Revised attempt verified correct!/i)).toBeInTheDocument();
  });

  it("blocks unsupported file formats client-side during upload queueing", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    render(<HomeworkPage />);
    await waitFor(() =>
      expect(screen.getByText(/Ready to Check Your Homework/i)).toBeInTheDocument()
    );

    const fileInput = document.getElementById("homework-file-input") as HTMLInputElement;
    const svgFile = new File(["<svg></svg>"], "malicious.svg", {
      type: "image/svg+xml",
    });
    fireEvent.change(fileInput, { target: { files: [svgFile] } });

    expect(
      screen.getByText(/is not a supported format\. Upload JPEG, PNG, WebP, or PDF/i)
    ).toBeInTheDocument();
  });

  it("enforces parent privacy boundary on /homework", async () => {
    mockUserRoles = ["parent"];
    render(<HomeworkPage />);
    expect(
      screen.getByText(/Student Homework Coaching Is Private/i)
    ).toBeInTheDocument();
  });
});
