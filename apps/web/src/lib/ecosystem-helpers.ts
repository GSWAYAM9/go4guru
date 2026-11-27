/**
 * Pure domain helpers for Phase 7 (Teacher, Mentor, Parent) and
 * Phase 8 (Multi-Tenant Institution & Subscription) UI workspaces.
 */

export interface GradeOverrideDelta {
  effectiveScore: number;
  percentage: number;
  overridden: boolean;
  deltaFromAi: number | null;
}

export function computeGradeOverrideDelta(params: {
  aiSuggestedScore: number | null;
  teacherScore: number | null;
  maxMarks: number;
}): GradeOverrideDelta {
  const safeMax = params.maxMarks > 0 ? params.maxMarks : 1;
  const effectiveScore =
    params.teacherScore !== null
      ? params.teacherScore
      : (params.aiSuggestedScore ?? 0);
  const percentage = Math.round((effectiveScore / safeMax) * 1000) / 10;
  const overridden = params.teacherScore !== null;
  const deltaFromAi =
    params.teacherScore !== null && params.aiSuggestedScore !== null
      ? Math.round((params.teacherScore - params.aiSuggestedScore) * 100) / 100
      : null;

  return { effectiveScore, percentage, overridden, deltaFromAi };
}

export interface SeatQuotaHealth {
  utilizationPct: number;
  tone: "healthy" | "degraded" | "neutral";
  warning: string | null;
}

export function evaluateSeatQuotaHealth(
  usedSeats: number,
  seatLimit: number,
  subscriptionStatus?: string | null
): SeatQuotaHealth {
  if (
    subscriptionStatus &&
    subscriptionStatus !== "active" &&
    subscriptionStatus !== "trial"
  ) {
    return {
      utilizationPct: 100,
      tone: "degraded",
      warning: `Subscription is ${subscriptionStatus}. Enrollment mutations are paused.`,
    };
  }
  if (seatLimit <= 0) {
    return {
      utilizationPct: 0,
      tone: "neutral",
      warning: "No seat quota configured.",
    };
  }
  const pct = Math.min(100, Math.round((usedSeats / seatLimit) * 1000) / 10);
  if (pct >= 90) {
    return {
      utilizationPct: pct,
      tone: "degraded",
      warning: `Approaching seat limit (${usedSeats}/${seatLimit}). Consider upgrading plan.`,
    };
  }
  return { utilizationPct: pct, tone: "healthy", warning: null };
}

export function formatConsentStatusLabel(
  status: "pending" | "verified" | "revoked" | string
): { label: string; tone: "healthy" | "degraded" | "neutral" } {
  if (status === "verified") {
    return { label: "Consent Verified", tone: "healthy" };
  }
  if (status === "revoked") {
    return { label: "Revoked", tone: "degraded" };
  }
  return { label: "Consent Pending", tone: "neutral" };
}

export function sanitizeSlugInput(raw: string): string {
  return raw
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

export function triggerCsvDownload(filename: string, csvContent: string): void {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
