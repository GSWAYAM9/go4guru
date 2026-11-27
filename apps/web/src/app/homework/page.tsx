"use client";

import type {
  HomeworkSubmissionDetailOut,
  HomeworkSubmissionSummaryOut,
  HomeworkSubjectSelection,
} from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard, StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { HomeworkEvaluationPanel } from "@/components/homework/homework-evaluation-panel";
import { HomeworkUploaderPanel } from "@/components/homework/homework-uploader-panel";
import {
  ApiClientError,
  correctHomeworkOcr,
  getHomeworkSubmission,
  listHomeworkSubmissions,
  revealHomeworkSolution,
  submitHomeworkRetry,
  unlockHomeworkHint,
  uploadHomeworkSubmission,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatOverallStatus, SUBJECT_LABELS } from "@/lib/homework-helpers";

export default function HomeworkPage() {
  const router = useRouter();
  const { user, token: accessToken, initializing: authLoading } = useAuth();

  const [history, setHistory] = useState<HomeworkSubmissionSummaryOut[]>([]);
  const [activeSubmission, setActiveSubmission] =
    useState<HomeworkSubmissionDetailOut | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submittingUpload, setSubmittingUpload] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  const isParentOnly =
    user !== null && user.roles.length === 1 && user.roles[0] === "parent";

  const selectSubmission = useCallback(
    async (submissionId: string, token: string) => {
      setLoadingDetail(true);
      setErrorMsg(null);
      try {
        const detail = await getHomeworkSubmission(token, submissionId);
        setActiveSubmission(detail);
      } catch (err) {
        setErrorMsg(
          err instanceof ApiClientError
            ? err.message
            : "Could not load homework submission details."
        );
      } finally {
        setLoadingDetail(false);
      }
    },
    []
  );

  const loadHistory = useCallback(
    async (token: string, autoSelectId?: string | null) => {
      setLoadingList(true);
      setErrorMsg(null);
      try {
        const items = await listHomeworkSubmissions(token);
        const safeItems = Array.isArray(items) ? items : [];
        setHistory(safeItems);
        const targetId = autoSelectId ?? safeItems[0]?.id ?? null;
        if (targetId) {
          await selectSubmission(targetId, token);
        } else {
          setActiveSubmission(null);
        }
      } catch (err) {
        setErrorMsg(
          err instanceof ApiClientError
            ? err.message
            : "Could not load homework submission history."
        );
      } finally {
        setLoadingList(false);
      }
    },
    [selectSubmission]
  );

  const userId = user?.id ?? null;

  useEffect(() => {
    if (authLoading) return;
    if (!userId || !accessToken) {
      router.replace("/login");
      return;
    }
    if (isParentOnly) {
      setLoadingList(false);
      return;
    }
    const queryId =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("submission")
        : null;
    void loadHistory(accessToken, queryId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, userId, accessToken, isParentOnly, loadHistory]);

  async function refreshHistoryOnly(token: string) {
    try {
      const items = await listHomeworkSubmissions(token);
      if (Array.isArray(items)) {
        setHistory(items);
      }
    } catch {
      // Non-blocking refresh
    }
  }

  async function handleUploadSubmit(payload: {
    files: File[];
    title: string;
    selected_subject: HomeworkSubjectSelection;
    manual_transcript: string;
  }): Promise<boolean> {
    if (!accessToken) return false;
    setSubmittingUpload(true);
    setErrorMsg(null);
    setStatusNotice(null);
    try {
      const created = await uploadHomeworkSubmission(accessToken, {
        files: payload.files,
        title: payload.title,
        selected_subject: payload.selected_subject,
        manual_transcript: payload.manual_transcript || undefined,
      });
      setActiveSubmission(created);
      setStatusNotice(
        created.needs_ocr_review
          ? "Upload stored securely. Confirm the OCR transcription below to run full step evaluation."
          : "Homework evaluated. Review your step breakdown and Hint Level 1 below."
      );
      await refreshHistoryOnly(accessToken);
      return true;
    } catch (err) {
      setErrorMsg(
        err instanceof ApiClientError
          ? err.message
          : "Homework upload or evaluation failed. Please retry."
      );
      return false;
    } finally {
      setSubmittingUpload(false);
    }
  }

  async function handleSaveOcr(payload: {
    pages: { page_no: number; corrected_text: string }[];
    subject_override: HomeworkSubjectSelection;
    re_evaluate: boolean;
  }) {
    if (!accessToken || !activeSubmission) return;
    setBusyAction("ocr");
    setErrorMsg(null);
    setStatusNotice(null);
    try {
      const updated = await correctHomeworkOcr(
        accessToken,
        activeSubmission.id,
        payload
      );
      setActiveSubmission(updated);
      setStatusNotice("OCR transcription saved and homework re-evaluated.");
      await refreshHistoryOnly(accessToken);
    } catch (err) {
      setErrorMsg(
        err instanceof ApiClientError
          ? err.message
          : "Could not save OCR correction."
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSubmitRetry(payload: {
    revised_work_text: string;
    student_reflection: string;
  }): Promise<boolean> {
    if (!accessToken || !activeSubmission) return false;
    setBusyAction("retry");
    setErrorMsg(null);
    setStatusNotice(null);
    try {
      const updated = await submitHomeworkRetry(
        accessToken,
        activeSubmission.id,
        {
          revised_work_text: payload.revised_work_text,
          student_reflection: payload.student_reflection || undefined,
        }
      );
      setActiveSubmission(updated);
      setStatusNotice(
        updated.latest_evaluation?.overall_status === "correct"
          ? "Revised attempt verified correct!"
          : "Revised attempt evaluated. Check updated step feedback and hints."
      );
      await refreshHistoryOnly(accessToken);
      return true;
    } catch (err) {
      setErrorMsg(
        err instanceof ApiClientError
          ? err.message
          : "Could not evaluate revised attempt."
      );
      return false;
    } finally {
      setBusyAction(null);
    }
  }

  async function handleUnlockHint(nextLevel: 1 | 2 | 3) {
    if (!accessToken || !activeSubmission) return;
    setBusyAction("hint");
    setErrorMsg(null);
    try {
      const updatedEval = await unlockHomeworkHint(
        accessToken,
        activeSubmission.id,
        nextLevel
      );
      setActiveSubmission((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          latest_evaluation: updatedEval,
          evaluation_history: prev.evaluation_history.map((e) =>
            e.id === updatedEval.id ? updatedEval : e
          ),
        };
      });
    } catch (err) {
      setErrorMsg(
        err instanceof ApiClientError
          ? err.message
          : "Could not unlock next hint."
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRevealSolution() {
    if (!accessToken || !activeSubmission) return;
    setBusyAction("reveal");
    setErrorMsg(null);
    try {
      const updatedEval = await revealHomeworkSolution(
        accessToken,
        activeSubmission.id
      );
      setActiveSubmission((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          latest_evaluation: updatedEval,
          evaluation_history: prev.evaluation_history.map((e) =>
            e.id === updatedEval.id ? updatedEval : e
          ),
        };
      });
    } catch (err) {
      setErrorMsg(
        err instanceof ApiClientError
          ? err.message
          : "Could not reveal complete solution."
      );
    } finally {
      setBusyAction(null);
    }
  }

  if (authLoading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <LoadingCard message="Loading Homework AI workspace..." />
      </main>
    );
  }

  if (isParentOnly) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <EmptyState
          title="Student Homework Coaching Is Private"
          description="Parent accounts receive privacy-preserving learning summaries on the dashboard and cannot access raw student Homework AI coaching sessions."
          action={
            <Link
              href="/dashboard"
              className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
            >
              Return to Dashboard
            </Link>
          }
        />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Homework AI Evaluator
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Upload photos or PDFs of your work for subject-aware step checking,
            error classification, graduated hints, and guided retries.
          </p>
        </div>
        <div className="text-xs text-slate-500">
          Mathematics · Physics · Chemistry · English · Social Science
        </div>
      </header>

      {errorMsg && (
        <div className="mb-4">
          <ErrorBanner title="Homework AI Error" message={errorMsg} />
        </div>
      )}

      {statusNotice && (
        <div
          role="status"
          aria-live="polite"
          className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
        >
          {statusNotice}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left column: Uploader + Submission History */}
        <div className="space-y-6 lg:col-span-4">
          <HomeworkUploaderPanel
            submitting={submittingUpload}
            onSubmit={handleUploadSubmit}
          />

          <section
            aria-labelledby="homework-history-heading"
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
          >
            <div className="flex items-center justify-between">
              <h2
                id="homework-history-heading"
                className="text-base font-semibold text-slate-900"
              >
                Submission History
              </h2>
              <span className="text-xs text-slate-500 tabular-nums">
                {history.length} total
              </span>
            </div>

            {loadingList ? (
              <div className="mt-3">
                <LoadingCard message="Loading submission history..." />
              </div>
            ) : history.length === 0 ? (
              <p className="mt-3 text-xs text-slate-600">
                No homework submissions yet. Upload your first page above to get
                step-by-step feedback.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-slate-200">
                {history.map((item) => {
                  const isSelected = activeSubmission?.id === item.id;
                  const meta = item.latest_overall_status
                    ? formatOverallStatus(item.latest_overall_status)
                    : { label: item.status.replace("_", " "), tone: "neutral" as const };
                  return (
                    <li key={item.id} className="py-2 first:pt-0 last:pb-0">
                      <button
                        type="button"
                        onClick={() => {
                          if (accessToken) {
                            void selectSubmission(item.id, accessToken);
                          }
                        }}
                        className={`w-full rounded-lg p-2.5 text-left transition ${
                          isSelected
                            ? "bg-indigo-50 ring-1 ring-indigo-200"
                            : "hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-900">
                            {item.title}
                          </p>
                          <span className="shrink-0 whitespace-nowrap">
                            <StatusBadge tone={meta.tone}>
                              {meta.label}
                            </StatusBadge>
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-600 tabular-nums">
                          {item.detected_subject
                            ? SUBJECT_LABELS[item.detected_subject]
                            : "Pending"}
                          {" · "}
                          {item.page_count}p
                          {item.retry_count > 0
                            ? ` · ${item.retry_count} retry`
                            : ""}
                          {item.error_count > 0
                            ? ` · ${item.error_count} issue${item.error_count === 1 ? "" : "s"}`
                            : ""}
                        </p>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>

        {/* Right column: Active Evaluation Workbench */}
        <div className="lg:col-span-8">
          {loadingDetail ? (
            <LoadingCard message="Loading evaluation details..." />
          ) : activeSubmission ? (
            <HomeworkEvaluationPanel
              submission={activeSubmission}
              busyAction={busyAction}
              onSaveOcr={handleSaveOcr}
              onSubmitRetry={handleSubmitRetry}
              onUnlockHint={handleUnlockHint}
              onRevealSolution={handleRevealSolution}
            />
          ) : (
            <EmptyState
              title="Ready to Check Your Homework"
              description="Upload a photo or PDF of your Mathematics, Physics, Chemistry, English, or Social Science work to get step-by-step verification, error diagnostics, and graduated hints without spoiling the answer."
            />
          )}
        </div>
      </div>
    </main>
  );
}
