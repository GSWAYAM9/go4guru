"use client";

import type { ExamPatternOut, ExamTrackOverviewOut } from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import {
  computePatternMaxMarks,
  computePatternTotalQuestions,
  formatExamDuration,
  getCoverageBadgeMeta,
  getExamTrackPresentation,
} from "@/lib/exam-prep-helpers";

interface ExamTrackHeaderProps {
  tracks: ExamTrackOverviewOut[];
  selectedExamCode: string;
  selectedPatternId: string | null;
  onSelectTrack: (examCode: string) => void;
  onSelectPattern: (patternId: string) => void;
}

export function ExamTrackHeader({
  tracks,
  selectedExamCode,
  selectedPatternId,
  onSelectTrack,
  onSelectPattern,
}: ExamTrackHeaderProps) {
  const activeTrack =
    tracks.find((t) => t.code === selectedExamCode) ?? tracks[0] ?? null;
  const selectedPattern: ExamPatternOut | null =
    activeTrack?.patterns.find((p) => p.id === selectedPatternId) ??
    activeTrack?.active_pattern ??
    activeTrack?.patterns[0] ??
    null;

  const coverageMeta = activeTrack
    ? getCoverageBadgeMeta(activeTrack.coverage_audit)
    : null;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Phase 9 · Examination Preparation Ecosystem
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Configurable Exam Prep Hub
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Versioned examination rules, audited syllabus mappings, verified
            PYQ drills, server-timed mocks, pacing analytics, formula sheets,
            and personalized revision schedules across CBSE Board, JEE Main, JEE
            Advanced, and NEET-UG.
          </p>
        </div>

        {activeTrack && activeTrack.patterns.length > 0 && (
          <div className="w-full sm:w-72">
            <label
              htmlFor="exam-pattern-version"
              className="block text-xs font-semibold uppercase tracking-wide text-slate-600"
            >
              Active Rule Version
            </label>
            <select
              id="exam-pattern-version"
              value={selectedPattern?.id ?? ""}
              onChange={(e) => onSelectPattern(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900 shadow-xs focus:border-indigo-500 focus:outline-none"
            >
              {activeTrack.patterns.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.version_label} ({p.effective_year}
                  {p.is_active ? " · Active" : ""})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 4 Exam Track Selector Cards */}
      <div
        role="radiogroup"
        aria-label="Select examination track"
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
      >
        {tracks.map((track) => {
          const meta = getExamTrackPresentation(track.code);
          const isSelected = track.code === activeTrack?.code;
          const pat = track.active_pattern ?? track.patterns[0] ?? null;
          const totalQ = computePatternTotalQuestions(pat);
          const maxMarks = computePatternMaxMarks(pat);

          return (
            <button
              key={track.id}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => onSelectTrack(track.code)}
              className={`flex flex-col justify-between rounded-xl border p-4 text-left transition ${
                isSelected
                  ? `${meta.accentBg} ${meta.accentBorder} ring-2 ring-indigo-600`
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-base font-bold ${
                      isSelected ? meta.accentText : "text-slate-900"
                    }`}
                  >
                    {meta.shortLabel}
                  </span>
                  <span className="rounded bg-white/80 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {track.target_seconds_per_question}s/Q
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {meta.subtitle}
                </p>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-200/70 pt-2 text-xs text-slate-700">
                <span>{formatExamDuration(pat?.rules.duration_seconds)}</span>
                <span>·</span>
                <span>{totalQ} Q</span>
                <span>·</span>
                <span>{maxMarks} Marks</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Honest Coverage Audit & Provenance Transparency Disclosure */}
      {activeTrack && coverageMeta && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone={coverageMeta.tone}>
                {coverageMeta.label}
              </StatusBadge>
              <span className="text-sm font-semibold text-slate-900">
                {activeTrack.name} Dataset &amp; Syllabus Audit
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-700">
              <span>
                Audited Chapters:{" "}
                <strong>
                  {activeTrack.coverage_audit.audited_chapters_count}/
                  {activeTrack.coverage_audit.included_chapters_count}
                </strong>
              </span>
              <span>
                Published Qs:{" "}
                <strong>
                  {activeTrack.coverage_audit.published_question_count}
                </strong>
              </span>
              <span>
                Verified PYQs:{" "}
                <strong>{activeTrack.coverage_audit.verified_pyq_count}</strong>
              </span>
              {activeTrack.coverage_audit.unverified_pyq_excluded_count > 0 && (
                <span className="text-amber-700">
                  Unverified PYQ Claims Excluded:{" "}
                  <strong>
                    {activeTrack.coverage_audit.unverified_pyq_excluded_count}
                  </strong>
                </span>
              )}
            </div>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            {activeTrack.coverage_audit.coverage_disclaimer}
          </p>
        </div>
      )}
    </section>
  );
}
