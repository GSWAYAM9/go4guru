"use client";

import type { ExamSyllabusChapterOut, ExamSyllabusResponse } from "@go4guru/contracts";
import { EmptyState, StatusBadge } from "@go4guru/ui";
import { useMemo, useState } from "react";

interface SyllabusPracticeTabProps {
  syllabus: ExamSyllabusResponse | null;
  launchingKey: string | null;
  onStartChapterPractice: (chapter: ExamSyllabusChapterOut) => void;
  onStartTopicPractice: (
    chapter: ExamSyllabusChapterOut,
    topicId: string,
    topicTitle: string
  ) => void;
}

export function SyllabusPracticeTab({
  syllabus,
  launchingKey,
  onStartChapterPractice,
  onStartTopicPractice,
}: SyllabusPracticeTabProps) {
  const [subjectFilter, setSubjectFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [expandedChapterId, setExpandedChapterId] = useState<string | null>(
    null
  );

  const subjects = useMemo(() => {
    if (!syllabus) return [];
    const seen = new Map<string, string>();
    for (const ch of syllabus.chapters) {
      seen.set(ch.subject_id, ch.subject_name);
    }
    return Array.from(seen.entries());
  }, [syllabus]);

  const filteredChapters = useMemo(() => {
    if (!syllabus) return [];
    return syllabus.chapters.filter((ch) => {
      if (subjectFilter !== "all" && ch.subject_id !== subjectFilter) {
        return false;
      }
      if (priorityFilter !== "all" && ch.priority_tier !== priorityFilter) {
        return false;
      }
      return true;
    });
  }, [syllabus, subjectFilter, priorityFilter]);

  if (!syllabus || syllabus.chapters.length === 0) {
    return (
      <EmptyState
        title="No syllabus chapters mapped yet for this version"
        description="Academic reviewers and content administrators can map versioned chapter weightages, priority tiers, and audit statuses to populate this syllabus matrix."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Syllabus &amp; Chapter Weightage Matrix
          </h2>
          <p className="text-xs text-slate-600">
            Blueprint version:{" "}
            <span className="font-mono font-semibold text-slate-800">
              {syllabus.pattern_version_label}
            </span>{" "}
            · Launch chapter-wise or topic-wise timed practice directly from
            mapped chapters.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Filter syllabus by subject"
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800"
          >
            <option value="all">All Subjects</option>
            {subjects.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter syllabus by priority"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800"
          >
            <option value="all">All Priority Tiers</option>
            <option value="high_yield">High Yield</option>
            <option value="core">Core</option>
            <option value="optional">Optional</option>
          </select>
        </div>
      </div>

      {filteredChapters.length === 0 ? (
        <EmptyState
          title="No chapters match your active filters"
          description="Clear the subject or priority filter to inspect all mapped chapters."
        />
      ) : (
        <div className="space-y-3">
          {filteredChapters.map((ch) => {
            const isExpanded = expandedChapterId === ch.chapter_id;
            const chapBusy = launchingKey === `chap:${ch.chapter_id}`;

            return (
              <article
                key={ch.id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                        {ch.subject_name}
                      </span>
                      <StatusBadge
                        tone={
                          ch.priority_tier === "high_yield"
                            ? "degraded"
                            : ch.priority_tier === "core"
                              ? "healthy"
                              : "neutral"
                        }
                      >
                        {ch.priority_tier.replace("_", " ")}
                      </StatusBadge>
                      <StatusBadge
                        tone={ch.audit_verified ? "healthy" : "degraded"}
                      >
                        {ch.audit_verified ? "Audited" : "Unverified Audit"}
                      </StatusBadge>
                      {ch.syllabus_status !== "included" && (
                        <StatusBadge tone="neutral">
                          {ch.syllabus_status}
                        </StatusBadge>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-slate-900">
                      {ch.chapter_title}
                    </h3>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
                      <span>
                        Weightage:{" "}
                        <strong className="text-slate-900">
                          {ch.weightage_pct.toFixed(1)}%
                        </strong>
                      </span>
                      <span>
                        Expected Qs:{" "}
                        <strong className="text-slate-900">
                          {ch.expected_questions}
                        </strong>
                      </span>
                      <span>
                        Published Qs:{" "}
                        <strong className="text-slate-900">
                          {ch.published_question_count}
                        </strong>
                      </span>
                      <span>
                        Verified PYQs:{" "}
                        <strong className="text-emerald-800">
                          {ch.verified_pyq_count}
                        </strong>
                      </span>
                    </div>
                    {ch.notes && (
                      <p className="text-xs text-slate-500">{ch.notes}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {ch.topics.length > 0 && (
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedChapterId(
                            isExpanded ? null : ch.chapter_id
                          )
                        }
                        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                      >
                        {isExpanded
                          ? "Hide Topics"
                          : `Topics (${ch.topics.length})`}
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={
                        chapBusy ||
                        ch.published_question_count === 0 ||
                        ch.syllabus_status === "excluded"
                      }
                      onClick={() => onStartChapterPractice(ch)}
                      className="rounded-lg bg-indigo-700 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {chapBusy
                        ? "Launching..."
                        : ch.published_question_count === 0
                          ? "No Published Qs"
                          : "Chapter Practice"}
                    </button>
                  </div>
                </div>

                {isExpanded && ch.topics.length > 0 && (
                  <div className="mt-3 border-t border-slate-100 pt-3">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Topic-Wise Practice Launchers
                    </p>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {ch.topics.map((topic) => {
                        const topicBusy =
                          launchingKey === `topic:${topic.id}`;
                        return (
                          <div
                            key={topic.id}
                            className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
                          >
                            <span className="truncate text-xs font-medium text-slate-800">
                              {topic.title}
                            </span>
                            <button
                              type="button"
                              disabled={topicBusy}
                              onClick={() =>
                                onStartTopicPractice(ch, topic.id, topic.title)
                              }
                              className="shrink-0 rounded bg-white px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50 disabled:opacity-50"
                            >
                              {topicBusy ? "..." : "Practice"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
