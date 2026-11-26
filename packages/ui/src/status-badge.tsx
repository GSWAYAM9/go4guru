import type { ReactNode } from "react";

export type BadgeTone = "healthy" | "degraded" | "neutral";

const TONE_STYLES: Record<BadgeTone, string> = {
  healthy: "border-emerald-700/30 bg-emerald-50 text-emerald-900",
  degraded: "border-amber-700/30 bg-amber-50 text-amber-900",
  neutral: "border-slate-300 bg-slate-100 text-slate-800",
};

export interface StatusBadgeProps {
  tone: BadgeTone;
  children: ReactNode;
}

/** Accessible status pill relying on explicit text + border contrast, not color alone. */
export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE_STYLES[tone]}`}
    >
      {children}
    </span>
  );
}
