/**
 * Pure TypeScript helpers for Phase 9 Examination Preparation Ecosystem.
 * Zero DOM/React imports — directly unit-testable via `node:test`.
 */

import type {
  ExamCoverageAuditOut,
  ExamPatternOut,
  ExamQuestionItemOut,
  ScoringRuleContract,
} from "@go4guru/contracts";

export interface ExamTrackPresentation {
  code: string;
  shortLabel: string;
  subtitle: string;
  accentBg: string;
  accentText: string;
  accentBorder: string;
}

const TRACK_META: Record<string, ExamTrackPresentation> = {
  CBSE_BOARD: {
    code: "CBSE_BOARD",
    shortLabel: "CBSE Board",
    subtitle: "Class 10 & 12 Competency & Step-Rubric Blueprint",
    accentBg: "bg-sky-50",
    accentText: "text-sky-900",
    accentBorder: "border-sky-200",
  },
  JEE_MAIN: {
    code: "JEE_MAIN",
    shortLabel: "JEE Main",
    subtitle: "NTA PCM MCQ + Numerical (+4/-1) Timed Simulation",
    accentBg: "bg-indigo-50",
    accentText: "text-indigo-900",
    accentBorder: "border-indigo-200",
  },
  JEE_ADVANCED: {
    code: "JEE_ADVANCED",
    shortLabel: "JEE Advanced",
    subtitle: "Multi-Correct Partial Marking (+4/+3/+2/+1/-2) & Matrix Match",
    accentBg: "bg-violet-50",
    accentText: "text-violet-900",
    accentBorder: "border-violet-200",
  },
  NEET: {
    code: "NEET",
    shortLabel: "NEET-UG",
    subtitle: "Physics, Chemistry & Biology Speed-Accuracy (+4/-1)",
    accentBg: "bg-emerald-50",
    accentText: "text-emerald-900",
    accentBorder: "border-emerald-200",
  },
};

export function getExamTrackPresentation(code: string): ExamTrackPresentation {
  const norm = code.trim().toUpperCase();
  return (
    TRACK_META[norm] ?? {
      code: norm,
      shortLabel: norm.replaceAll("_", " "),
      subtitle: "Versioned Configurable Examination Track",
      accentBg: "bg-slate-50",
      accentText: "text-slate-900",
      accentBorder: "border-slate-200",
    }
  );
}

export function formatScoringRuleLabel(rule: ScoringRuleContract): string {
  const pos = `+${rule.correct_marks}`;
  const neg = rule.wrong_marks < 0 ? `${rule.wrong_marks}` : "0";
  if (rule.mode === "jee_adv_partial") {
    return `${pos}/+3/+2/+1 / ${neg} (Partial Subset)`;
  }
  if (rule.mode === "partial_subset") {
    return `${pos} (+${rule.partial_credit_per_correct_option}/opt) / ${neg}`;
  }
  return `${pos} / ${neg} (No Negative)`.replace(
    rule.wrong_marks < 0 ? " (No Negative)" : "",
    ""
  );
}

export function formatExamDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds <= 0) return "Untimed";
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  if (hrs > 0 && mins > 0) return `${hrs}h ${mins}m`;
  if (hrs > 0) return `${hrs}h`;
  return `${mins} min`;
}

export function computePatternMaxMarks(pattern: ExamPatternOut | null): number {
  if (!pattern) return 0;
  return pattern.rules.sections.reduce((acc, sec) => {
    const countable = sec.attempt_limit
      ? Math.min(sec.question_count, sec.attempt_limit)
      : sec.question_count;
    return acc + countable * sec.scoring.correct_marks;
  }, 0);
}

export function computePatternTotalQuestions(
  pattern: ExamPatternOut | null
): number {
  if (!pattern) return 0;
  return pattern.rules.sections.reduce((acc, sec) => acc + sec.question_count, 0);
}

export function getCoverageBadgeMeta(audit: ExamCoverageAuditOut): {
  tone: "healthy" | "degraded" | "neutral";
  label: string;
} {
  switch (audit.coverage_status) {
    case "audited_complete":
      return { tone: "healthy", label: "Audited Coverage Verified" };
    case "audited_partial":
      return { tone: "degraded", label: "Partial Audited Coverage" };
    case "partial_unverified":
      return { tone: "degraded", label: "Unverified Partial Dataset" };
    default:
      return { tone: "neutral", label: "No Audited Syllabus Mapped Yet" };
  }
}

