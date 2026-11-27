"use client";

import type {
  AttemptDetailedSolutionsResponse,
  ExamAnalyticsResponse,
  ExamFormulaOut,
  ExamQuestionsExplorerResponse,
  ExamRevisionPlanOut,
  ExamSyllabusChapterOut,
  ExamSyllabusResponse,
  ExamTrackOverviewOut,
} from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ExamAnalyticsTab } from "@/components/exams/ExamAnalyticsTab";
import { ExamTrackHeader } from "@/components/exams/ExamTrackHeader";
import { RevisionFormulasTab } from "@/components/exams/RevisionFormulasTab";
import { SyllabusPracticeTab } from "@/components/exams/SyllabusPracticeTab";
import { TimedMocksTab } from "@/components/exams/TimedMocksTab";
import {
  type PyqFilterState,
  VerifiedPyqTab,
} from "@/components/exams/VerifiedPyqTab";
import {
  createExamRevisionPlan,
  exploreExamQuestions,
  fetchAttemptDetailedSolutions,
  fetchExamAnalytics,
  fetchExamSyllabus,
  generateExamMockTest,
  launchExamPractice,
  listExamFormulas,
  listExamPrepTracks,
  listExamRevisionPlans,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type ExamWorkspaceTab =
  | "syllabus"
  | "pyq"
  | "mocks"
  | "analytics"
  | "revision";

const DEFAULT_PYQ_FILTERS: PyqFilterState = {
  verifiedPyqOnly: true,
  examYear: "",
  examSession: "",
  difficulty: "",
  questionType: "",
};

export default function ExamPrepPage() {
  const router = useRouter();
  const { token: accessToken, user, initializing } = useAuth();

  const [tracks, setTracks] = useState<ExamTrackOverviewOut[]>([]);
  const [selectedExamCode, setSelectedExamCode] = useState<string>("JEE_MAIN");
  const [selectedPatternId, setSelectedPatternId] = useState<string | null>(
    null
  );
  const [activeTab, setActiveTab] = useState<ExamWorkspaceTab>("syllabus");

  const [syllabus, setSyllabus] = useState<ExamSyllabusResponse | null>(null);
  const [pyqData, setPyqData] =
    useState<ExamQuestionsExplorerResponse | null>(null);
  const [pyqFilters, setPyqFilters] =
    useState<PyqFilterState>(DEFAULT_PYQ_FILTERS);
  const [analytics, setAnalytics] = useState<ExamAnalyticsResponse | null>(
    null
  );
  const [formulas, setFormulas] = useState<ExamFormulaOut[]>([]);
  const [revisionPlans, setRevisionPlans] = useState<ExamRevisionPlanOut[]>([]);

  const [loadingTracks, setLoadingTracks] = useState(true);
  const [loadingTrackDetail, setLoadingTrackDetail] = useState(false);
  const [loadingPyq, setLoadingPyq] = useState(false);
  const [launchingKey, setLaunchingKey] = useState<string | null>(null);
  const [generatingMock, setGeneratingMock] = useState(false);
  const [creatingPlan, setCreatingPlan] = useState(false);
  const [solutionsLoadingId, setSolutionsLoadingId] = useState<string | null>(
    null
  );
  const [activeSolutions, setActiveSolutions] =
    useState<AttemptDetailedSolutionsResponse | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedExamRef = useRef(selectedExamCode);
  selectedExamRef.current = selectedExamCode;

  const loadTracks = useCallback(async (token: string) => {
    setLoadingTracks(true);
    setError(null);
    try {
      const list = await listExamPrepTracks(token);
      setTracks(list);
      if (list.length > 0) {
        const preferred =
          list.find((t) => t.code === selectedExamRef.current) ??
          list.find((t) => t.code === "JEE_MAIN") ??
          list[0];
        setSelectedExamCode(preferred.code);
        setSelectedPatternId(
          preferred.active_pattern?.id ?? preferred.patterns[0]?.id ?? null
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load examination tracks."
      );
    } finally {
      setLoadingTracks(false);
    }
  }, []);

  const loadTrackWorkspace = useCallback(
    async (token: string, examCode: string, patternVersionLabel?: string) => {
      setLoadingTrackDetail(true);
      setError(null);
      setActiveSolutions(null);
      try {
        const [sylRes, anaRes, formRes, planRes] = await Promise.all([
          fetchExamSyllabus(token, examCode, patternVersionLabel),
          fetchExamAnalytics(token, examCode),
          listExamFormulas(token, examCode),
          listExamRevisionPlans(token, examCode),
        ]);
        setSyllabus(sylRes);
        setAnalytics(anaRes);
        setFormulas(formRes);
        setRevisionPlans(planRes);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load exam track data."
        );
      } finally {
        setLoadingTrackDetail(false);
      }
    },
    []
  );

  const loadQuestions = useCallback(
    async (token: string, examCode: string, filters: PyqFilterState) => {
      setLoadingPyq(true);
      try {
        const res = await exploreExamQuestions(token, examCode, {
          verified_pyq_only: filters.verifiedPyqOnly,
          exam_year: filters.examYear ? Number(filters.examYear) : null,
          exam_session: filters.examSession || null,
          difficulty: filters.difficulty || null,
          question_type: filters.questionType || null,
          limit: 40,
        });
        setPyqData(res);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load verified PYQs."
        );
      } finally {
        setLoadingPyq(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!accessToken) {
      setLoadingTracks(false);
      return;
    }
    void loadTracks(accessToken);
  }, [accessToken, loadTracks]);

  const activeTrack =
    tracks.find((t) => t.code === selectedExamCode) ?? tracks[0] ?? null;
  const activePattern =
    activeTrack?.patterns.find((p) => p.id === selectedPatternId) ??
    activeTrack?.active_pattern ??
    activeTrack?.patterns[0] ??
    null;

  const activeExamCode = activeTrack?.code ?? null;
  const activePatternVersion = activePattern?.version_label;

  useEffect(() => {
    if (!accessToken || !activeExamCode) return;
    void loadTrackWorkspace(accessToken, activeExamCode, activePatternVersion);
  }, [accessToken, activeExamCode, activePatternVersion, loadTrackWorkspace]);

  useEffect(() => {
    if (!accessToken || !activeExamCode) return;
    void loadQuestions(accessToken, activeExamCode, pyqFilters);
  }, [accessToken, activeExamCode, pyqFilters, loadQuestions]);

  function handleSelectTrack(examCode: string) {
    setSelectedExamCode(examCode);
    const nextTrack = tracks.find((t) => t.code === examCode);
    setSelectedPatternId(
      nextTrack?.active_pattern?.id ?? nextTrack?.patterns[0]?.id ?? null
    );
    setPyqFilters(DEFAULT_PYQ_FILTERS);
    setNotice(null);
    setError(null);
  }

  async function handleStartChapterPractice(chapter: ExamSyllabusChapterOut) {
    if (!accessToken || !activeTrack) return;
    setLaunchingKey(`chap:${chapter.chapter_id}`);
    setError(null);
    try {
      const launched = await launchExamPractice(accessToken, activeTrack.code, {
        mode: "chapter_practice",
        title: `${activeTrack.name} · ${chapter.chapter_title}`,
        exam_pattern_id: activePattern?.id ?? null,
        subject_id: chapter.subject_id,
        chapter_id: chapter.chapter_id,
        question_count: 10,
      });
      router.push(`/assessments/${launched.attempt_id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to start chapter practice."
      );
    } finally {
      setLaunchingKey(null);
    }
  }

  async function handleStartTopicPractice(
    chapter: ExamSyllabusChapterOut,
    topicId: string,
    topicTitle: string
  ) {
    if (!accessToken || !activeTrack) return;
    setLaunchingKey(`topic:${topicId}`);
    setError(null);
    try {
      const launched = await launchExamPractice(accessToken, activeTrack.code, {
        mode: "topic_practice",
        title: `${activeTrack.name} · ${topicTitle}`,
        exam_pattern_id: activePattern?.id ?? null,
        subject_id: chapter.subject_id,
        chapter_id: chapter.chapter_id,
        topic_id: topicId,
        question_count: 10,
      });
      router.push(`/assessments/${launched.attempt_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to start topic practice."
      );
    } finally {
      setLaunchingKey(null);
    }
  }

  async function handleLaunchFilteredPyqDrill() {
    if (!accessToken || !activeTrack) return;
    setLaunchingKey("pyq_drill");
    setError(null);
    try {
      const launched = await launchExamPractice(accessToken, activeTrack.code, {
        mode: pyqFilters.verifiedPyqOnly
          ? "verified_pyq_drill"
          : "chapter_practice",
        title: pyqFilters.verifiedPyqOnly
          ? `${activeTrack.name} Verified PYQ Drill`
          : `${activeTrack.name} Filtered Practice`,
        exam_pattern_id: activePattern?.id ?? null,
        verified_pyq_only: pyqFilters.verifiedPyqOnly,
        exam_year: pyqFilters.examYear ? Number(pyqFilters.examYear) : null,
        exam_session: pyqFilters.examSession || null,
        difficulty:
          (pyqFilters.difficulty as "easy" | "medium" | "hard") || null,
        question_type: pyqFilters.questionType || null,
        question_count: 15,
      });
      router.push(`/assessments/${launched.attempt_id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to launch filtered PYQ drill."
      );
    } finally {
      setLaunchingKey(null);
    }
  }

  async function handleGenerateMock(verifiedPyqOnly: boolean) {
    if (!accessToken || !activeTrack) return;
    setGeneratingMock(true);
    setError(null);
    try {
      const launched = await generateExamMockTest(
        accessToken,
        activeTrack.code,
        {
          exam_pattern_id: activePattern?.id ?? null,
          mock_scope: "full_mock",
          verified_pyq_only: verifiedPyqOnly,
        }
      );
      router.push(`/assessments/${launched.attempt_id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to assemble timed mock examination."
      );
    } finally {
      setGeneratingMock(false);
    }
  }

  async function handleOpenSolutions(attemptId: string) {
    if (!accessToken) return;
    setSolutionsLoadingId(attemptId);
    setError(null);
    try {
      const res = await fetchAttemptDetailedSolutions(accessToken, attemptId);
      setActiveSolutions(res);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load detailed post-attempt solutions."
      );
    } finally {
      setSolutionsLoadingId(null);
    }
  }

  async function handleCreateRevisionPlan(payload: {
    title?: string;
    target_exam_date: string;
    daily_minutes: number;
  }) {
    if (!accessToken || !activeTrack) return;
    setCreatingPlan(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createExamRevisionPlan(
        accessToken,
        activeTrack.code,
        {
          ...payload,
          exam_pattern_id: activePattern?.id ?? null,
        }
      );
      setRevisionPlans((prev) => [created, ...prev]);
      setNotice(`Revision plan "${created.title}" generated and saved.`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to generate exam revision plan."
      );
    } finally {
      setCreatingPlan(false);
    }
  }

  if (initializing) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <LoadingCard message="Restoring your session..." />
      </main>
    );
  }

  if (!user || !accessToken) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
        <EmptyState
          title="Sign in to access Exam Preparation Ecosystem"
          description="Sign in as a student, teacher, mentor, or reviewer to explore CBSE Board, JEE Main, JEE Advanced, and NEET syllabi, verified PYQs, timed mocks, and pacing analytics."
          action={
            <Link
              href="/login"
              className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
            >
              Sign In
            </Link>
          }
        />
      </main>
    );
  }

  const tabs: { id: ExamWorkspaceTab; label: string }[] = [
    { id: "syllabus", label: "Syllabus & Chapter Practice" },
    { id: "pyq", label: "Verified PYQs & Explorer" },
    { id: "mocks", label: "Timed Mocks & Solutions" },
    { id: "analytics", label: "Exam Analytics & Pacing" },
    { id: "revision", label: "Formulas & Revision Plans" },
  ];

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      {error && <ErrorBanner title="Exam Prep Error" message={error} />}
      {notice && (
        <div
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900"
        >
          {notice}
        </div>
      )}

      {loadingTracks ? (
        <LoadingCard message="Loading examination tracks & versioned patterns..." />
      ) : tracks.length === 0 ? (
        <EmptyState
          title="No examination tracks registered"
          description="Run Alembic migrations to seed CBSE Board, JEE Main, JEE Advanced, and NEET examination tracks."
        />
      ) : (
        <>
          <ExamTrackHeader
            tracks={tracks}
            selectedExamCode={selectedExamCode}
            selectedPatternId={selectedPatternId}
            onSelectTrack={handleSelectTrack}
            onSelectPattern={setSelectedPatternId}
          />

          {/* Workspace Sub-Navigation Tabs */}
          <div
            role="tablist"
            aria-label="Exam preparation workspace sections"
            className="flex flex-wrap gap-2 border-b border-slate-200 pb-3"
          >
            {tabs.map((tab) => {
              const selected = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  onClick={() => setActiveTab(tab.id)}
                  className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition sm:text-sm ${
                    selected
                      ? "bg-indigo-700 text-white shadow-2xs"
                      : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {loadingTrackDetail ? (
            <LoadingCard message="Loading syllabus, analytics, formulas, and revision plans..." />
          ) : (
            <div>
              {activeTab === "syllabus" && (
                <SyllabusPracticeTab
                  syllabus={syllabus}
                  launchingKey={launchingKey}
                  onStartChapterPractice={(ch) =>
                    void handleStartChapterPractice(ch)
                  }
                  onStartTopicPractice={(ch, tid, ttitle) =>
                    void handleStartTopicPractice(ch, tid, ttitle)
                  }
                />
              )}

              {activeTab === "pyq" && (
                <VerifiedPyqTab
                  data={pyqData}
                  filters={pyqFilters}
                  loading={loadingPyq}
                  launching={launchingKey === "pyq_drill"}
                  onChangeFilters={setPyqFilters}
                  onLaunchFilteredDrill={() =>
                    void handleLaunchFilteredPyqDrill()
                  }
                />
              )}

              {activeTab === "mocks" && (
                <TimedMocksTab
                  examName={activeTrack?.name ?? "Exam"}
                  selectedPattern={activePattern}
                  history={analytics?.performance_history ?? []}
                  generatingMock={generatingMock}
                  solutionsLoadingId={solutionsLoadingId}
                  activeSolutions={activeSolutions}
                  onGenerateMock={(pyqOnly) => void handleGenerateMock(pyqOnly)}
                  onOpenSolutions={(aid) => void handleOpenSolutions(aid)}
                  onCloseSolutions={() => setActiveSolutions(null)}
                />
              )}

              {activeTab === "analytics" && (
                <ExamAnalyticsTab analytics={analytics} />
              )}

              {activeTab === "revision" && (
                <RevisionFormulasTab
                  examName={activeTrack?.name ?? "Exam"}
                  formulas={formulas}
                  revisionPlans={revisionPlans}
                  creatingPlan={creatingPlan}
                  onCreateRevisionPlan={handleCreateRevisionPlan}
                />
              )}
            </div>
          )}
        </>
      )}
    </main>
  );
}
