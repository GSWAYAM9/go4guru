"use client";

import type { LanguageCapabilityOut } from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import { useMemo, useState } from "react";
import { patchLanguageCapability } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  getCapabilityStatusMeta,
  getTestingStatusMeta,
} from "@/lib/multilingual-helpers";

interface CapabilityRegistryTabProps {
  capabilities: LanguageCapabilityOut[];
  onRefresh: () => Promise<void>;
}

const ADMIN_ROLES = new Set([
  "content_admin",
  "academic_reviewer",
  "platform_admin",
]);

function SupportCell({ supported }: { supported: boolean | undefined }) {
  return supported ? (
    <span className="font-semibold text-emerald-700" aria-label="Supported">
      Yes
    </span>
  ) : (
    <span className="text-slate-400" aria-label="Not verified">
      No
    </span>
  );
}

export function CapabilityRegistryTab({
  capabilities,
  onRefresh,
}: CapabilityRegistryTabProps) {
  const { token, user } = useAuth();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [savingCode, setSavingCode] = useState<string | null>(null);
  const [editLimitations, setEditLimitations] = useState("");
  const [editCapabilityStatus, setEditCapabilityStatus] = useState("beta");
  const [editTestingStatus, setEditTestingStatus] = useState("partial");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canManage = (user?.roles ?? []).some((r) => ADMIN_ROLES.has(r));

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return capabilities.filter((cap) => {
      if (
        statusFilter !== "all" &&
        (cap.capability_status ?? "beta") !== statusFilter
      ) {
        return false;
      }
      if (!q) return true;
      return (
        cap.display_name.toLowerCase().includes(q) ||
        cap.native_name.toLowerCase().includes(q) ||
        cap.language_code.toLowerCase().includes(q) ||
        (cap.script_name ?? "").toLowerCase().includes(q)
      );
    });
  }, [capabilities, query, statusFilter]);

  const inspected = useMemo(
    () =>
      capabilities.find((c) => c.language_code === selectedCode) ??
      filtered[0] ??
      null,
    [capabilities, filtered, selectedCode]
  );

  function openInspector(cap: LanguageCapabilityOut) {
    setSelectedCode(cap.language_code);
    setEditLimitations(cap.known_limitations ?? "");
    setEditCapabilityStatus(cap.capability_status ?? "beta");
    setEditTestingStatus(cap.testing_status ?? "pending");
    setFeedback(null);
    setError(null);
  }

  async function handleGovernanceSave() {
    if (!token || !inspected) return;
    setSavingCode(inspected.language_code);
    setFeedback(null);
    setError(null);
    try {
      await patchLanguageCapability(token, inspected.language_code, {
        capability_status: editCapabilityStatus,
        testing_status: editTestingStatus,
        known_limitations: editLimitations,
      });
      await onRefresh();
      setFeedback(
        `Updated capability registry record for ${inspected.display_name} (${inspected.language_code}).`
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to update language capability metadata."
      );
    } finally {
      setSavingCode(null);
    }
  }

  return (
    <section className="space-y-6" aria-label="Language Capability Registry">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Empirical Language Capability Registry
          </h2>
          <p className="text-sm text-slate-600">
            Tracks verified capability status, provider support, testing status,
            availability, quality score, and known limitations for all{" "}
            {capabilities.length} languages. No language is advertised as fully
            supported until evaluated.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search language or script..."
            aria-label="Search languages"
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by capability status"
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          >
            <option value="all">All Statuses ({capabilities.length})</option>
            <option value="production">Production</option>
            <option value="beta">Beta</option>
            <option value="experimental">Experimental</option>
            <option value="planned">Planned</option>
          </select>
        </div>
      </div>

      {/* Capability Matrix Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3 font-semibold">Language & Script</th>
              <th className="px-3 py-3 font-semibold">Status</th>
              <th className="px-3 py-3 font-semibold">Testing</th>
              <th className="px-3 py-3 font-semibold text-center">UI</th>
              <th className="px-3 py-3 font-semibold text-center">Expl</th>
              <th className="px-3 py-3 font-semibold text-center">TTS</th>
              <th className="px-3 py-3 font-semibold text-center">STT</th>
              <th className="px-3 py-3 font-semibold text-center">Sub</th>
              <th className="px-3 py-3 font-semibold text-center">Q/A</th>
              <th className="px-3 py-3 font-semibold text-right">Quality</th>
              <th className="px-3 py-3 font-semibold">Fallback</th>
              <th className="px-4 py-3 font-semibold">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((cap) => {
              const capMeta = getCapabilityStatusMeta(cap.capability_status);
              const qaMeta = getTestingStatusMeta(cap.testing_status);
              const isSelected = inspected?.language_code === cap.language_code;

              return (
                <tr
                  key={cap.language_code}
                  className={
                    isSelected ? "bg-indigo-50/40" : "hover:bg-slate-50/70"
                  }
                >
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-900">
                      {cap.display_name}{" "}
                      <span className="font-normal text-slate-500">
                        ({cap.language_code})
                      </span>
                    </div>
                    <div className="text-slate-600">
                      {cap.native_name} · {cap.script_name || "Latin"}
                      {cap.rtl ? " · RTL" : ""}
                    </div>
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <StatusBadge tone={capMeta.tone}>{capMeta.label}</StatusBadge>
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <StatusBadge tone={qaMeta.tone}>{qaMeta.label}</StatusBadge>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <SupportCell supported={cap.ui_supported} />
                  </td>
                  <td className="px-3 py-3 text-center">
                    <SupportCell supported={cap.explanation_supported} />
                  </td>
                  <td className="px-3 py-3 text-center">
                    <SupportCell supported={cap.tts_supported} />
                  </td>
                  <td className="px-3 py-3 text-center">
                    <SupportCell supported={cap.stt_supported} />
                  </td>
                  <td className="px-3 py-3 text-center">
                    <SupportCell supported={cap.subtitle_supported} />
                  </td>
                  <td className="px-3 py-3 text-center">
                    <SupportCell
                      supported={Boolean(
                        cap.question_supported && cap.answer_supported
                      )}
                    />
                  </td>
                  <td className="px-3 py-3 text-right font-medium tabular-nums text-slate-800">
                    {cap.quality_score_pct != null
                      ? `${cap.quality_score_pct.toFixed(1)}%`
                      : "Untested"}
                  </td>
                  <td className="px-3 py-3 font-mono text-slate-700">
                    {(cap.fallback_language_code || "en").toUpperCase()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => openInspector(cap)}
                      className="whitespace-nowrap shrink-0 font-medium text-indigo-700 hover:text-indigo-900 hover:underline"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td
                  colSpan={12}
                  className="px-4 py-8 text-center text-sm text-slate-500"
                >
                  No languages matched your current search or filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Selected Language Empirical Detail & Known Limitations */}
      {inspected && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                {inspected.display_name} — {inspected.native_name} (
                {inspected.language_code})
              </h3>
              <p className="text-xs text-slate-600">
                Script: {inspected.script_name || "Latin"} · Direction:{" "}
                {inspected.rtl ? "Right-to-Left (RTL)" : "Left-to-Right (LTR)"}{" "}
                · Availability:{" "}
                <span className="font-medium text-slate-900">
                  {inspected.availability_status || "limited"}
                </span>{" "}
                · Academic review:{" "}
                <span className="font-medium text-slate-900">
                  {inspected.academic_review_status}
                </span>
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge
                tone={getCapabilityStatusMeta(inspected.capability_status).tone}
              >
                {getCapabilityStatusMeta(inspected.capability_status).label}
              </StatusBadge>
              <StatusBadge
                tone={getTestingStatusMeta(inspected.testing_status).tone}
              >
                {getTestingStatusMeta(inspected.testing_status).label}
              </StatusBadge>
            </div>
          </div>

          {/* Known Limitations */}
          <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-950">
            <span className="font-semibold">Known Limitations & Scope: </span>
            {inspected.known_limitations ||
              "No limitations documented yet; review before production rollout."}
          </div>

          {/* Provider Matrix */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {["llm", "tts", "stt", "translation"].map((slot) => {
              const info = (inspected.provider_matrix?.[slot] ?? {}) as Record<
                string,
                string
              >;
              return (
                <div
                  key={slot}
                  className="rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-xs"
                >
                  <div className="font-semibold uppercase tracking-wide text-slate-500">
                    {slot}
                  </div>
                  <div className="mt-1 font-medium text-slate-900">
                    {info.provider ||
                      (slot === "tts"
                        ? inspected.voice_provider || "None"
                        : slot === "stt"
                          ? inspected.stt_provider || "None"
                          : slot === "translation"
                            ? inspected.translation_provider || "None"
                            : "Configured LLM")}
                  </div>
                  <div className="mt-0.5 text-slate-600">
                    Status: {info.status || "unverified"} · Quality:{" "}
                    {info.quality || "untested"}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Governance Override Form (Admin / Academic Reviewer only) */}
          {canManage && token && (
            <div className="border-t border-slate-200 pt-4 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                Governance Update (Reviewer / Admin)
              </h4>
              <div className="grid gap-3 md:grid-cols-3">
                <label className="block text-xs text-slate-700">
                  Capability Status
                  <select
                    value={editCapabilityStatus}
                    onChange={(e) => setEditCapabilityStatus(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                  >
                    <option value="production">Production</option>
                    <option value="beta">Beta</option>
                    <option value="experimental">Experimental</option>
                    <option value="planned">Planned</option>
                  </select>
                </label>
                <label className="block text-xs text-slate-700">
                  Testing Status
                  <select
                    value={editTestingStatus}
                    onChange={(e) => setEditTestingStatus(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                  >
                    <option value="passed">Passed</option>
                    <option value="partial">Partial</option>
                    <option value="pending">Pending</option>
                    <option value="failed">Failed</option>
                  </select>
                </label>
                <div className="flex items-end">
                  <button
                    type="button"
                    disabled={savingCode === inspected.language_code}
                    onClick={() => void handleGovernanceSave()}
                    className="whitespace-nowrap shrink-0 rounded-md bg-slate-900 px-3.5 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    {savingCode ? "Updating..." : "Save Capability Audit"}
                  </button>
                </div>
              </div>
              <label className="block text-xs text-slate-700">
                Documented Known Limitations
                <textarea
                  rows={2}
                  value={editLimitations}
                  onChange={(e) => setEditLimitations(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
                />
              </label>
              {feedback && (
                <p className="text-xs text-emerald-700">{feedback}</p>
              )}
              {error && <p className="text-xs text-rose-700">{error}</p>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
