import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ExamPrepPage from "@/app/exams/page";

const mockRouter = { push: vi.fn(), replace: vi.fn() };

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-student-jwt",
    user: {
      id: "student-1",
      email: "aarav@go4guru.edu",
      display_name: "Aarav Sharma",
      roles: ["student"],
      permissions: ["exam_prep:read", "assessment:attempt", "quiz:create"],
      is_minor: false,
      mfa_enabled: false,
      mfa_verified: true,
      status: "active",
    },
    initializing: false,
    mfaRequired: false,
    clearSession: vi.fn(),
  }),
}));

const MOCK_TRACKS = [
  {
    id: "trk-cbse",
    code: "CBSE_BOARD",
    name: "CBSE Board Examination",
    target_seconds_per_question: 108,
    active_pattern: {
      id: "pat-cbse",
      exam_track_id: "trk-cbse",
      exam_track_code: "CBSE_BOARD",
      exam_track_name: "CBSE Board Examination",
      version_label: "cbse-board-2026-blueprint-v2",
      effective_year: 2026,
      is_active: true,
      rules: {
        duration_seconds: 10800,
        grace_seconds: 60,
        shuffle_questions: false,
        shuffle_options: false,
        retake_policy: { max_attempts: null, cooldown_minutes: 0 },
        sections: [
          {
            code: "SEC-A",
            name: "MCQ & Assertion-Reason",
            question_count: 20,
            attempt_limit: null,
            allowed_question_types: ["mcq_single", "assertion_reason"],
            difficulty_distribution: {},
            question_type_distribution: {},
            scoring: {
              mode: "standard",
              correct_marks: 1,
              wrong_marks: 0,
              unanswered_marks: 0,
              partial_credit_per_correct_option: 0,
            },
          },
        ],
      },
    },
    patterns: [],
    coverage_audit: {
      exam_code: "CBSE_BOARD",
      mapped_chapters_count: 2,
      included_chapters_count: 2,
      audited_chapters_count: 1,
      chapters_with_questions_count: 1,
      published_question_count: 15,
      verified_pyq_count: 2,
      unverified_pyq_excluded_count: 0,
      audited_coverage_pct: 50,
      question_coverage_pct: 50,
      coverage_status: "audited_partial",
      coverage_disclaimer:
        "Partial audited coverage: complete exam coverage is not claimed.",
    },
  },
  {
    id: "trk-jee-main",
    code: "JEE_MAIN",
    name: "JEE Main",
    target_seconds_per_question: 144,
    active_pattern: {
      id: "pat-jee-main",
      exam_track_id: "trk-jee-main",
      exam_track_code: "JEE_MAIN",
      exam_track_name: "JEE Main",
      version_label: "jee-main-2026-nta-v2",
      effective_year: 2026,
      is_active: true,
      rules: {
        duration_seconds: 10800,
        grace_seconds: 30,
        shuffle_questions: true,
        shuffle_options: true,
        retake_policy: { max_attempts: null, cooldown_minutes: 0 },
        sections: [
          {
            code: "PHY-A",
            name: "Physics MCQ (+4/-1)",
            question_count: 20,
            attempt_limit: null,
            allowed_question_types: ["mcq_single"],
            difficulty_distribution: {},
            question_type_distribution: {},
            scoring: {
              mode: "standard",
              correct_marks: 4,
              wrong_marks: -1,
              unanswered_marks: 0,
              partial_credit_per_correct_option: 0,
            },
          },
          {
            code: "PHY-B",
            name: "Physics Numerical (+4/-1)",
            question_count: 5,
            attempt_limit: 5,
            allowed_question_types: ["numerical", "integer"],
            difficulty_distribution: {},
            question_type_distribution: {},
            scoring: {
              mode: "standard",
              correct_marks: 4,
              wrong_marks: -1,
              unanswered_marks: 0,
              partial_credit_per_correct_option: 0,
            },
          },
        ],
      },
    },
    patterns: [],
    coverage_audit: {
      exam_code: "JEE_MAIN",
      mapped_chapters_count: 2,
      included_chapters_count: 2,
      audited_chapters_count: 1,
      chapters_with_questions_count: 2,
      published_question_count: 24,
      verified_pyq_count: 4,
      unverified_pyq_excluded_count: 1,
      audited_coverage_pct: 50,
      question_coverage_pct: 100,
      coverage_status: "audited_partial",
      coverage_disclaimer:
        "Partial audited coverage: 1/2 chapters audited, 4 verified PYQs available. Complete exam coverage is not claimed.",
    },
  },
  {
    id: "trk-jee-adv",
    code: "JEE_ADVANCED",
    name: "JEE Advanced",
    target_seconds_per_question: 180,
    active_pattern: {
      id: "pat-jee-adv",
      exam_track_id: "trk-jee-adv",
      exam_track_code: "JEE_ADVANCED",
      exam_track_name: "JEE Advanced",
      version_label: "jee-adv-2026-p1-v2",
      effective_year: 2026,
      is_active: true,
      rules: {
        duration_seconds: 10800,
        grace_seconds: 30,
        shuffle_questions: true,
        shuffle_options: false,
        retake_policy: { max_attempts: null, cooldown_minutes: 0 },
        sections: [
          {
            code: "SEC-2",
            name: "One or More Correct",
            question_count: 9,
            attempt_limit: null,
            allowed_question_types: ["mcq_multiple"],
            difficulty_distribution: {},
            question_type_distribution: {},
            scoring: {
              mode: "jee_adv_partial",
              correct_marks: 4,
              wrong_marks: -2,
              unanswered_marks: 0,
              partial_credit_per_correct_option: 1,
            },
          },
        ],
      },
    },
    patterns: [],
    coverage_audit: {
      exam_code: "JEE_ADVANCED",
      mapped_chapters_count: 1,
      included_chapters_count: 1,
      audited_chapters_count: 0,
      chapters_with_questions_count: 1,
      published_question_count: 6,
      verified_pyq_count: 0,
      unverified_pyq_excluded_count: 0,
      audited_coverage_pct: 0,
      question_coverage_pct: 100,
      coverage_status: "partial_unverified",
      coverage_disclaimer: "Coverage is currently unverified.",
    },
  },
  {
    id: "trk-neet",
    code: "NEET",
    name: "NEET-UG",
    target_seconds_per_question: 60,
    active_pattern: null,
    patterns: [],
    coverage_audit: {
      exam_code: "NEET",
      mapped_chapters_count: 0,
      included_chapters_count: 0,
      audited_chapters_count: 0,
      chapters_with_questions_count: 0,
      published_question_count: 0,
      verified_pyq_count: 0,
      unverified_pyq_excluded_count: 0,
      audited_coverage_pct: 0,
      question_coverage_pct: 0,
      coverage_status: "empty",
      coverage_disclaimer: "No syllabus chapters mapped yet.",
    },
  },
];

