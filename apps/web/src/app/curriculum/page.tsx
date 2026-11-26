"use client";

import type {
  CurriculumTreeResponse,
  GradeOut,
  SubjectOut,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiClientError,
  fetchCurriculumTree,
  fetchGrades,
  fetchSubjects,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function CurriculumPage() {
  const { token } = useAuth();
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [subjects, setSubjects] = useState<SubjectOut[]>([]);
  const [gradeId, setGradeId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [tree, setTree] = useState<CurriculumTreeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRefs() {
      try {
        const [g, s] = await Promise.all([fetchGrades(), fetchSubjects()]);
        setGrades(g);
        setSubjects(s);
      } catch {
        // Handled when loading tree
      }
    }
    void loadRefs();
  }, []);

  useEffect(() => {
    async function loadTree() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchCurriculumTree({
          gradeId: gradeId || undefined,
          subjectId: subjectId || undefined,
          token,
        });
        setTree(res);
      } catch (err) {
        setError(
          err instanceof ApiClientError
            ? err.message
            : "Unable to load published curriculum."
        );
      } finally {
        setLoading(false);
      }
    }
    void loadTree();
  }, [gradeId, subjectId, token]);

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Versioned Curriculum Explorer
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Browse published Board → Session → Class → Subject → Book → Chapter → Topic → Concept hierarchies.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <div>
            <label htmlFor="filter-grade" className="block text-xs font-medium text-slate-600">
              Class
            </label>
            <select
              id="filter-grade"
              value={gradeId}
              onChange={(e) => setGradeId(e.target.value)}
              className="mt-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm"
            >
              <option value="">All Classes (6–12)</option>
              {grades.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-subject" className="block text-xs font-medium text-slate-600">
              Subject
            </label>
            <select
              id="filter-subject"
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="mt-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm"
            >
              <option value="">All Subjects</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {loading ? <LoadingCard message="Loading published syllabus tree..." /> : null}
      {!loading && error ? <ErrorBanner title="Curriculum Error" message={error} /> : null}

      {!loading && !error && !tree ? (
        <EmptyState
          title="No Published Curriculum Version Yet"
          description="Published syllabus versions created by Content Admins appear here. Unverified or draft versions are never exposed to learners."
          action={
            <Link
              href="/admin"
              className="inline-block rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
            >
              Open Admin Studio
            </Link>
          }
        />
      ) : null}

      {!loading && !error && tree ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <StatusBadge tone="healthy">Published</StatusBadge>
            <span className="font-semibold text-slate-900">
              {tree.board.name} ({tree.board.code})
            </span>
            <span className="text-slate-600">
              Session {tree.academic_session.code} • Version {tree.version.version_tag}
            </span>
          </div>

          {tree.books.length === 0 ? (
            <EmptyState
              title="No matching books for selected filters"
              description="Try clearing the Class or Subject filter, or ask a Content Admin to add books to this curriculum version."
            />
          ) : (
            tree.books.map((book) => (
              <section
                key={book.id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">
                      {book.title}
                    </h2>
                    <p className="text-xs text-slate-600">
                      {book.grade_label} • {book.subject_name} • Publisher:{" "}
                      {book.publisher}
                    </p>
                  </div>
                  {book.official_source_url ? (
                    <a
                      href={book.official_source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-medium text-indigo-700 underline"
                    >
                      Official Reference Link
                    </a>
                  ) : null}
                </div>

                <div className="mt-4 space-y-4">
                  {book.chapters.map((ch) => (
                    <div
                      key={ch.id}
                      className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <h3 className="font-semibold text-slate-900">
                            Ch {ch.sequence_no}: {ch.title}
                          </h3>
                          {ch.summary ? (
                            <p className="mt-0.5 text-xs text-slate-600">
                              {ch.summary}
                            </p>
                          ) : null}
                        </div>
                        <Link
                          href={`/practice?chapterId=${ch.id}&subjectId=${book.subject_id}`}
                          className="rounded-md bg-indigo-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-800"
                        >
                          Practice Chapter
                        </Link>
                      </div>

                      {ch.topics.length > 0 ? (
                        <ul className="mt-3 space-y-2 border-t border-slate-200 pt-3 text-sm">
                          {ch.topics.map((tp) => (
                            <li key={tp.id} className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-slate-800">
                                  Topic {tp.sequence_no}: {tp.title}
                                </span>
                              </div>
                              {tp.concepts.length > 0 ? (
                                <div className="ml-4 flex flex-wrap gap-2">
                                  {tp.concepts.map((cp) => (
                                    <Link
                                      key={cp.id}
                                      href={`/practice?conceptId=${cp.id}&chapterId=${ch.id}&subjectId=${book.subject_id}`}
                                      className="rounded border border-indigo-200 bg-white px-2.5 py-1 text-xs text-indigo-900 hover:bg-indigo-50"
                                    >
                                      {cp.code}: {cp.title}
                                      {cp.learning_objectives.length > 0
                                        ? ` (${cp.learning_objectives.length} LO)`
                                        : ""}
                                    </Link>
                                  ))}
                                </div>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  ))}
                </div>
              </section>
            ))
          )}
        </div>
      ) : null}
    </main>
  );
}
