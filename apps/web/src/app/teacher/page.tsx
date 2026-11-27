"use client";

import type {
  AssignmentSubmissionOut,
  ClassEnrollmentOut,
  QuestionBankOptionOut,
  TeacherAssignmentOut,
  TeacherClassAnalyticsOut,
  TeacherDashboardOut,
  TeacherSectionOut,
  TeacherStudentAnalyticsOut,
} from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard, StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  aiGradeSubmission,
  createTeacherAssignment,
  createTeacherClass,
  createTeacherSection,
  enrollTeacherClassStudent,
  fetchTeacherClassAnalytics,
  fetchTeacherClassReportCsv,
  fetchTeacherDashboard,
  fetchTeacherStudentAnalytics,
  listAssignmentSubmissions,
  listTeacherAssignments,
  listTeacherClassStudents,
  listTeacherQuestionBankOptions,
  listTeacherSections,
  overrideSubmissionGrade,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  computeGradeOverrideDelta,
  triggerCsvDownload,
} from "@/lib/ecosystem-helpers";

type TeacherTab = "classes" | "assignments" | "grading" | "analytics";

export default function TeacherHubPage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();

  const [tab, setTab] = useState<TeacherTab>("classes");
  const [dashboard, setDashboard] = useState<TeacherDashboardOut | null>(null);
  const [selectedClassId, setSelectedClassId] = useState<string>("");
  const [sections, setSections] = useState<TeacherSectionOut[]>([]);
  const [students, setStudents] = useState<ClassEnrollmentOut[]>([]);
  const [assignments, setAssignments] = useState<TeacherAssignmentOut[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string>("");
  const [submissions, setSubmissions] = useState<AssignmentSubmissionOut[]>([]);
  const [questionBank, setQuestionBank] = useState<QuestionBankOptionOut[]>([]);
  const [classAnalytics, setClassAnalytics] =
    useState<TeacherClassAnalyticsOut | null>(null);
  const [studentAnalytics, setStudentAnalytics] =
    useState<TeacherStudentAnalyticsOut | null>(null);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Forms
  const [className, setClassName] = useState("");
  const [gradeLabel, setGradeLabel] = useState("Class 10");
  const [subjectName, setSubjectName] = useState("Mathematics");

  const [sectionName, setSectionName] = useState("");
  const [sectionCode, setSectionCode] = useState("");
  const [sectionCapacity, setSectionCapacity] = useState("40");

  const [enrollEmail, setEnrollEmail] = useState("");
  const [enrollSectionId, setEnrollSectionId] = useState("");
  const [enrollRollNo, setEnrollRollNo] = useState("");

  const [asgnTitle, setAsgnTitle] = useState("");
  const [asgnType, setAsgnType] = useState<"assignment" | "quiz" | "test">(
    "assignment"
  );
  const [asgnMarks, setAsgnMarks] = useState("20");
  const [asgnInstructions, setAsgnInstructions] = useState("");
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<string[]>([]);

  // Teacher override editor state keyed by submission ID
  const [overrideScores, setOverrideScores] = useState<Record<string, string>>(
    {}
  );
  const [overrideFeedback, setOverrideFeedback] = useState<
    Record<string, string>
  >({});
  const [overrideReasons, setOverrideReasons] = useState<
    Record<string, string>
  >({});

  const loadClassDetails = useCallback(
    async (authToken: string, classId: string) => {
      const [secList, stuList, asgnList, analytics] = await Promise.all([
        listTeacherSections(authToken, classId),
        listTeacherClassStudents(authToken, classId),
        listTeacherAssignments(authToken, classId),
        fetchTeacherClassAnalytics(authToken, classId),
      ]);
      setSections(secList);
      setStudents(stuList);
      setAssignments(asgnList);
      setClassAnalytics(analytics);
      setStudentAnalytics(null);
      if (asgnList.length > 0) {
        const nextAsgnId = asgnList[0].id;
        setSelectedAssignmentId(nextAsgnId);
        const subs = await listAssignmentSubmissions(authToken, nextAsgnId);
        setSubmissions(subs);
      } else {
        setSelectedAssignmentId("");
        setSubmissions([]);
      }
    },
    []
  );

  const selectedClassIdRef = useRef(selectedClassId);
  selectedClassIdRef.current = selectedClassId;

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [dash, qb] = await Promise.all([
        fetchTeacherDashboard(token),
        listTeacherQuestionBankOptions(token, 20).catch(() => []),
      ]);
      setDashboard(dash);
      setQuestionBank(qb);
      const firstClassId = selectedClassIdRef.current || dash.classes[0]?.id || "";
      if (firstClassId) {
        selectedClassIdRef.current = firstClassId;
        setSelectedClassId(firstClassId);
        await loadClassDetails(token, firstClassId);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load Teacher Hub."
      );
    } finally {
      setLoading(false);
    }
  }, [token, loadClassDetails]);

  useEffect(() => {
    if (!initializing && !token) {
      router.replace("/login");
    }
  }, [initializing, token, router]);

  useEffect(() => {
    if (token) {
      void loadDashboard();
    }
  }, [token, loadDashboard]);

  async function handleSelectClass(classId: string) {
    setSelectedClassId(classId);
    if (!token || !classId) return;
    setBusy(true);
    setError(null);
    try {
      await loadClassDetails(token, classId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load class data."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectAssignment(assignmentId: string) {
    setSelectedAssignmentId(assignmentId);
    if (!token || !assignmentId) return;
    setBusy(true);
    setError(null);
    try {
      const subs = await listAssignmentSubmissions(token, assignmentId);
      setSubmissions(subs);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load submissions."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateClass(e: FormEvent) {
    e.preventDefault();
    if (!token || !className.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createTeacherClass(token, {
        name: className.trim(),
        grade_label: gradeLabel.trim(),
        subject_name: subjectName.trim(),
      });
      setClassName("");
      setSelectedClassId(created.id);
      setNotice(`Created class "${created.name}".`);
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create class.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateSection(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedClassId || !sectionName.trim() || !sectionCode.trim())
      return;
    setBusy(true);
    setError(null);
    try {
      await createTeacherSection(token, selectedClassId, {
        name: sectionName.trim(),
        code: sectionCode.trim(),
        capacity: Number(sectionCapacity) || 40,
      });
      setSectionName("");
      setSectionCode("");
      setNotice("Section added.");
      await loadClassDetails(token, selectedClassId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add section.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEnrollStudent(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedClassId || !enrollEmail.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await enrollTeacherClassStudent(token, selectedClassId, {
        student_email: enrollEmail.trim(),
        section_id: enrollSectionId || null,
        roll_no: enrollRollNo.trim() || null,
      });
      setEnrollEmail("");
      setEnrollRollNo("");
      setNotice("Student enrolled in class.");
      await loadClassDetails(token, selectedClassId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not enroll student."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateAssignment(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedClassId || !asgnTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createTeacherAssignment(token, {
        class_id: selectedClassId,
        title: asgnTitle.trim(),
        assignment_type: asgnType,
        instructions: asgnInstructions.trim(),
        question_ids: selectedQuestionIds,
        max_marks: Number(asgnMarks) || 20,
      });
      setAsgnTitle("");
      setAsgnInstructions("");
      setSelectedQuestionIds([]);
      setNotice("Published to class.");
      await loadClassDetails(token, selectedClassId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create assignment."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleAiGrade(submissionId: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await aiGradeSubmission(token, submissionId);
      setSubmissions((prev) =>
        prev.map((s) => (s.id === submissionId ? updated : s))
      );
      if (updated.ai_suggested_score !== null) {
        setOverrideScores((prev) => ({
          ...prev,
          [submissionId]: String(updated.ai_suggested_score),
        }));
      }
      setNotice("AI grading draft generated. Review and apply Teacher Override.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI grading failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleTeacherOverride(sub: AssignmentSubmissionOut) {
    if (!token) return;
    const rawScore = overrideScores[sub.id];
    const parsedScore =
      rawScore !== undefined && rawScore !== ""
        ? Number(rawScore)
        : (sub.teacher_score ?? sub.ai_suggested_score ?? 0);
    setBusy(true);
    setError(null);
    try {
      const updated = await overrideSubmissionGrade(token, sub.id, {
        teacher_score: parsedScore,
        teacher_feedback: overrideFeedback[sub.id] ?? sub.teacher_feedback ?? "",
        teacher_override_reason:
          overrideReasons[sub.id] ?? sub.teacher_override_reason ?? undefined,
        status: "returned",
      });
      setSubmissions((prev) => prev.map((s) => (s.id === sub.id ? updated : s)));
      setNotice(`Teacher grade saved (${updated.teacher_score}/${updated.max_marks}).`);
      if (selectedClassId) {
        const analytics = await fetchTeacherClassAnalytics(token, selectedClassId);
        setClassAnalytics(analytics);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save teacher override."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleInspectStudent(studentId: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const stats = await fetchTeacherStudentAnalytics(token, studentId);
      setStudentAnalytics(stats);
      setTab("analytics");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Cannot view student analytics."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleExportCsv() {
    if (!token || !selectedClassId) return;
    setBusy(true);
    setError(null);
    try {
      const csv = await fetchTeacherClassReportCsv(token, selectedClassId);
      triggerCsvDownload(`class_report_${selectedClassId.slice(0, 8)}.csv`, csv);
      setNotice("Formula-safe CSV report downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  }

  function toggleQuestionId(qid: string) {
    setSelectedQuestionIds((prev) =>
      prev.includes(qid) ? prev.filter((id) => id !== qid) : [...prev, qid]
    );
  }

  if (initializing || loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <LoadingCard message="Loading Teacher Hub..." />
      </main>
    );
  }

  const canAccess = user?.roles.some((r) =>
    ["teacher", "school_admin", "platform_admin"].includes(r)
  );
  if (!canAccess) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <ErrorBanner
          title="Teacher access required"
          message="Your account does not hold the teacher, school_admin, or platform_admin role."
        />
        <div className="mt-4">
          <Link href="/dashboard" className="text-sm font-medium text-indigo-700 underline">
            Return to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Educator Workspace
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Teacher Hub
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage classes, sections, Question Bank assessments, AI-assisted grading with full Teacher Override, and analytics.
          </p>
        </div>
        {selectedClassId && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleExportCsv()}
            className="shrink-0 whitespace-nowrap rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
          >
            Export Class CSV
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

      {/* KPI Strip */}
      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Active Classes", value: dashboard?.total_classes ?? 0 },
          { label: "Enrolled Students", value: dashboard?.total_students ?? 0 },
          {
            label: "Assignments & Tests",
            value: dashboard?.total_assignments ?? 0,
          },
          {
            label: "Pending Reviews",
            value: dashboard?.pending_reviews_count ?? 0,
          },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-lg border border-slate-200 bg-white p-4"
          >
            <p className="text-xs font-medium text-slate-500">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
              {kpi.value}
            </p>
          </div>
        ))}
      </section>

      {/* Class Selector + Workspace Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <label
            htmlFor="teacher-class-select"
            className="text-xs font-semibold uppercase tracking-wide text-slate-600"
          >
            Active Class
          </label>
          <select
            id="teacher-class-select"
            value={selectedClassId}
            onChange={(e) => void handleSelectClass(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
          >
            <option value="">Select class...</option>
            {(dashboard?.classes ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.grade_label} · {c.subject_name})
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Teacher sections">
          {(
            [
              ["classes", "Classes & Roster"],
              ["assignments", "Assignments & Bank"],
              ["grading", "Submissions & Override"],
              ["analytics", "Analytics & Weak Concepts"],
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

      {/* TAB 1: CLASSES, SECTIONS & ROSTER */}
      {tab === "classes" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 lg:col-span-5">
            <h2 className="text-base font-semibold text-slate-900">
              Create New Class
            </h2>
            <form onSubmit={handleCreateClass} className="space-y-3">
              <div>
                <label
                  htmlFor="new-class-name"
                  className="block text-xs font-medium text-slate-700"
                >
                  Class Title
                </label>
                <input
                  id="new-class-name"
                  required
                  value={className}
                  onChange={(e) => setClassName(e.target.value)}
                  placeholder="e.g., Class 10 CBSE Mathematics"
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="new-grade-label"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Grade
                  </label>
                  <input
                    id="new-grade-label"
                    required
                    value={gradeLabel}
                    onChange={(e) => setGradeLabel(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label
                    htmlFor="new-subject-name"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Subject
                  </label>
                  <input
                    id="new-subject-name"
                    required
                    value={subjectName}
                    onChange={(e) => setSubjectName(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800 disabled:opacity-50"
              >
                Create Class
              </button>
            </form>

            {selectedClassId && (
              <div className="border-t border-slate-200 pt-4">
                <h3 className="text-sm font-semibold text-slate-900">
                  Add Section to Active Class
                </h3>
                <form
                  onSubmit={handleCreateSection}
                  className="mt-2 grid grid-cols-3 gap-2"
                >
                  <input
                    required
                    placeholder="Section A"
                    value={sectionName}
                    onChange={(e) => setSectionName(e.target.value)}
                    className="rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                  <input
                    required
                    placeholder="Code (A)"
                    value={sectionCode}
                    onChange={(e) => setSectionCode(e.target.value)}
                    className="rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={sectionCapacity}
                    onChange={(e) => setSectionCapacity(e.target.value)}
                    className="rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={busy}
                    className="col-span-3 rounded-md border border-indigo-700 px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
                  >
                    Add Section
                  </button>
                </form>
                {sections.length > 0 && (
                  <ul className="mt-3 space-y-1.5 text-xs text-slate-700">
                    {sections.map((s) => (
                      <li
                        key={s.id}
                        className="flex items-center justify-between rounded bg-slate-50 px-3 py-1.5"
                      >
                        <span className="font-medium">
                          {s.name} ({s.code})
                        </span>
                        <span className="tabular-nums text-slate-500">
                          {s.enrolled_count}/{s.capacity} seats
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 lg:col-span-7">
            <h2 className="text-base font-semibold text-slate-900">
              Student Roster & Enrollment
            </h2>
            {!selectedClassId ? (
              <EmptyState
                title="No class selected"
                description="Create or choose a class to manage sections and enroll students."
              />
            ) : (
              <>
                <form
                  onSubmit={handleEnrollStudent}
                  className="grid gap-2 sm:grid-cols-12"
                >
                  <input
                    type="email"
                    required
                    placeholder="student@school.edu"
                    value={enrollEmail}
                    onChange={(e) => setEnrollEmail(e.target.value)}
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm sm:col-span-5"
                  />
                  <select
                    value={enrollSectionId}
                    onChange={(e) => setEnrollSectionId(e.target.value)}
                    className="rounded-md border border-slate-300 px-2.5 py-2 text-sm sm:col-span-3"
                  >
                    <option value="">Any Section</option>
                    {sections.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder="Roll #"
                    value={enrollRollNo}
                    onChange={(e) => setEnrollRollNo(e.target.value)}
                    className="rounded-md border border-slate-300 px-2.5 py-2 text-sm sm:col-span-2"
                  />
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-md bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800 sm:col-span-2"
                  >
                    Enroll
                  </button>
                </form>

                {students.length === 0 ? (
                  <EmptyState
                    title="No students enrolled yet"
                    description="Add students by email to begin tracking assignments and mastery."
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                        <tr>
                          <th className="py-2 pr-3">Student</th>
                          <th className="py-2 pr-3">Section</th>
                          <th className="py-2 pr-3">Roll</th>
                          <th className="py-2 text-right">Analytics</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {students.map((st) => (
                          <tr key={st.id}>
                            <td className="py-2.5 pr-3">
                              <p className="font-medium text-slate-900">
                                {st.student_name}
                              </p>
                              <p className="text-xs text-slate-500">
                                {st.student_email}
                              </p>
                            </td>
                            <td className="py-2.5 pr-3 text-slate-700">
                              {st.section_name ?? "General"}
                            </td>
                            <td className="py-2.5 pr-3 tabular-nums text-slate-700">
                              {st.roll_no ?? "—"}
                            </td>
                            <td className="py-2.5 text-right">
                              <button
                                type="button"
                                onClick={() =>
                                  void handleInspectStudent(st.student_id)
                                }
                                className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50"
                              >
                                View Progress
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}

      {/* TAB 2: ASSIGNMENTS, QUIZZES, TESTS & QUESTION BANK */}
      {tab === "assignments" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 lg:col-span-6">
            <h2 className="text-base font-semibold text-slate-900">
              Create Assignment, Quiz, or Test
            </h2>
            {!selectedClassId ? (
              <EmptyState
                title="Select a class first"
                description="Choose an active class above to publish assessments."
              />
            ) : (
              <form onSubmit={handleCreateAssignment} className="space-y-3">
                <div>
                  <label
                    htmlFor="asgn-title"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Title
                  </label>
                  <input
                    id="asgn-title"
                    required
                    value={asgnTitle}
                    onChange={(e) => setAsgnTitle(e.target.value)}
                    placeholder="Quadratic Equations Unit Test"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="asgn-type"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Assessment Type
                    </label>
                    <select
                      id="asgn-type"
                      value={asgnType}
                      onChange={(e) =>
                        setAsgnType(
                          e.target.value as "assignment" | "quiz" | "test"
                        )
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    >
                      <option value="assignment">Assignment</option>
                      <option value="quiz">Quiz</option>
                      <option value="test">Test</option>
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="asgn-marks"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Max Marks
                    </label>
                    <input
                      id="asgn-marks"
                      type="number"
                      min={1}
                      max={500}
                      value={asgnMarks}
                      onChange={(e) => setAsgnMarks(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="asgn-instructions"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Instructions & Rubric Notes
                  </label>
                  <textarea
                    id="asgn-instructions"
                    rows={3}
                    value={asgnInstructions}
                    onChange={(e) => setAsgnInstructions(e.target.value)}
                    placeholder="Show all algebraic steps clearly..."
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-700">
                    Select Published Questions from Question Bank (
                    {selectedQuestionIds.length} selected)
                  </p>
                  {questionBank.length === 0 ? (
                    <p className="mt-1 text-xs text-slate-500">
                      No published questions available yet. Assignments can still
                      be created with written instructions.
                    </p>
                  ) : (
                    <div className="mt-2 max-h-48 space-y-1.5 overflow-y-auto rounded-md border border-slate-200 p-2">
                      {questionBank.map((q) => (
                        <label
                          key={q.question_id}
                          className="flex cursor-pointer items-start gap-2 rounded p-1.5 text-xs hover:bg-slate-50"
                        >
                          <input
                            type="checkbox"
                            checked={selectedQuestionIds.includes(q.question_id)}
                            onChange={() => toggleQuestionId(q.question_id)}
                            className="mt-0.5"
                          />
                          <span className="flex-1 text-slate-800">
                            <span className="font-semibold uppercase text-indigo-700">
                              [{q.question_type} · {q.difficulty}]
                            </span>{" "}
                            {q.stem_preview}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
                >
                  Publish to Class
                </button>
              </form>
            )}
          </section>

          <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 lg:col-span-6">
            <h2 className="text-base font-semibold text-slate-900">
              Class Assignments & Tests ({assignments.length})
            </h2>
            {assignments.length === 0 ? (
              <EmptyState
                title="No assignments yet"
                description="Publish your first assignment, quiz, or test on the left."
              />
            ) : (
              <div className="space-y-3">
                {assignments.map((a) => (
                  <div
                    key={a.id}
                    className="rounded-md border border-slate-200 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">{a.title}</p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {a.assignment_type.toUpperCase()} · {a.max_marks}{" "}
                          marks · {a.question_ids.length} bank questions
                        </p>
                      </div>
                      <StatusBadge tone="neutral">{a.status}</StatusBadge>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
                      <span className="tabular-nums">
                        {a.submissions_count} submitted · {a.graded_count} graded
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          void handleSelectAssignment(a.id);
                          setTab("grading");
                        }}
                        className="font-medium text-indigo-700 hover:underline"
                      >
                        Review Submissions
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* TAB 3: SUBMISSIONS, AI-ASSISTED GRADING & TEACHER OVERRIDE */}
      {tab === "grading" && (
        <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Submission Review & Teacher Override
              </h2>
              <p className="text-xs text-slate-600">
                AI grading provides an initial draft only. Final marks and feedback are always controlled by Teacher Override.
              </p>
            </div>
            <select
              aria-label="Select assignment to grade"
              value={selectedAssignmentId}
              onChange={(e) => void handleSelectAssignment(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm"
            >
              <option value="">Choose assignment...</option>
              {assignments.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title} ({a.max_marks} marks)
                </option>
              ))}
            </select>
          </div>

          {submissions.length === 0 ? (
            <EmptyState
              title="No student submissions yet"
              description="Once enrolled students submit responses for this assignment, review and grade them here."
            />
          ) : (
            <div className="space-y-4">
              {submissions.map((sub) => {
                const delta = computeGradeOverrideDelta({
                  aiSuggestedScore: sub.ai_suggested_score,
                  teacherScore: sub.teacher_score,
                  maxMarks: sub.max_marks,
                });
                return (
                  <article
                    key={sub.id}
                    className="space-y-3 rounded-lg border border-slate-200 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">
                          {sub.student_name}{" "}
                          <span className="text-xs font-normal text-slate-500">
                            ({sub.student_email})
                          </span>
                        </p>
                        <p className="mt-1 whitespace-pre-wrap rounded bg-slate-50 p-3 text-sm text-slate-800">
                          {sub.response_text}
                        </p>
                      </div>
                      <StatusBadge
                        tone={
                          sub.status === "returned" ||
                          sub.status === "teacher_reviewed"
                            ? "healthy"
                            : "neutral"
                        }
                      >
                        {sub.status.replace("_", " ")}
                      </StatusBadge>
                    </div>

                    <div className="grid gap-4 rounded-md bg-slate-50 p-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold uppercase text-slate-600">
                            AI-Assisted Draft
                          </span>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void handleAiGrade(sub.id)}
                            className="rounded border border-indigo-700 bg-white px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                          >
                            Generate AI Draft
                          </button>
                        </div>
                        <p className="text-sm font-medium tabular-nums text-slate-900">
                          Suggested:{" "}
                          {sub.ai_suggested_score !== null
                            ? `${sub.ai_suggested_score} / ${sub.max_marks}`
                            : "Not generated yet"}
                        </p>
                        {sub.ai_feedback_summary && (
                          <p className="text-xs text-slate-600">
                            {sub.ai_feedback_summary}
                          </p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold uppercase text-slate-700">
                            Teacher Final Score & Override
                          </span>
                          <span className="text-xs font-medium tabular-nums text-slate-600">
                            Effective: {delta.effectiveScore}/{sub.max_marks} (
                            {delta.percentage}%)
                            {delta.deltaFromAi !== null
                              ? ` · Δ ${delta.deltaFromAi >= 0 ? "+" : ""}${delta.deltaFromAi}`
                              : ""}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="number"
                            step="0.5"
                            min={0}
                            max={sub.max_marks}
                            aria-label={`Teacher score for ${sub.student_name}`}
                            placeholder="Final score"
                            value={
                              overrideScores[sub.id] ??
                              (sub.teacher_score !== null
                                ? String(sub.teacher_score)
                                : sub.ai_suggested_score !== null
                                  ? String(sub.ai_suggested_score)
                                  : "")
                            }
                            onChange={(e) =>
                              setOverrideScores((prev) => ({
                                ...prev,
                                [sub.id]: e.target.value,
                              }))
                            }
                            className="rounded border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                          />
                          <input
                            placeholder="Override reason (optional)"
                            value={
                              overrideReasons[sub.id] ??
                              sub.teacher_override_reason ??
                              ""
                            }
                            onChange={(e) =>
                              setOverrideReasons((prev) => ({
                                ...prev,
                                [sub.id]: e.target.value,
                              }))
                            }
                            className="rounded border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                          />
                        </div>
                        <textarea
                          rows={2}
                          placeholder="Teacher feedback for student..."
                          value={
                            overrideFeedback[sub.id] ??
                            sub.teacher_feedback ??
                            ""
                          }
                          onChange={(e) =>
                            setOverrideFeedback((prev) => ({
                              ...prev,
                              [sub.id]: e.target.value,
                            }))
                          }
                          className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                        />
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void handleTeacherOverride(sub)}
                          className="rounded-md bg-indigo-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-800"
                        >
                          Save Teacher Override & Return
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* TAB 4: CLASS & STUDENT ANALYTICS + WEAK CONCEPTS */}
      {tab === "analytics" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 lg:col-span-7">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">
                Class Analytics & Weak Concepts
              </h2>
              {selectedClassId && (
                <button
                  type="button"
                  onClick={() => void handleExportCsv()}
                  className="text-xs font-medium text-indigo-700 hover:underline"
                >
                  Download CSV
                </button>
              )}
            </div>
            {!classAnalytics ? (
              <EmptyState
                title="No analytics loaded"
                description="Select a class to inspect aggregate mastery and weak concepts."
              />
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Avg Score</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">
                      {classAnalytics.average_score_pct}%
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Avg Mastery</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">
                      {classAnalytics.average_mastery_pct}%
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Submissions</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">
                      {classAnalytics.total_submissions}
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Graded</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">
                      {classAnalytics.graded_submissions}
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Weak Concepts Below 60% Mastery
                  </h3>
                  {classAnalytics.weak_concepts.length === 0 ? (
                    <p className="mt-2 text-xs text-slate-500">
                      No weak concepts flagged yet across enrolled learners.
                    </p>
                  ) : (
                    <ul className="mt-2 space-y-2">
                      {classAnalytics.weak_concepts.map((wc) => (
                        <li
                          key={wc.concept_id}
                          className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-xs"
                        >
                          <span className="font-mono text-slate-700">
                            Concept {wc.concept_id.slice(0, 8)}
                          </span>
                          <span className="tabular-nums text-slate-900">
                            {wc.average_mastery_pct}% avg ·{" "}
                            {wc.affected_students_count} student(s)
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 lg:col-span-5">
            <h2 className="text-base font-semibold text-slate-900">
              Individual Student Analytics
            </h2>
            {!studentAnalytics ? (
              <EmptyState
                title="Choose a student"
                description="Click 'View Progress' beside any enrolled student in Classes & Roster."
              />
            ) : (
              <div className="space-y-3 text-sm">
                <div>
                  <p className="font-semibold text-slate-900">
                    {studentAnalytics.student_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {studentAnalytics.student_email}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Practice Accuracy</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {studentAnalytics.practice_accuracy_pct}%
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Mastery Avg</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {studentAnalytics.mastery_average_pct}%
                    </p>
                  </div>
                </div>
                <p className="text-xs text-slate-600 tabular-nums">
                  {studentAnalytics.practice_total_attempts} practice attempts ·{" "}
                  {studentAnalytics.submissions_total} submissions (
                  {studentAnalytics.submissions_average_pct}% avg)
                </p>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
