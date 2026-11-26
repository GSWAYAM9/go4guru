export interface ErrorBannerProps {
  title: string;
  message: string;
  requestId?: string;
}

/** Accessible alert banner surfacing truthful failure states with optional request_id. */
export function ErrorBanner({ title, message, requestId }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-700/30 bg-red-50 p-4 text-sm text-red-950"
    >
      <p className="font-semibold">{title}</p>
      <p className="mt-1">{message}</p>
      {requestId ? (
        <p className="mt-2 font-mono text-xs text-red-900">Request ID: {requestId}</p>
      ) : null}
    </div>
  );
}
