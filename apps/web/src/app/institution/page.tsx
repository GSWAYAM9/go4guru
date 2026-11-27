"use client";

import type {
  AcademicYearOut,
  BranchOut,
  InstitutionAssessmentOut,
  InstitutionBatchOut,
  InstitutionMemberOut,
  InstitutionReportOut,
  OrganizationOut,
  SchoolOut,
  SubscriptionPlanOut,
} from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard, StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  addOrgMember,
  createOrgAcademicYear,
  createOrgAssessment,
  createOrgBatch,
  createOrgBranch,
  createOrganization,
  createOrgSchool,
  enrollOrgBatchStudent,
  fetchOrgReport,
  fetchOrgReportCsv,
  listOrgAcademicYears,
  listOrganizations,
  listOrgAssessments,
  listOrgBatches,
  listOrgBranches,
  listOrgMembers,
  listOrgSchools,
  listSubscriptionPlans,
  updateOrganizationConfig,
  updateTenantSubscription,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  evaluateSeatQuotaHealth,
  sanitizeSlugInput,
  triggerCsvDownload,
} from "@/lib/ecosystem-helpers";

type InstTab =
  | "overview"
  | "schools"
  | "batches"
  | "staff"
  | "assessments"
  | "config";

export default function InstitutionConsolePage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();

  const [tab, setTab] = useState<InstTab>("overview");
  const [orgs, setOrgs] = useState<OrganizationOut[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [plans, setPlans] = useState<SubscriptionPlanOut[]>([]);
  const [schools, setSchools] = useState<SchoolOut[]>([]);
  const [branches, setBranches] = useState<BranchOut[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYearOut[]>([]);
  const [batches, setBatches] = useState<InstitutionBatchOut[]>([]);
  const [members, setMembers] = useState<InstitutionMemberOut[]>([]);
  const [assessments, setAssessments] = useState<InstitutionAssessmentOut[]>(
    []
  );
  const [report, setReport] = useState<InstitutionReportOut | null>(null);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Onboarding form
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [orgEmail, setOrgEmail] = useState("");
  const [orgType, setOrgType] = useState<
    "school_group" | "coaching_institute" | "standalone_school"
  >("school_group");
  const [orgPlanCode, setOrgPlanCode] = useState("school_starter");

  // School & Branch forms
  const [schoolCode, setSchoolCode] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [schoolBoard, setSchoolBoard] = useState("CBSE");
  const [schoolCity, setSchoolCity] = useState("");

  const [branchSchoolId, setBranchSchoolId] = useState("");
  const [branchCode, setBranchCode] = useState("");
  const [branchName, setBranchName] = useState("");

  // Academic Year & Batch forms
  const [aySchoolId, setAySchoolId] = useState("");
  const [ayLabel, setAyLabel] = useState("2026-27");
  const [ayStart, setAyStart] = useState("2026-04-01");
  const [ayEnd, setAyEnd] = useState("2027-03-31");

  const [batchSchoolId, setBatchSchoolId] = useState("");
  const [batchName, setBatchName] = useState("");
  const [batchGrade, setBatchGrade] = useState("Class 11");
  const [batchSection, setBatchSection] = useState("A");
  const [batchTrack, setBatchTrack] = useState("jee_main");

  // Staff & Student Enrollment forms
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState<
    "school_admin" | "teacher" | "mentor" | "student"
  >("teacher");
  const [enrollBatchId, setEnrollBatchId] = useState("");
  const [enrollStudentEmail, setEnrollStudentEmail] = useState("");
  const [enrollRollNo, setEnrollRollNo] = useState("");

  // Institution Assessment form
  const [asmtSchoolId, setAsmtSchoolId] = useState("");
  const [asmtBatchId, setAsmtBatchId] = useState("");
  const [asmtTitle, setAsmtTitle] = useState("");
  const [asmtKind, setAsmtKind] = useState<"assignment" | "test">("test");
  const [asmtMaxMarks, setAsmtMaxMarks] = useState("100");

  const selectedOrg = orgs.find((o) => o.id === selectedOrgId) ?? null;

  const loadOrgDetails = useCallback(async (authToken: string, orgId: string) => {
    const [sc, br, ay, bt, mb, asmt, rpt] = await Promise.all([
      listOrgSchools(authToken, orgId),
      listOrgBranches(authToken, orgId),
      listOrgAcademicYears(authToken, orgId),
      listOrgBatches(authToken, orgId),
      listOrgMembers(authToken, orgId),
      listOrgAssessments(authToken, orgId),
      fetchOrgReport(authToken, orgId),
    ]);
    setSchools(sc);
    setBranches(br);
    setAcademicYears(ay);
    setBatches(bt);
    setMembers(mb);
    setAssessments(asmt);
    setReport(rpt);
    if (sc[0]) {
      setBranchSchoolId((prev) => prev || sc[0].id);
      setAySchoolId((prev) => prev || sc[0].id);
      setBatchSchoolId((prev) => prev || sc[0].id);
      setAsmtSchoolId((prev) => prev || sc[0].id);
    }
    if (bt[0]) {
      setEnrollBatchId((prev) => prev || bt[0].id);
    }
  }, []);

  const selectedOrgIdRef = useRef(selectedOrgId);
  selectedOrgIdRef.current = selectedOrgId;

  const loadConsole = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [orgList, planList] = await Promise.all([
        listOrganizations(token),
        listSubscriptionPlans(token).catch(() => []),
      ]);
      setOrgs(orgList);
      setPlans(planList);
      const nextOrgId = selectedOrgIdRef.current || orgList[0]?.id || "";
      if (nextOrgId) {
        selectedOrgIdRef.current = nextOrgId;
        setSelectedOrgId(nextOrgId);
        await loadOrgDetails(token, nextOrgId);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load Institution Console."
      );
    } finally {
      setLoading(false);
    }
  }, [token, loadOrgDetails]);

  useEffect(() => {
    if (!initializing && !token) {
      router.replace("/login");
    }
  }, [initializing, token, router]);

  useEffect(() => {
    if (token) {
      void loadConsole();
    }
  }, [token, loadConsole]);

  async function handleSelectOrg(orgId: string) {
    setSelectedOrgId(orgId);
    if (!token || !orgId) return;
    setBusy(true);
    setError(null);
    try {
      await loadOrgDetails(token, orgId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load tenant records."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleOnboardOrg(e: FormEvent) {
    e.preventDefault();
    if (!token || !orgName.trim() || !orgEmail.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createOrganization(token, {
        name: orgName.trim(),
        slug: sanitizeSlugInput(orgSlug || orgName),
        organization_type: orgType,
        contact_email: orgEmail.trim(),
        plan_code: orgPlanCode,
      });
      setOrgName("");
      setOrgSlug("");
      setOrgEmail("");
      setSelectedOrgId(created.id);
      setNotice(`Onboarded tenant "${created.name}" (${created.plan_name}).`);
      await loadConsole();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Organization onboarding failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateSchool(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId) return;
    setBusy(true);
    setError(null);
    try {
      await createOrgSchool(token, selectedOrgId, {
        code: schoolCode.trim(),
        name: schoolName.trim(),
        board_code: schoolBoard.trim(),
        city: schoolCity.trim() || undefined,
      });
      setSchoolCode("");
      setSchoolName("");
      setSchoolCity("");
      setNotice("School added under tenant boundary.");
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create school.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateBranch(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId || !branchSchoolId) return;
    setBusy(true);
    setError(null);
    try {
      await createOrgBranch(token, selectedOrgId, {
        school_id: branchSchoolId,
        code: branchCode.trim(),
        name: branchName.trim(),
      });
      setBranchCode("");
      setBranchName("");
      setNotice("Branch created.");
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create branch.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateAcademicYear(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId || !aySchoolId) return;
    setBusy(true);
    setError(null);
    try {
      await createOrgAcademicYear(token, selectedOrgId, {
        school_id: aySchoolId,
        label: ayLabel.trim(),
        starts_on: ayStart,
        ends_on: ayEnd,
        is_current: true,
      });
      setNotice(`Academic year ${ayLabel} created.`);
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create academic year."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateBatch(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId || !batchSchoolId) return;
    setBusy(true);
    setError(null);
    try {
      await createOrgBatch(token, selectedOrgId, {
        school_id: batchSchoolId,
        name: batchName.trim(),
        grade_label: batchGrade.trim(),
        section_name: batchSection.trim(),
        exam_track: batchTrack.trim(),
      });
      setBatchName("");
      setNotice("Batch created.");
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create batch.");
    } finally {
      setBusy(false);
    }
  }

  async function handleAddMember(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId || !memberEmail.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await addOrgMember(token, selectedOrgId, {
        user_email: memberEmail.trim(),
        member_role: memberRole,
      });
      setMemberEmail("");
      setNotice(`Added ${memberRole} to tenant roster.`);
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not add tenant member."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleBatchEnroll(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId || !enrollBatchId || !enrollStudentEmail.trim())
      return;
    setBusy(true);
    setError(null);
    try {
      await enrollOrgBatchStudent(token, selectedOrgId, enrollBatchId, {
        student_email: enrollStudentEmail.trim(),
        roll_no: enrollRollNo.trim() || null,
      });
      setEnrollStudentEmail("");
      setEnrollRollNo("");
      setNotice("Student enrolled in batch.");
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch enrollment failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateAssessment(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedOrgId || !asmtSchoolId || !asmtTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createOrgAssessment(token, selectedOrgId, {
        school_id: asmtSchoolId,
        batch_id: asmtBatchId || null,
        title: asmtTitle.trim(),
        kind: asmtKind,
        max_marks: Number(asmtMaxMarks) || 100,
      });
      setAsmtTitle("");
      setNotice("Institutional assessment published.");
      await loadOrgDetails(token, selectedOrgId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create assessment."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleConfig(
    key: "allow_ai_tutor" | "allow_homework_ai" | "require_mfa_for_admins" | "allow_parent_portal"
  ) {
    if (!token || !selectedOrg) return;
    setBusy(true);
    setError(null);
    try {
      const current = Boolean(selectedOrg.config[key]);
      await updateOrganizationConfig(token, selectedOrg.id, {
        [key]: !current,
      });
      setNotice("Tenant configuration updated.");
      await loadConsole();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update configuration."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleChangePlan(planCode: string) {
    if (!token || !selectedOrgId) return;
    setBusy(true);
    setError(null);
    try {
      await updateTenantSubscription(token, selectedOrgId, {
        plan_code: planCode,
        status: "active",
      });
      setNotice(`Subscription plan updated to ${planCode}.`);
      await loadConsole();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Subscription update failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleExportOrgCsv() {
    if (!token || !selectedOrgId) return;
    setBusy(true);
    try {
      const csv = await fetchOrgReportCsv(token, selectedOrgId);
      triggerCsvDownload(`institution_report_${selectedOrgId.slice(0, 8)}.csv`, csv);
      setNotice("Tenant report CSV downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report export failed.");
    } finally {
      setBusy(false);
    }
  }

  if (initializing || loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <LoadingCard message="Loading Institution Console..." />
      </main>
    );
  }

  const canAccess = user?.roles.some((r) =>
    ["school_admin", "platform_admin"].includes(r)
  );
  if (!canAccess) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <ErrorBanner
          title="Institution administration access required"
          message="Your account must hold school_admin or platform_admin permissions."
        />
        <div className="mt-4">
          <Link href="/dashboard" className="text-sm font-medium text-indigo-700 underline">
            Return to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  const quotaHealth = report
    ? evaluateSeatQuotaHealth(
        report.students_count,
        report.seat_limit,
        report.subscription_status
      )
    : null;

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Multi-Tenant Institutional Platform
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Institution Administration Console
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Tenant-scoped organizations, schools, branches, academic years, batches, staff, enrollments, assessments, and subscription entitlements.
          </p>
        </div>
        {selectedOrgId && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleExportOrgCsv()}
            className="shrink-0 whitespace-nowrap rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Export Institution CSV
          </button>
        )}
      </header>

      {error && <ErrorBanner title="Action failed" message={error} />}
      {notice && (
        <div
          role="status"
          className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900"
        >
          {notice}
        </div>
      )}

      {/* Tenant Selector + Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <label
            htmlFor="org-tenant-select"
            className="text-xs font-semibold uppercase tracking-wide text-slate-600"
          >
            Tenant
          </label>
          <select
            id="org-tenant-select"
            value={selectedOrgId}
            onChange={(e) => void handleSelectOrg(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
          >
            <option value="">Select organization...</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name} ({o.slug})
              </option>
            ))}
          </select>
          {selectedOrg && (
            <StatusBadge tone="healthy">
              {selectedOrg.plan_name ?? "Starter"}
            </StatusBadge>
          )}
        </div>

        <div className="flex flex-wrap gap-1" role="tablist">
          {(
            [
              ["overview", "Overview & Onboard"],
              ["schools", "Schools & Branches"],
              ["batches", "Years & Batches"],
              ["staff", "Staff & Enrollments"],
              ["assessments", "Tests & Assignments"],
              ["config", "Config & Plan"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`shrink-0 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition ${
                tab === id
                  ? "bg-indigo-700 text-white"
                  : "text-slate-700 hover:bg-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB: OVERVIEW & ONBOARDING */}
      {tab === "overview" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <section className="space-y-4 lg:col-span-7">
            {report ? (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {[
                    {
                      label: "Schools / Branches",
                      value: `${report.schools_count} / ${report.branches_count}`,
                    },
                    {
                      label: "Students / Seat Cap",
                      value: `${report.students_count} / ${report.seat_limit}`,
                    },
                    {
                      label: "Teachers / Mentors",
                      value: `${report.teachers_count} / ${report.mentors_count}`,
                    },
                    { label: "Active Batches", value: report.batches_count },
                    {
                      label: "Avg Practice Accuracy",
                      value: `${report.average_student_practice_accuracy_pct}%`,
                    },
                    {
                      label: "Avg Student Mastery",
                      value: `${report.average_student_mastery_pct}%`,
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="rounded-lg border border-slate-200 bg-white p-4"
                    >
                      <p className="text-xs text-slate-500">{item.label}</p>
                      <p className="mt-1 text-xl font-bold tabular-nums text-slate-900">
                        {item.value}
                      </p>
                    </div>
                  ))}
                </div>

                {quotaHealth?.warning && (
                  <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs text-amber-900">
                    {quotaHealth.warning}
                  </div>
                )}

                <div className="rounded-lg border border-slate-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-slate-900">
                    Tenant School Breakdown
                  </h2>
                  {report.schools_breakdown.length === 0 ? (
                    <p className="mt-2 text-xs text-slate-500">
                      No schools registered under this organization yet.
                    </p>
                  ) : (
                    <table className="mt-3 w-full text-left text-sm">
                      <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                        <tr>
                          <th className="py-2">School</th>
                          <th className="py-2">Board</th>
                          <th className="py-2 text-right">Branches</th>
                          <th className="py-2 text-right">Batches</th>
                          <th className="py-2 text-right">Tests</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {report.schools_breakdown.map((row) => (
                          <tr key={row.school_id}>
                            <td className="py-2 font-medium text-slate-900">
                              {row.school_name}
                            </td>
                            <td className="py-2 text-slate-600">
                              {row.board_code}
                            </td>
                            <td className="py-2 text-right tabular-nums">
                              {row.branches_count}
                            </td>
                            <td className="py-2 text-right tabular-nums">
                              {row.batches_count}
                            </td>
                            <td className="py-2 text-right tabular-nums">
                              {row.assessments_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            ) : (
              <EmptyState
                title="No institution tenant selected"
                description="Onboard a new organization on the right to provision its isolated tenant workspace."
              />
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 lg:col-span-5">
            <h2 className="text-base font-semibold text-slate-900">
              Onboard New Organization Tenant
            </h2>
            <form onSubmit={handleOnboardOrg} className="mt-3 space-y-3">
              <div>
                <label
                  htmlFor="org-name"
                  className="block text-xs font-medium text-slate-700"
                >
                  Organization Name
                </label>
                <input
                  id="org-name"
                  required
                  value={orgName}
                  onChange={(e) => {
                    setOrgName(e.target.value);
                    if (!orgSlug) setOrgSlug(sanitizeSlugInput(e.target.value));
                  }}
                  placeholder="Vidya Bharati Public Schools"
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="org-slug"
                  className="block text-xs font-medium text-slate-700"
                >
                  Tenant Slug
                </label>
                <input
                  id="org-slug"
                  required
                  value={orgSlug}
                  onChange={(e) => setOrgSlug(e.target.value)}
                  placeholder="vidya-bharati"
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono"
                />
              </div>
              <div>
                <label
                  htmlFor="org-email"
                  className="block text-xs font-medium text-slate-700"
                >
                  Admin Contact Email
                </label>
                <input
                  id="org-email"
                  type="email"
                  required
                  value={orgEmail}
                  onChange={(e) => setOrgEmail(e.target.value)}
                  placeholder="admin@vidyabharati.edu"
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={orgType}
                  onChange={(e) =>
                    setOrgType(
                      e.target.value as
                        | "school_group"
                        | "coaching_institute"
                        | "standalone_school"
                    )
                  }
                  className="rounded-md border border-slate-300 px-2.5 py-2 text-sm"
                >
                  <option value="school_group">School Group</option>
                  <option value="standalone_school">Standalone School</option>
                  <option value="coaching_institute">Coaching Institute</option>
                </select>
                <select
                  value={orgPlanCode}
                  onChange={(e) => setOrgPlanCode(e.target.value)}
                  className="rounded-md border border-slate-300 px-2.5 py-2 text-sm"
                >
                  <option value="school_starter">School Starter</option>
                  <option value="school_growth">School Growth</option>
                  <option value="school_enterprise">Enterprise</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Onboard Organization
              </button>
            </form>
          </section>
        </div>
      )}

      {/* TAB: SCHOOLS & BRANCHES */}
      {tab === "schools" && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Schools ({schools.length})
            </h2>
            <form onSubmit={handleCreateSchool} className="grid grid-cols-2 gap-2">
              <input
                required
                placeholder="Code (DPS-N)"
                value={schoolCode}
                onChange={(e) => setSchoolCode(e.target.value)}
                className="rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                required
                placeholder="Board (CBSE)"
                value={schoolBoard}
                onChange={(e) => setSchoolBoard(e.target.value)}
                className="rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                required
                placeholder="School Name"
                value={schoolName}
                onChange={(e) => setSchoolName(e.target.value)}
                className="col-span-2 rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                placeholder="City"
                value={schoolCity}
                onChange={(e) => setSchoolCity(e.target.value)}
                className="rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={busy || !selectedOrgId}
                className="rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Add School
              </button>
            </form>
            <ul className="space-y-2 text-sm">
              {schools.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{s.name}</p>
                    <p className="text-xs text-slate-500">
                      {s.code} · {s.board_code}
                      {s.city ? ` · ${s.city}` : ""}
                    </p>
                  </div>
                  <span className="text-xs tabular-nums text-slate-600">
                    {s.branches_count} branches · {s.batches_count} batches
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Branches ({branches.length}
              {report ? ` / ${report.max_branches}` : ""})
            </h2>
            <form onSubmit={handleCreateBranch} className="space-y-2">
              <select
                required
                value={branchSchoolId}
                onChange={(e) => setBranchSchoolId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select school...</option>
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input
                  required
                  placeholder="Branch Code"
                  value={branchCode}
                  onChange={(e) => setBranchCode(e.target.value)}
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                />
                <input
                  required
                  placeholder="Branch Name"
                  value={branchName}
                  onChange={(e) => setBranchName(e.target.value)}
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={busy || !branchSchoolId}
                className="w-full rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Add Branch
              </button>
            </form>
            <ul className="space-y-2 text-sm">
              {branches.map((b) => (
                <li
                  key={b.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2"
                >
                  <span className="font-medium text-slate-900">
                    {b.name} ({b.code})
                  </span>
                  <StatusBadge tone="healthy">{b.status}</StatusBadge>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}

      {/* TAB: ACADEMIC YEARS & BATCHES */}
      {tab === "batches" && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Academic Years ({academicYears.length})
            </h2>
            <form onSubmit={handleCreateAcademicYear} className="space-y-2">
              <select
                required
                value={aySchoolId}
                onChange={(e) => setAySchoolId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select school...</option>
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <input
                required
                value={ayLabel}
                onChange={(e) => setAyLabel(e.target.value)}
                placeholder="2026-27"
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  value={ayStart}
                  onChange={(e) => setAyStart(e.target.value)}
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  value={ayEnd}
                  onChange={(e) => setAyEnd(e.target.value)}
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={busy || !aySchoolId}
                className="w-full rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white"
              >
                Add Academic Year
              </button>
            </form>
            <ul className="space-y-2 text-xs">
              {academicYears.map((y) => (
                <li
                  key={y.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2"
                >
                  <span className="font-semibold text-slate-900">{y.label}</span>
                  <span className="tabular-nums text-slate-500">
                    {y.starts_on} → {y.ends_on}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Classes, Sections & Batches ({batches.length})
            </h2>
            <form onSubmit={handleCreateBatch} className="space-y-2">
              <select
                required
                value={batchSchoolId}
                onChange={(e) => setBatchSchoolId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select school...</option>
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <input
                required
                placeholder="Batch Name (e.g., JEE Apex 2027)"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  required
                  value={batchGrade}
                  onChange={(e) => setBatchGrade(e.target.value)}
                  className="rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                />
                <input
                  required
                  value={batchSection}
                  onChange={(e) => setBatchSection(e.target.value)}
                  className="rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                />
                <select
                  value={batchTrack}
                  onChange={(e) => setBatchTrack(e.target.value)}
                  className="rounded border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="cbse_board">CBSE Board</option>
                  <option value="jee_main">JEE Main</option>
                  <option value="jee_advanced">JEE Adv</option>
                  <option value="neet">NEET</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={busy || !batchSchoolId}
                className="w-full rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white"
              >
                Create Batch
              </button>
            </form>
            <ul className="space-y-2 text-xs">
              {batches.map((b) => (
                <li
                  key={b.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{b.name}</p>
                    <p className="text-slate-500">
                      {b.grade_label} · Sec {b.section_name} ·{" "}
                      {b.exam_track.toUpperCase()}
                    </p>
                  </div>
                  <span className="tabular-nums text-slate-700">
                    {b.enrolled_count}/{b.capacity}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}

      {/* TAB: STAFF & STUDENT ENROLLMENTS */}
      {tab === "staff" && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Staff & Tenant Members ({members.length})
            </h2>
            <form onSubmit={handleAddMember} className="grid grid-cols-12 gap-2">
              <input
                type="email"
                required
                placeholder="staff-or-student@school.edu"
                value={memberEmail}
                onChange={(e) => setMemberEmail(e.target.value)}
                className="col-span-6 rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <select
                value={memberRole}
                onChange={(e) =>
                  setMemberRole(
                    e.target.value as
                      | "school_admin"
                      | "teacher"
                      | "mentor"
                      | "student"
                  )
                }
                className="col-span-3 rounded border border-slate-300 px-2 py-2 text-sm"
              >
                <option value="teacher">Teacher</option>
                <option value="mentor">Mentor</option>
                <option value="student">Student</option>
                <option value="school_admin">School Admin</option>
              </select>
              <button
                type="submit"
                disabled={busy || !selectedOrgId}
                className="col-span-3 rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white"
              >
                Add
              </button>
            </form>
            <ul className="space-y-2 text-xs">
              {members.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{m.user_name}</p>
                    <p className="text-slate-500">{m.user_email}</p>
                  </div>
                  <StatusBadge tone="neutral">{m.member_role}</StatusBadge>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Enroll Student in Batch
            </h2>
            <form onSubmit={handleBatchEnroll} className="space-y-2.5">
              <select
                required
                value={enrollBatchId}
                onChange={(e) => setEnrollBatchId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select batch...</option>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.grade_label})
                  </option>
                ))}
              </select>
              <input
                type="email"
                required
                placeholder="student@school.edu"
                value={enrollStudentEmail}
                onChange={(e) => setEnrollStudentEmail(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                placeholder="Roll No (optional)"
                value={enrollRollNo}
                onChange={(e) => setEnrollRollNo(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={busy || !enrollBatchId}
                className="w-full rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white"
              >
                Enroll Student
              </button>
            </form>
          </section>
        </div>
      )}

      {/* TAB: INSTITUTIONAL ASSESSMENTS */}
      {tab === "assessments" && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Publish Institution Test or Assignment
            </h2>
            <form onSubmit={handleCreateAssessment} className="space-y-2.5">
              <select
                required
                value={asmtSchoolId}
                onChange={(e) => setAsmtSchoolId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select school...</option>
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <select
                value={asmtBatchId}
                onChange={(e) => setAsmtBatchId(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">All batches in school</option>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
              <input
                required
                placeholder="Mid-Term Science Common Test"
                value={asmtTitle}
                onChange={(e) => setAsmtTitle(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={asmtKind}
                  onChange={(e) =>
                    setAsmtKind(e.target.value as "assignment" | "test")
                  }
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="test">Institution Test</option>
                  <option value="assignment">Institution Assignment</option>
                </select>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={asmtMaxMarks}
                  onChange={(e) => setAsmtMaxMarks(e.target.value)}
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={busy || !asmtSchoolId}
                className="w-full rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white"
              >
                Publish Institutional Assessment
              </button>
            </form>
          </section>

          <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Tenant Assessments ({assessments.length})
            </h2>
            {assessments.length === 0 ? (
              <EmptyState
                title="No institutional assessments yet"
                description="Schedule a school-wide or batch-wide test on the left."
              />
            ) : (
              <ul className="space-y-2 text-xs">
                {assessments.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center justify-between rounded border border-slate-200 px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {a.title}
                      </p>
                      <p className="text-slate-500">
                        {a.kind.toUpperCase()} · {a.max_marks} marks
                      </p>
                    </div>
                    <StatusBadge tone="healthy">{a.status}</StatusBadge>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      {/* TAB: TENANT CONFIG & SUBSCRIPTION ENTITLEMENTS */}
      {tab === "config" && selectedOrg && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Tenant Feature Configuration
            </h2>
            {(
              [
                ["allow_ai_tutor", "Enable Curriculum AI Tutor"],
                ["allow_homework_ai", "Enable Homework AI Evaluation"],
                ["require_mfa_for_admins", "Require TOTP MFA for School Admins"],
                ["allow_parent_portal", "Enable Parent & Guardian Portal"],
              ] as const
            ).map(([key, label]) => (
              <label
                key={key}
                className="flex items-center justify-between rounded border border-slate-200 px-3 py-2.5 text-sm text-slate-800"
              >
                <span>{label}</span>
                <input
                  type="checkbox"
                  checked={Boolean(selectedOrg.config[key])}
                  onChange={() => void handleToggleConfig(key)}
                />
              </label>
            ))}
          </section>

          <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold text-slate-900">
              Subscription Plan & Entitlements
            </h2>
            <p className="text-xs text-slate-600 tabular-nums">
              Current plan: <strong>{selectedOrg.plan_name ?? "Starter"}</strong>{" "}
              · Seats: {selectedOrg.seat_limit} · Teachers:{" "}
              {selectedOrg.max_teachers} · Branches: {selectedOrg.max_branches}
            </p>
            <div className="space-y-2">
              {plans.map((p) => {
                const isCurrent = p.code === selectedOrg.plan_code;
                return (
                  <div
                    key={p.id}
                    className={`flex items-center justify-between rounded border p-3 ${
                      isCurrent
                        ? "border-indigo-600 bg-indigo-50/40"
                        : "border-slate-200"
                    }`}
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {p.name}
                      </p>
                      <p className="text-xs text-slate-600 tabular-nums">
                        ₹{p.monthly_price_inr.toLocaleString("en-IN")}/mo ·{" "}
                        {p.max_students} students · {p.max_branches} branches
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={busy || isCurrent}
                      onClick={() => void handleChangePlan(p.code)}
                      className="rounded border border-indigo-700 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
                    >
                      {isCurrent ? "Active" : "Switch Plan"}
                    </button>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
