"use client";

import type { ApiMetaResponse, ReadinessResponse } from "@go4guru/contracts";
import { ErrorBanner, StatusBadge } from "@go4guru/ui";
import { WHITEBOARD_OPCODES } from "@go4guru/whiteboard-schema";
import { useCallback, useEffect, useState } from "react";
import { ApiClientError, fetchApiMeta, fetchReadiness } from "@/lib/api-client";

interface FoundationState {
  loading: boolean;
  readiness: ReadinessResponse | null;
  meta: ApiMetaResponse | null;
  error: { message: string; code: string; requestId?: string } | null;
}

export function FoundationStatus() {
  const [state, setState] = useState<FoundationState>({
    loading: true,
    readiness: null,
    meta: null,
    error: null,
  });

  const loadStatus = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const [readiness, meta] = await Promise.all([
        fetchReadiness(),
        fetchApiMeta(),
      ]);
      setState({ loading: false, readiness, meta, error: null });
    } catch (err) {
      if (err instanceof ApiClientError) {
        setState({
          loading: false,
          readiness: null,
          meta: null,
          error: {
            message: err.message,
            code: err.code,
            requestId: err.requestId,
          },
        });
        return;
      }
      setState({
        loading: false,
        readiness: null,
        meta: null,
        error: {
          code: "NETWORK_UNREACHABLE",
          message:
            "Backend API is unreachable. Start apps/api on port 8000 to verify live readiness.",
        },
      });
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  return (
    <section aria-labelledby="foundation-status-heading" className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h2
            id="foundation-status-heading"
            className="text-xl font-semibold text-slate-900"
          >
            Phase 0 Runtime &amp; Module Verification
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Live probe of FastAPI backend dependencies and modular monolith
            boundaries. Product dashboards remain disabled until Phases 1–12.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadStatus()}
          disabled={state.loading}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 disabled:opacity-60"
        >
          {state.loading ? "Checking..." : "Refresh Probe"}
        </button>
      </div>

      {state.loading ? (
        <div
          role="status"
          aria-live="polite"
          className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600"
        >
          Probing FastAPI readiness and modular boundaries...
        </div>
      ) : null}

      {!state.loading && state.error ? (
        <ErrorBanner
          title={`Backend Readiness Unavailable (${state.error.code})`}
          message={state.error.message}
          requestId={state.error.requestId}
        />
      ) : null}

      {!state.loading && state.readiness ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                API Overall Status
              </h3>
              <StatusBadge
                tone={
                  state.readiness.status === "ready" ? "healthy" : "degraded"
                }
              >
                {state.readiness.status === "ready"
                  ? "Ready"
                  : "Degraded (503)"}
              </StatusBadge>
            </div>
            <dl className="mt-4 space-y-2 text-sm text-slate-700">
              <div className="flex justify-between">
                <dt className="text-slate-500">Service</dt>
                <dd className="font-mono">{state.readiness.service}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Version</dt>
                <dd className="font-mono">{state.readiness.version}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Environment</dt>
                <dd className="font-mono">{state.readiness.environment}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Dependency Checks
            </h3>
            <ul className="mt-4 space-y-3 text-sm">
              {Object.entries(state.readiness.checks).map(([name, check]) => (
                <li
                  key={name}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="font-mono font-medium text-slate-800">
                    {name}
                  </span>
                  <div className="flex items-center gap-2">
                    {check.error ? (
                      <span className="font-mono text-xs text-slate-500">
                        {check.error}
                      </span>
                    ) : null}
                    <StatusBadge
                      tone={check.status === "up" ? "healthy" : "degraded"}
                    >
                      {check.status === "up" ? "Up" : "Down"}
                    </StatusBadge>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      {!state.loading && state.meta ? (
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-semibold text-slate-900">
              Registered Modular Monolith Domains ({state.meta.modules.length})
            </h3>
            <span className="font-mono text-xs text-slate-500">
              REST: {state.meta.api_prefix} | WS: {state.meta.ws_prefix}
            </span>
          </div>
          {state.meta.modules.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No backend modules reported.
            </p>
          ) : (
            <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {state.meta.modules.map((mod) => (
                <li
                  key={mod.name}
                  className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                >
                  <span className="font-mono font-medium text-slate-800">
                    {mod.name}
                  </span>
                  <StatusBadge tone="neutral">{mod.planned_phase}</StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
        Shared contract status: <span className="font-mono">@go4guru/whiteboard-schema</span>{" "}
        exports {WHITEBOARD_OPCODES.length} canonical whiteboard opcodes (runtime
        activates in Phase 4).
      </div>
    </section>
  );
}
