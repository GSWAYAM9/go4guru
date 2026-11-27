import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MentorHubPage from "@/app/mentor/page";
import ParentPortalPage from "@/app/parent/page";
import TeacherHubPage from "@/app/teacher/page";

const mockRouter = { push: vi.fn(), replace: vi.fn() };
let mockUserRoles: string[] = ["teacher"];

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-jwt-token",
    user: {
      id: "user-1",
      email: "educator@example.com",
      display_name: "Educator User",
      roles: mockUserRoles,
      permissions: [],
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

describe("Phase 7: Teacher, Mentor & Parent Workspaces", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Teacher Hub and saves a Teacher Override grade over AI draft", async () => {
    mockUserRoles = ["teacher"];
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input, init) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/v1/teacher/dashboard")) {
          return new Response(
            JSON.stringify({
              teacher_id: "user-1",
              total_classes: 1,
              total_students: 24,
              total_assignments: 1,
              pending_reviews_count: 1,
              classes: [
                {
                  id: "cls-1",
                  tenant_id: null,
                  teacher_id: "user-1",
                  name: "Class 10 CBSE Math",
                  grade_label: "Class 10",
                  subject_name: "Mathematics",
                  status: "active",
                  sections_count: 1,
                  students_count: 24,
                  assignments_count: 1,
                  created_at: "2026-11-26T10:00:00Z",
                },
              ],
              recent_assignments: [],
            }),
            { status: 200 }
          );
        }
        if (url.includes("/api/v1/teacher/question-bank")) {
          return new Response(JSON.stringify([]), { status: 200 });
        }
        if (url.endsWith("/classes/cls-1/sections")) {
          return new Response(JSON.stringify([]), { status: 200 });
        }
        if (url.endsWith("/classes/cls-1/students")) {
          return new Response(JSON.stringify([]), { status: 200 });
        }
        if (url.includes("/api/v1/teacher/assignments?class_id=cls-1")) {
          return new Response(
            JSON.stringify([
              {
                id: "asgn-1",
                class_id: "cls-1",
                section_id: null,
                teacher_id: "user-1",
                title: "Quadratic Equations Quiz",
                instructions: "Show all steps",
                assignment_type: "quiz",
                question_ids: [],
                max_marks: 20,
                due_at: null,
                status: "published",
                submissions_count: 1,
                graded_count: 0,
                created_at: "2026-11-26T10:00:00Z",
              },
            ]),
            { status: 200 }
          );
        }
        if (url.endsWith("/classes/cls-1/analytics")) {
          return new Response(
            JSON.stringify({
              class_id: "cls-1",
              class_name: "Class 10 CBSE Math",
              total_students: 24,
              total_assignments: 1,
              total_submissions: 1,
              graded_submissions: 0,
              average_score_pct: 75,
              average_mastery_pct: 68,
              weak_concepts: [],
            }),
            { status: 200 }
          );
        }
        if (url.endsWith("/assignments/asgn-1/submissions")) {
          return new Response(
            JSON.stringify([
              {
                id: "sub-1",
                assignment_id: "asgn-1",
                student_id: "stu-1",
                student_name: "Aarav Sharma",
                student_email: "aarav@school.edu",
                response_text: "Step 1: Factor (x-2)(x-3)=0 -> x=2, 3.",
                ai_suggested_score: 16,
                ai_feedback_summary: "AI Draft: Good algebraic method.",
                teacher_score: null,
                teacher_override_reason: null,
                teacher_feedback: null,
                effective_score: 16,
                max_marks: 20,
                status: "ai_graded",
                graded_by: null,
                graded_at: null,
                created_at: "2026-11-26T10:00:00Z",
              },
            ]),
            { status: 200 }
          );
        }
        if (url.endsWith("/submissions/sub-1/override") && method === "PATCH") {
          return new Response(
            JSON.stringify({
              id: "sub-1",
              assignment_id: "asgn-1",
              student_id: "stu-1",
              student_name: "Aarav Sharma",
              student_email: "aarav@school.edu",
              response_text: "Step 1: Factor (x-2)(x-3)=0 -> x=2, 3.",
              ai_suggested_score: 16,
              ai_feedback_summary: "AI Draft: Good algebraic method.",
              teacher_score: 19,
              teacher_override_reason: "Complete working shown",
              teacher_feedback: "Great job!",
              effective_score: 19,
              max_marks: 20,
              status: "returned",
              graded_by: "user-1",
              graded_at: "2026-11-26T11:00:00Z",
              created_at: "2026-11-26T10:00:00Z",
            }),
            { status: 200 }
          );
        }
        return new Response(JSON.stringify({}), { status: 200 });
      }
    );

    render(<TeacherHubPage />);

    await waitFor(() => {
      expect(screen.getByText("Teacher Hub")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("tab", { name: /Submissions & Override/i }));

    await waitFor(() => {
      expect(screen.getByText("Aarav Sharma")).toBeTruthy();
    });

    const scoreInput = screen.getByLabelText(/Teacher score for Aarav Sharma/i);
    fireEvent.change(scoreInput, { target: { value: "19" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Teacher Override/i }));

    await waitFor(() => {
      expect(screen.getByText(/Teacher grade saved \(19\/20\)/i)).toBeTruthy();
    });
    expect(fetchMock).toHaveBeenCalled();
  });

  it("renders Mentor Hub with assigned student review and interventions", async () => {
    mockUserRoles = ["mentor"];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/mentor/dashboard")) {
        return new Response(
          JSON.stringify({
            mentor_id: "user-1",
            assigned_students_count: 1,
            active_goals_count: 2,
            upcoming_sessions_count: 1,
            open_follow_ups_count: 1,
            students: [
              {
                assignment_id: "ma-1",
                student_id: "stu-1",
                student_name: "Diya Verma",
                student_email: "diya@school.edu",
                status: "active",
                notes: "NEET focus",
                active_goals_count: 2,
                open_follow_ups_count: 1,
                created_at: "2026-11-26T09:00:00Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/api/v1/mentor/students/stu-1/review")) {
        return new Response(
          JSON.stringify({
            student_id: "stu-1",
            student_name: "Diya Verma",
            student_email: "diya@school.edu",
            primary_exam_target: "neet",
            daily_study_minutes_target: 90,
            practice_total_attempts: 40,
            practice_accuracy_pct: 72.5,
            mastery_average_pct: 64.0,
            weak_concepts: [],
            due_flashcards_count: 8,
            active_study_plans_count: 1,
            completed_plan_items_count: 5,
            homework_evaluated_count: 3,
            recommended_interventions: [
              "Clear 8 overdue spaced-repetition flashcard(s) this week.",
            ],
            goals: [],
            sessions: [],
            follow_ups: [],
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<MentorHubPage />);

    await waitFor(() => {
      expect(screen.getByText("Mentor Hub")).toBeTruthy();
      expect(
        screen.getByText(/Clear 8 overdue spaced-repetition flashcard/i)
      ).toBeTruthy();
    });
  });

  it("renders Parent Portal with child-safety boundary and verified summary", async () => {
    mockUserRoles = ["parent"];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/parent/dashboard")) {
        return new Response(
          JSON.stringify({
            parent_user_id: "user-1",
            active_goals_count: 1,
            verified_links_count: 1,
            pending_links_count: 0,
            linked_students: [
              {
                id: "link-1",
                parent_user_id: "user-1",
                student_user_id: "stu-1",
                student_name: "Aarav Sharma",
                student_email: "aarav@school.edu",
                relationship_type: "parent",
                consent_status: "verified",
                consent_granted_at: "2026-11-26T09:00:00Z",
                revoked_at: null,
                privacy_settings: {
                  share_learning_summary: true,
                  share_weak_topics: true,
                  share_upcoming_tests: true,
                  allow_raw_ai_transcripts: false,
                },
                created_at: "2026-11-26T08:00:00Z",
              },
            ],
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/api/v1/parent/students/stu-1/summary")) {
        return new Response(
          JSON.stringify({
            student_user_id: "stu-1",
            student_name: "Aarav Sharma",
            consent_status: "verified",
            privacy_notice: "Raw AI transcripts excluded.",
            privacy_settings: {
              share_learning_summary: true,
              share_weak_topics: true,
              share_upcoming_tests: true,
              allow_raw_ai_transcripts: false,
            },
            onboarding_completed: true,
            primary_exam_target: "cbse_board",
            daily_study_minutes_target: 60,
            practice_total_attempts: 50,
            practice_correct_attempts: 42,
            practice_accuracy_pct: 84,
            practice_sessions_completed: 6,
            mastery_average_pct: 79,
            mastered_concepts_count: 5,
            weak_topics: [],
            revision_due_flashcards: 4,
            revision_total_flashcards: 25,
            revision_active_study_plans: 1,
            revision_completed_plan_items: 9,
            homework_total_submissions: 4,
            homework_evaluated_submissions: 4,
            upcoming_assessments: [
              {
                id: "a-1",
                title: "Physics Optics Unit Test",
                assignment_type: "test",
                due_at: "2026-12-01T10:00:00Z",
                max_marks: 50,
              },
            ],
            goals: [],
            generated_at: "2026-11-26T10:00:00Z",
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<ParentPortalPage />);

    await waitFor(() => {
      expect(screen.getByText("Parent & Guardian Dashboard")).toBeTruthy();
      expect(screen.getByText("Locked Off")).toBeTruthy();
      expect(screen.getByText("Physics Optics Unit Test")).toBeTruthy();
    });
  });
});