// Hydrate patterns array on tracks cleanly
for (const t of MOCK_TRACKS) {
  if (t.active_pattern) {
    (t.patterns as unknown[]).push(t.active_pattern);
  }
}

describe("Phase 9: Examination Preparation Ecosystem (/exams)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockRouter.push.mockReset();
  });

  it("renders all 4 tracks, honest coverage audit, verified PYQs, timed mock rules, detailed solutions, analytics, and revision plans", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/v1/exam-prep/tracks")) {
        return new Response(JSON.stringify(MOCK_TRACKS), { status: 200 });
      }
      if (url.includes("/syllabus")) {
        return new Response(
          JSON.stringify({
            exam_code: "JEE_MAIN",
            exam_name: "JEE Main",
            pattern_version_label: "jee-main-2026-nta-v2",
            coverage_audit: MOCK_TRACKS[1].coverage_audit,
            chapters: [
              {
                id: "syl-1",
                exam_track_id: "trk-jee-main",
                pattern_version_label: "jee-main-2026-nta-v2",
                subject_id: "sub-phy",
                subject_name: "Physics",
                chapter_id: "ch-elec",
                chapter_title: "Electrostatics",
                weightage_pct: 8.5,
                expected_questions: 2,
                priority_tier: "high_yield",
                syllabus_status: "included",
                notes: "Focus on Gauss Law and electric dipole torque.",
                audit_verified: true,
                audited_at: "2026-11-25T10:00:00Z",
                published_question_count: 12,
                verified_pyq_count: 4,
                topics: [{ id: "top-gauss", title: "Gauss Law" }],
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.includes("/questions")) {
        return new Response(
          JSON.stringify({
            exam_code: "JEE_MAIN",
            verified_pyq_only: true,
            facets: {
              available_years: [2024, 2023],
              available_sessions: ["January", "April"],
              available_difficulties: ["medium", "hard"],
              available_question_types: ["mcq_single", "numerical"],
              total_published_questions: 24,
              total_verified_pyqs: 4,
              unverified_pyq_excluded_count: 1,
            },
            questions: [
              {
                question_id: "q-pyq-1",
                question_version_id: "qv-pyq-1",
                question_type: "mcq_single",
                subject_id: "sub-phy",
                subject_name: "Physics",
                chapter_id: "ch-elec",
                chapter_title: "Electrostatics",
                topic_id: "top-gauss",
                topic_title: "Gauss Law",
                concept_id: null,
                concept_title: null,
                stem_markdown:
                  "A point charge $q$ is placed at the centre of a cube. Find flux through one face.",
                difficulty: "medium",
                default_marks: 4,
                default_negative_marks: 1,
                estimated_seconds: 90,
                options: [
                  { option_key: "A", content_markdown: "$q / 6\\varepsilon_0$" },
                  { option_key: "B", content_markdown: "$q / \\varepsilon_0$" },
                ],
                pyq_provenance: {
                  is_verified_pyq: true,
                  badge_label: "JEE Main · 2024 · January · Shift 1",
                  exam_name: "JEE Main",
                  exam_year: 2024,
                  exam_session: "January",
                  exam_shift: "Shift 1",
                  paper_code: "JM24-J1",
                  question_number: "7",
                  source_url: null,
                  verification_status: "verified",
                },
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.includes("/analytics")) {
        return new Response(
          JSON.stringify({
            exam_code: "JEE_MAIN",
            exam_name: "JEE Main",
            total_attempts: 2,
            total_questions_answered: 20,
            overall_accuracy_pct: 62.5,
            average_seconds_per_question: 158,
            target_seconds_per_question: 144,
            pacing_status: "slow_needs_drill",
            weak_subjects: [
              {
                entity_id: "sub-phy",
                name: "Physics",
                attempts: 10,
                correct: 5,
                accuracy_pct: 50,
                avg_seconds: 165,
                severity: "needs_focus",
              },
            ],
            weak_chapters: [
              {
                entity_id: "ch-elec",
                name: "Electrostatics",
                attempts: 5,
                correct: 2,
                accuracy_pct: 40,
                avg_seconds: 180,
                severity: "critical",
              },
            ],
            weak_concepts: [],
            performance_history: [
              {
                attempt_id: "att-101",
                title: "JEE Main Timed Mock (jee-main-2026-nta-v2)",
                category: "jee_main",
                submitted_at: "2026-11-24T10:00:00Z",
                raw_score: 48,
                max_score: 100,
                accuracy_pct: 62.5,
                avg_seconds_per_question: 158,
              },
            ],
            improvement_recommendations: [
              "Prioritize chapter 'Electrostatics' (40.0% accuracy) with formula revision.",
            ],
          }),
          { status: 200 }
        );
      }
      if (url.includes("/formulas")) {
        return new Response(
          JSON.stringify([
            {
              id: "form-1",
              exam_track_id: "trk-jee-main",
              subject_id: "sub-phy",
              subject_name: "Physics",
              chapter_id: "ch-elec",
              chapter_title: "Electrostatics",
              topic_id: "top-gauss",
              topic_title: "Gauss Law",
              title: "Gauss's Law in Vacuum",
              formula_latex: "\\Phi = \\frac{q_{enc}}{\\varepsilon_0}",
              variables: [
                { symbol: "q_{enc}", meaning: "Enclosed charge", unit: "C" },
              ],
              when_to_use: "Closed Gaussian surfaces with symmetry.",
              common_pitfall: "Forgetting negative charges inside the surface.",
              difficulty: "medium",
              is_high_yield: true,
              status: "PUBLISHED",
            },
          ]),
          { status: 200 }
        );
      }
      if (url.includes("/revision-plans") && method === "GET") {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/revision-plans") && method === "POST") {
        return new Response(
          JSON.stringify({
            id: "plan-1",
            exam_track_id: "trk-jee-main",
            exam_code: "JEE_MAIN",
            exam_pattern_id: "pat-jee-main",
            title: "JEE Main Final Sprint",
            target_exam_date: "2026-12-10",
            daily_minutes: 120,
            focus_chapters: [],
            schedule: [
              {
                day_number: 1,
                date: "2026-11-27",
                total_minutes: 120,
                blocks: [
                  {
                    activity: "formula_revision",
                    title: "Formula & Key Concept Sheet: Electrostatics",
                    minutes: 30,
                    chapter_id: "ch-elec",
                    focus_note: "Physics · high yield",
                  },
                ],
              },
            ],
            status: "active",
            created_at: "2026-11-26T14:00:00Z",
          }),
          { status: 201 }
        );
      }
      if (url.includes("/attempts/att-101/solutions")) {
        return new Response(
          JSON.stringify({
            attempt_id: "att-101",
            title: "JEE Main Timed Mock (jee-main-2026-nta-v2)",
            status: "submitted",
            raw_score: 48,
            max_score: 100,
            accuracy_pct: 62.5,
            submitted_at: "2026-11-24T10:00:00Z",
            items: [
              {
                sequence_no: 1,
                question_id: "q-pyq-1",
                question_version_id: "qv-pyq-1",
                question_type: "mcq_single",
                subject_name: "Physics",
                chapter_title: "Electrostatics",
                stem_markdown: "Find flux through one face of a cube.",
                options: [],
                student_response_jsonb: { selected_key: "B" },
                correct_answer_jsonb: { correct_key: "A" },
                is_correct: false,
                marks_awarded: -1,
                time_spent_seconds: 120,
                explanation_markdown:
                  "By symmetry, each of the 6 faces shares 1/6th of total flux.",
                steps: ["Total flux = q/e0", "Flux per face = q/(6e0)"],
                common_mistakes_markdown: "Dividing by 4 instead of 6 faces.",
              },
            ],
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<ExamPrepPage />);

    // 1. All 4 tracks & honest coverage audit render
    await waitFor(() => {
      expect(screen.getByText("CBSE Board")).toBeInTheDocument();
      expect(screen.getByText("JEE Main")).toBeInTheDocument();
      expect(screen.getByText("JEE Advanced")).toBeInTheDocument();
      expect(screen.getByText("NEET-UG")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Complete exam coverage is not claimed/i)
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Electrostatics")).toBeInTheDocument();
    });

    // 2. Switch to Verified PYQ tab & verify provenance badge + exclusion guard
    fireEvent.click(screen.getByRole("tab", { name: /Verified PYQs/i }));
    await waitFor(() => {
      expect(
        screen.getByText(/Verified PYQ · JEE Main · 2024 · January · Shift 1/i)
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/Provenance Guard Active/i)).toBeInTheDocument();

    // 3. Switch to Timed Mocks & open Detailed Solutions
    fireEvent.click(screen.getByRole("tab", { name: /Timed Mocks/i }));
    await waitFor(() => {
      expect(screen.getByText(/Physics Numerical \(\+4\/-1\)/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Detailed Solutions" }));
    await waitFor(() => {
      expect(
        screen.getByText(/Dividing by 4 instead of 6 faces/i)
      ).toBeInTheDocument();
    });

    // 4. Switch to Exam Analytics & verify pacing + weak chapters
    fireEvent.click(screen.getByRole("tab", { name: /Exam Analytics/i }));
    await waitFor(() => {
      expect(screen.getByText("62.5%")).toBeInTheDocument();
      expect(screen.getByText("158s/Q")).toBeInTheDocument();
      expect(screen.getByText(/Needs Speed & Concept Drill/i)).toBeInTheDocument();
    });

    // 5. Switch to Formulas & Revision Plans & generate a plan
    fireEvent.click(screen.getByRole("tab", { name: /Formulas & Revision/i }));
    await waitFor(() => {
      expect(screen.getByText("Gauss's Law in Vacuum")).toBeInTheDocument();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Build Revision Schedule/i })
    );
    await waitFor(() => {
      expect(screen.getByText("JEE Main Final Sprint")).toBeInTheDocument();
    });
  });
});
