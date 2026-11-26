"use client";

import type {
  AcademicSessionOut,
  BoardOut,
  CurriculumVersionOut,
  GradeOut,
} from "@go4guru/contracts";
import { ErrorBanner, LoadingCard } from "@go4guru/ui";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import {
  ApiClientError,
  fetchBoards,
  fetchCurriculumVersions,
  fetchGrades,
  fetchSessions,
  fetchStudentProfile,
  updateStudentProfile,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function OnboardingPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [boards, setBoards] = useState<BoardOut[]>([]);
  const [sessions, setSessions] = useState<AcademicSessionOut[]>([]);
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [versions, setVersions] = useState<CurriculumVersionOut[]>([]);

  const [boardId, setBoardId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [gradeId, setGradeId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [examTarget, setExamTarget] = useState("cbse_board");
  const [dailyMinutes, setDailyMinutes] = useState("60");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    const authToken = token;
    async function load() {
      setLoading(true);
      try {
        const [b, s, g, v, sp] = await Promise.all([
          fetchBoards(),
          fetchSessions(),
          fetchGrades(),
          fetchCurriculumVersions(authToken, false),
          fetchStudentProfile(authToken),
        ]);
        setBoards(b);
        setSessions(s);
        setGrades(g);
        setVersions(v);
        setBoardId(sp.board_id ?? b[0]?.id ?? "");
        setSessionId(sp.academic_session_id ?? s[0]?.id ?? "");
        setGradeId(sp.grade_id ?? g[0]?.id ?? "");
        setVersionId(sp.curriculum_version_id ?? v[0]?.id ?? "");
        setExamTarget(sp.primary_exam_target);
        setDailyMinutes(String(sp.daily_study_minutes_target));
      } catch (err) {
        setError(
          err instanceof ApiClientError ? err.message : "Failed to load onboarding options."
        );
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [initializing, token, router]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      await updateStudentProfile(token, {
        board_id: boardId || null,
        academic_session_id: sessionId || null,
        grade_id: gradeId || null,
        curriculum_version_id: versionId || null,
        primary_exam_target: examTarget,
        daily_study_minutes_target: Number(dailyMinutes) || 60,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Unable to save profile."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-xl px-4 py-10">
      <h1 className="text-2xl font-bold text-slate-900">Student Academic Profile</h1>
      <p className="mt-1 text-sm text-slate-600">
        Select your class, board, and target examination to tailor your learning dashboard.
      </p>

      {loading ? (
        <div className="mt-6">
          <LoadingCard message="Loading academic boards, classes, and published versions..." />
        </div>
      ) : null}

      {error ? (
        <div className="mt-6">
          <ErrorBanner title="Profile Error" message={error} />
        </div>
      ) : null}

      {!loading ? (
        <form
          onSubmit={(e) => void handleSave(e)}
          className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6"
        >
          <div>
            <label htmlFor="onb-grade" className="block text-sm font-medium text-slate-800">
              Class / Grade
            </label>
            <select
              id="onb-grade"
              value={gradeId}
              onChange={(e) => setGradeId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select class...</option>
              {grades.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="onb-board" className="block text-sm font-medium text-slate-800">
                Board
              </label>
              <select
                id="onb-board"
                value={boardId}
                onChange={(e) => setBoardId(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">None published yet</option>
                {boards.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.code} — {b.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="onb-session" className="block text-sm font-medium text-slate-800">
                Academic Session
              </label>
              <select
                id="onb-session"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">None created yet</option>
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="onb-version" className="block text-sm font-medium text-slate-800">
              Published Syllabus Version
            </label>
            <select
              id="onb-version"
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select version when published...</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.version_tag} ({v.status})
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="onb-target" className="block text-sm font-medium text-slate-800">
                Primary Goal
              </label>
              <select
                id="onb-target"
                value={examTarget}
                onChange={(e) => setExamTarget(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="cbse_board">CBSE Board Exams</option>
                <option value="jee_main">JEE Main</option>
                <option value="jee_advanced">JEE Advanced</option>
                <option value="neet">NEET UG</option>
                <option value="foundation">Foundation (6–10)</option>
              </select>
            </div>

            <div>
              <label htmlFor="onb-mins" className="block text-sm font-medium text-slate-800">
                Daily Target (minutes)
              </label>
              <input
                id="onb-mins"
                type="number"
                min={10}
                max={720}
                value={dailyMinutes}
                onChange={(e) => setDailyMinutes(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save Profile & Open Dashboard"}
          </button>
        </form>
      ) : null}
    </main>
  );
}
