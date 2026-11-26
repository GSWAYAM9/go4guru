"use client";

import type {
  ContentLicenseResponse,
  ContentSourceResponse,
  ImportBatchOut,
  ImportPreviewResponse,
  QuestionOut,
} from "@go4guru/contracts";
import {
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  ApiClientError,
  commitImportBatch,
  createCurriculumEntity,
  createQuestionApi,
  fetchContentLicenses,
  fetchContentSources,
  fetchGrades,
  fetchImportPreview,
  reviewQuestionApi,
  rollbackImportBatch,
  saveImportMapping,
  searchQuestionsApi,
  uploadImportWorkbook,
  validateImportBatch,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function AdminStudioPage() {
  const router = useRouter();
  const { token, user, mfaRequired, initializing } = useAuth();

  const [tab, setTab] = useState<"curriculum" | "questions" | "imports">("imports");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const [sources, setSources] = useState<ContentSourceResponse[]>([]);
  const [licenses, setLicenses] = useState<ContentLicenseResponse[]>([]);
  const [questions, setQuestions] = useState<QuestionOut[]>([]);

  // Quick curriculum setup fields
  const [boardCode, setBoardCode] = useState("CBSE");
  const [boardName, setBoardName] = useState("Central Board of Secondary Education");
  const [createdIds, setCreatedIds] = useState<{
    boardId?: string;
    sessionId?: string;
    versionId?: string;
    gradeId?: string;
    subjectId?: string;
    bookId?: string;
    chapterId?: string;
    sourceId?: string;
    licenseId?: string;
  }>({});

  // Excel import staging state
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportBatchOut | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [stemHeader, setStemHeader] = useState("");
  const [answerHeader, setAnswerHeader] = useState("");
  const [optAHeader, setOptAHeader] = useState("");
  const [optBHeader, setOptBHeader] = useState("");
  const [optCHeader, setOptCHeader] = useState("");
  const [optDHeader, setOptDHeader] = useState("");

  // Question quick-author state
  const [qStem, setQStem] = useState("");
  const [qNumAns, setQNumAns] = useState("42");

  const refreshData = useCallback(async (authToken: string) => {
    setLoading(true);
    setError(null);
    try {
      const [s, l, g, qRes] = await Promise.all([
        fetchContentSources(authToken),
        fetchContentLicenses(authToken),
        fetchGrades(),
        searchQuestionsApi(authToken, { limit: 25 }),
      ]);
      setSources(s);
      setLicenses(l);
      setQuestions(qRes.items);
      setCreatedIds((prev) => ({
        ...prev,
        gradeId: prev.gradeId ?? g.find((x) => x.number === 10)?.id ?? g[0]?.id,
        sourceId: prev.sourceId ?? s[0]?.id,
        licenseId: prev.licenseId ?? l.find((x) => x.legal_review_status === "approved")?.id ?? l[0]?.id,
      }));
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? `${err.code}: ${err.message}`
          : "Admin API error."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    if (mfaRequired) {
      router.push("/login");
      return;
    }
    void refreshData(token);
  }, [initializing, token, mfaRequired, router, refreshData]);

  async function handleBootstrapCurriculum(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setStatusMsg(null);
    try {
      const b = (await createCurriculumEntity(token, "/boards", {
        code: boardCode,
        name: boardName,
      })) as { id: string };
      const s = (await createCurriculumEntity(token, "/sessions", {
        code: "2026-27",
        starts_on: "2026-04-01",
        ends_on: "2027-03-31",
      })) as { id: string };
      const v = (await createCurriculumEntity(token, "/versions", {
        board_id: b.id,
        academic_session_id: s.id,
        version_tag: "2026-27-v1",
      })) as { id: string };
      const subj = (await createCurriculumEntity(token, "/subjects", {
        code: "MATH",
        name: "Mathematics",
        discipline: "mathematics",
      })) as { id: string };
      const grades = await fetchGrades();
      const grade10 = grades.find((g) => g.number === 10) ?? grades[0];
      const book = (await createCurriculumEntity(token, "/books", {
        curriculum_version_id: v.id,
        grade_id: grade10.id,
        subject_id: subj.id,
        title: "Class 10 Mathematics Foundation",
        publisher: "Go4Guru Original",
      })) as { id: string };
      const chap = (await createCurriculumEntity(token, "/chapters", {
        book_id: book.id,
        sequence_no: 1,
        code: "CH-1",
        title: "Linear Equations",
      })) as { id: string };
      await createCurriculumEntity(token, `/versions/${v.id}/publish`, {});
      setCreatedIds((prev) => ({
        ...prev,
        boardId: b.id,
        sessionId: s.id,
        versionId: v.id,
        gradeId: grade10.id,
        subjectId: subj.id,
        bookId: book.id,
        chapterId: chap.id,
      }));
      setStatusMsg("Created and published initial syllabus hierarchy.");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Curriculum creation failed.");
    }
  }

  async function handleUploadExcel(e: FormEvent) {
    e.preventDefault();
    if (!token || !file) return;
    setError(null);
    setStatusMsg(null);
    try {
      const b = await uploadImportWorkbook(token, file);
      setBatch(b);
      const headers = b.detected_sheets[0]?.headers ?? [];
      setStemHeader(headers[0] ?? "");
      setAnswerHeader(headers[headers.length - 1] ?? "");
      setStatusMsg(
        `Uploaded ${b.original_filename}: detected sheet '${b.selected_sheet}' with ${b.total_rows} rows.`
      );
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Upload failed.");
    }
  }

  async function handleMapAndValidate() {
    if (!token || !batch || !batch.selected_sheet) return;
    setError(null);
    if (
      !createdIds.versionId ||
      !createdIds.gradeId ||
      !createdIds.subjectId ||
      !createdIds.chapterId ||
      !createdIds.sourceId ||
      !createdIds.licenseId
    ) {
      setError(
        "Need curriculum version/grade/subject/chapter and approved source/license IDs set."
      );
      return;
    }
    try {
      await saveImportMapping(token, batch.id, {
        selected_sheet: batch.selected_sheet,
        column_map: {
          stem_markdown: stemHeader,
          correct_answer: answerHeader,
          ...(optAHeader ? { option_a: optAHeader } : {}),
          ...(optBHeader ? { option_b: optBHeader } : {}),
          ...(optCHeader ? { option_c: optCHeader } : {}),
          ...(optDHeader ? { option_d: optDHeader } : {}),
        },
        default_curriculum_version_id: createdIds.versionId,
        default_grade_id: createdIds.gradeId,
        default_subject_id: createdIds.subjectId,
        default_chapter_id: createdIds.chapterId,
        source_id: createdIds.sourceId,
        license_id: createdIds.licenseId,
      });
      const validated = await validateImportBatch(token, batch.id);
      setBatch(validated);
      const prev = await fetchImportPreview(token, batch.id);
      setPreview(prev);
      setStatusMsg(
        `Validated ${validated.total_rows} rows: valid=${validated.valid_rows}, warnings=${validated.warning_rows}, errors=${validated.error_rows}, duplicates=${validated.duplicate_rows}.`
      );
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Validation failed.");
    }
  }

  async function handleCreateQuickQuestion(e: FormEvent) {
    e.preventDefault();
    if (!token || !createdIds.versionId || !createdIds.sourceId || !createdIds.licenseId) {
      setError("Select or create curriculum + rights first.");
      return;
    }
    try {
      await createQuestionApi(token, {
        question_type: "numerical",
        curriculum_version_id: createdIds.versionId,
        grade_id: createdIds.gradeId,
        subject_id: createdIds.subjectId,
        chapter_id: createdIds.chapterId,
        stem_markdown: qStem,
        correct_answer_jsonb: { expected_value: Number(qNumAns), tolerance_abs: 0.01 },
        provenance: {
          source_id: createdIds.sourceId,
          license_id: createdIds.licenseId,
          source_type: "original",
        },
      });
      setQStem("");
      setStatusMsg("Question drafted in Question Bank.");
      await refreshData(token);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Question creation failed.");
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Admin &amp; Reviewer Studio
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Signed in as {user?.email} ({user?.roles.join(", ")})
          </p>
        </div>
        <div className="flex gap-2">
          {(["imports", "curriculum", "questions"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
                tab === t
                  ? "bg-indigo-700 text-white"
                  : "border border-slate-300 bg-white text-slate-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </header>

      {error ? <ErrorBanner title="Admin Action Error" message={error} /> : null}
      {statusMsg ? (
        <div
          role="status"
          className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900"
        >
          {statusMsg}
        </div>
      ) : null}
      {loading ? <LoadingCard message="Loading admin catalogs..." /> : null}

      {!loading && tab === "curriculum" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Create &amp; Publish Syllabus Version
          </h2>
          <form
            onSubmit={(e) => void handleBootstrapCurriculum(e)}
            className="mt-4 grid gap-3 sm:grid-cols-2"
          >
            <input
              type="text"
              value={boardCode}
              onChange={(e) => setBoardCode(e.target.value)}
              placeholder="Board Code (e.g., CBSE)"
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="text"
              value={boardName}
              onChange={(e) => setBoardName(e.target.value)}
              placeholder="Board Name"
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="rounded bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800 sm:col-span-2"
            >
              Create &amp; Publish Starter Board/Session/Book/Chapter
            </button>
          </form>
        </section>
      ) : null}

      {!loading && tab === "questions" ? (
        <section className="space-y-6">
          <form
            onSubmit={(e) => void handleCreateQuickQuestion(e)}
            className="space-y-3 rounded-xl border border-slate-200 bg-white p-6"
          >
            <h2 className="text-lg font-semibold text-slate-900">
              Author Original Numerical Question
            </h2>
            <p className="text-xs text-slate-600">
              Registered Sources: {sources.length} | Licenses: {licenses.length}
            </p>
            <textarea
              required
              rows={2}
              value={qStem}
              onChange={(e) => setQStem(e.target.value)}
              placeholder="Question stem (supports $LaTeX$)"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="number"
              step="any"
              value={qNumAns}
              onChange={(e) => setQNumAns(e.target.value)}
              placeholder="Expected numeric value"
              className="w-48 rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="ml-3 rounded bg-indigo-700 px-4 py-2 text-sm font-medium text-white"
            >
              Save Draft Question
            </button>
          </form>

          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900">
              Question Bank ({questions.length})
            </h2>
            <ul className="mt-3 space-y-2 text-sm">
              {questions.map((q) => (
                <li
                  key={q.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 p-3"
                >
                  <div>
                    <StatusBadge
                      tone={q.status === "PUBLISHED" ? "healthy" : "neutral"}
                    >
                      {q.status}
                    </StatusBadge>
                    <span className="ml-2 font-medium text-slate-900">
                      {q.stem_markdown}
                    </span>
                  </div>
                  {q.status !== "PUBLISHED" && token ? (
                    <button
                      type="button"
                      onClick={async () => {
                        await reviewQuestionApi(token, q.id, {
                          decision: "approved",
                          publish: true,
                        });
                        await refreshData(token);
                      }}
                      className="rounded bg-emerald-700 px-3 py-1 text-xs font-medium text-white"
                    >
                      Approve &amp; Publish
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}

      {!loading && tab === "imports" ? (
        <section className="space-y-6 rounded-xl border border-slate-200 bg-white p-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              14-Stage Excel / CSV Question Import Staging
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Inspects uploaded workbook headers dynamically without hardcoded assumptions; archives raw files immutably and supports batch rollback.
            </p>
          </div>

          <form onSubmit={(e) => void handleUploadExcel(e)} className="flex flex-wrap items-center gap-3">
            <input
              type="file"
              accept=".xlsx,.csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-sm"
            />
            <button
              type="submit"
              disabled={!file}
              className="rounded bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Upload &amp; Inspect Sheets
            </button>
          </form>

          {batch ? (
            <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">
                  Batch {batch.original_filename} ({batch.status})
                </p>
                <StatusBadge tone="neutral">{batch.total_rows} rows</StatusBadge>
              </div>
              <p className="text-xs text-slate-600">
                Detected headers:{" "}
                {(batch.detected_sheets[0]?.headers ?? []).join(", ") || "None"}
              </p>

              <div className="grid gap-3 sm:grid-cols-3">
                <input
                  type="text"
                  placeholder="Header -> stem_markdown"
                  value={stemHeader}
                  onChange={(e) => setStemHeader(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Header -> correct_answer"
                  value={answerHeader}
                  onChange={(e) => setAnswerHeader(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Header -> option_a (optional)"
                  value={optAHeader}
                  onChange={(e) => setOptAHeader(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Header -> option_b (optional)"
                  value={optBHeader}
                  onChange={(e) => setOptBHeader(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Header -> option_c (optional)"
                  value={optCHeader}
                  onChange={(e) => setOptCHeader(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
                />
                <input
                  type="text"
                  placeholder="Header -> option_d (optional)"
                  value={optDHeader}
                  onChange={(e) => setOptDHeader(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void handleMapAndValidate()}
                  className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
                >
                  Save Mapping &amp; Validate
                </button>
                {batch.status === "preview_ready" && token ? (
                  <button
                    type="button"
                    onClick={async () => {
                      const res = await commitImportBatch(token, batch.id);
                      setStatusMsg(
                        `Committed ${res.committed_count} questions into ${res.status}.`
                      );
                    }}
                    className="rounded bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white"
                  >
                    Commit Valid Rows
                  </button>
                ) : null}
                {batch.status === "committed" && token ? (
                  <button
                    type="button"
                    onClick={async () => {
                      const res = await rollbackImportBatch(token, batch.id);
                      setStatusMsg(
                        `Rolled back ${res.rolled_back_questions} uncommitted draft questions.`
                      );
                    }}
                    className="rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white"
                  >
                    Rollback Batch
                  </button>
                ) : null}
              </div>

              {preview ? (
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-300">
                      <th className="py-1">Row</th>
                      <th className="py-1">Status</th>
                      <th className="py-1">Errors / Warnings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r) => (
                      <tr key={r.id} className="border-b border-slate-200">
                        <td className="py-1">{r.row_number}</td>
                        <td className="py-1 font-mono">{r.validation_status}</td>
                        <td className="py-1">
                          {[...r.errors, ...r.warnings].join("; ") || "OK"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