export function getPacingBadgeMeta(pacingStatus: string): {
  tone: "healthy" | "degraded" | "neutral";
  label: string;
} {
  switch (pacingStatus) {
    case "fast_accurate":
      return { tone: "healthy", label: "Exam-Ready Pace & Accuracy" };
    case "on_pace_accurate":
      return { tone: "healthy", label: "On Target Pace" };
    case "rushing_errors":
      return { tone: "degraded", label: "Rushing — Negative Marking Risk" };
    case "slow_accurate":
      return { tone: "degraded", label: "Accurate but Slow" };
    case "slow_needs_drill":
      return { tone: "degraded", label: "Needs Speed & Concept Drill" };
    default:
      return { tone: "neutral", label: "Awaiting First Timed Attempt" };
  }
}

/**
 * Frontend defense-in-depth guard: only render a Verified PYQ citation when
 * backend verification fields are explicitly verified and complete.
 */
export function hasVerifiedPyqBadge(question: ExamQuestionItemOut): boolean {
  const p = question.pyq_provenance;
  if (!p) return false;
  return (
    p.is_verified_pyq === true &&
    p.verification_status === "verified" &&
    Boolean(p.exam_name?.trim()) &&
    Number.isInteger(p.exam_year) &&
    p.exam_year >= 1980 &&
    p.exam_year <= 2035
  );
}

export function formatQuestionTypeLabel(qtype: string): string {
  const map: Record<string, string> = {
    mcq_single: "Single Choice MCQ",
    mcq_multiple: "Multi-Correct MCQ",
    numerical: "Numerical Value",
    integer: "Integer Type",
    assertion_reason: "Assertion-Reason",
    case_study: "Case-Based",
    match_following: "Match List",
    matrix_match: "Matrix Match",
    short_answer: "Short Answer",
    long_answer: "Long Answer",
  };
  return map[qtype] ?? qtype.replaceAll("_", " ");
}

export function formatAnswerPayload(
  payload: Record<string, unknown> | null | undefined
): string {
  if (!payload || Object.keys(payload).length === 0) {
    return "Unattempted";
  }
  if (typeof payload.selected_key === "string" && payload.selected_key.trim()) {
    return `Option ${payload.selected_key.trim().toUpperCase()}`;
  }
  if (typeof payload.correct_key === "string" && payload.correct_key.trim()) {
    return `Option ${payload.correct_key.trim().toUpperCase()}`;
  }
  if (Array.isArray(payload.selected_keys) && payload.selected_keys.length > 0) {
    return `Options ${payload.selected_keys.map((k) => String(k).toUpperCase()).join(", ")}`;
  }
  if (Array.isArray(payload.correct_keys) && payload.correct_keys.length > 0) {
    return `Options ${payload.correct_keys.map((k) => String(k).toUpperCase()).join(", ")}`;
  }
  if (payload.numeric_value !== undefined && payload.numeric_value !== null) {
    return String(payload.numeric_value);
  }
  if (payload.expected_value !== undefined && payload.expected_value !== null) {
    const tol =
      typeof payload.tolerance_abs === "number" && payload.tolerance_abs > 0
        ? ` (±${payload.tolerance_abs})`
        : "";
    return `${String(payload.expected_value)}${tol}`;
  }
  const matchObj =
    (payload.matches as Record<string, unknown> | undefined) ??
    (payload.expected_matches as Record<string, unknown> | undefined);
  if (matchObj && typeof matchObj === "object" && Object.keys(matchObj).length > 0) {
    return Object.entries(matchObj)
      .map(([k, v]) => `${k}→${String(v)}`)
      .join(", ");
  }
  if (typeof payload.text_answer === "string" && payload.text_answer.trim()) {
    return payload.text_answer.trim();
  }
  if (typeof payload.expected_text === "string" && payload.expected_text.trim()) {
    return payload.expected_text.trim();
  }
  return JSON.stringify(payload);
}
