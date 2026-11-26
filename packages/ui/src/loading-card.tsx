export interface LoadingCardProps {
  message?: string;
}

/** Accessible loading state container with polite live announcement. */
export function LoadingCard({ message = "Loading..." }: LoadingCardProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-xs"
    >
      {message}
    </div>
  );
}
