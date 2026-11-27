import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import InstitutionConsolePage from "@/app/institution/page";

const mockRouter = { push: vi.fn(), replace: vi.fn() };

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-admin-jwt",
    user: {
      id: "admin-1",
      email: "admin@alpha.edu",
      display_name: "Principal Admin",
      roles: ["school_admin"],
      permissions: [
        "org:manage_tenant",
        "org:manage_staff",
        "org:manage_enrollments",
        "org:view_reports",
        "billing:manage_subscription",
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

describe("Phase 8: Multi-Tenant Institution Administration Console", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders tenant report, school breakdown, and subscription plan controls", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/org/organizations")) {
        return new Response(
          JSON.stringify([
            {
              id: "org-1",
              slug: "alpha-schools",
              name: "Alpha Public Schools",
              organization_type: "school_group",
              status: "active",
              contact_email: "admin@alpha.edu",
              config: {
                default_language: "en",
                allow_ai_tutor: true,
                allow_homework_ai: true,
                require_mfa_for_admins: true,
                allow_parent_portal: true,
              },
              plan_code: "school_starter",
              plan_name: "School Starter",
              subscription_status: "active",
              seat_limit: 150,
              max_teachers: 20,
              max_branches: 2,
              entitlements: { ai_tutor: true, homework_ai: true },
              created_at: "2026-11-26T09:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }
      if (url.endsWith("/api/v1/billing/plans")) {
        return new Response(
          JSON.stringify([
            {
              id: "plan-1",
              code: "school_starter",
              name: "School Starter",
              tier: "starter",
              monthly_price_inr: 9999,
              max_students: 150,
              max_teachers: 20,
              max_branches: 2,
              entitlements: { ai_tutor: true },
              is_active: true,
            },
            {
              id: "plan-2",
              code: "school_growth",
              name: "School Growth",
              tier: "growth",
              monthly_price_inr: 24999,
              max_students: 1000,
              max_teachers: 100,
              max_branches: 10,
              entitlements: { ai_tutor: true, live_classroom: true },
              is_active: true,
            },
          ]),
          { status: 200 }
        );
      }
      if (url.endsWith("/organizations/org-1/reports")) {
        return new Response(
          JSON.stringify({
            tenant_id: "org-1",
            organization_name: "Alpha Public Schools",
            plan_code: "school_starter",
            subscription_status: "active",
            schools_count: 1,
            branches_count: 1,
            max_branches: 2,
            batches_count: 3,
            teachers_count: 8,
            max_teachers: 20,
            mentors_count: 2,
            students_count: 112,
            seat_limit: 150,
            seat_utilization_pct: 74.67,
            assessments_count: 4,
            average_student_practice_accuracy_pct: 78.4,
            average_student_mastery_pct: 71.2,
            schools_breakdown: [
              {
                school_id: "sch-1",
                school_name: "Alpha North Campus",
                board_code: "CBSE",
                branches_count: 1,
                batches_count: 3,
                assessments_count: 4,
              },
            ],
            generated_at: "2026-11-26T10:00:00Z",
          }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    render(<InstitutionConsolePage />);

    await waitFor(() => {
      expect(screen.getByText("Institution Administration Console")).toBeTruthy();
      expect(screen.getByText("Alpha North Campus")).toBeTruthy();
      expect(screen.getByText("112 / 150")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("tab", { name: /Config & Plan/i }));

    await waitFor(() => {
      expect(screen.getByText("School Growth")).toBeTruthy();
      expect(screen.getByText(/Enable Curriculum AI Tutor/i)).toBeTruthy();
    });
  });
});
