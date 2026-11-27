"use client";

import type { LanguageCapabilityOut } from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import { useLanguage } from "@/lib/language-context";

export type LanguageStudioTab =
  | "preferences"
  | "registry"
  | "bilingual"
  | "glossary"
  | "review";

interface LanguageHubHeaderProps {
  activeTab: LanguageStudioTab;
  onSelectTab: (tab: LanguageStudioTab) => void;
  capabilities: LanguageCapabilityOut[];
  registrySource: "api" | "fallback";
  voiceConfigured: boolean | null;
}

const TABS: Array<{ id: LanguageStudioTab; label: string }> = [
  { id: "preferences", label: "Preferences (6 Modalities)" },
  { id: "registry", label: "Capability Registry" },
  { id: "bilingual", label: "Bilingual & Voice Lab" },
  { id: "glossary", label: "STEM Terminology" },
  { id: "review", label: "Translation Review & QA" },
];

export function LanguageHubHeader({
  activeTab,
  onSelectTab,
  capabilities,
  registrySource,
  voiceConfigured,
}: LanguageHubHeaderProps) {
  const { preferences, isRtl, uiCoveragePct, t } = useLanguage();

  const productionCount = capabilities.filter(
    (c) => c.capability_status === "production"
  ).length;
  const betaCount = capabilities.filter(
    (c) => c.capability_status === "beta"
  ).length;
  const experimentalCount = capabilities.filter(
    (c) => c.capability_status === "experimental" || c.capability_status === "planned"
  ).length;
  const activeCap = capabilities.find(
    (c) => c.language_code === preferences.ui_language
  );

  return (
    <header className="space-y-5 border-b border-slate-200 pb-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Phase 10 · Multilingual Learning Expansion
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            {t("languages.title", "Multilingual Learning & Language Capability Hub")}
          </h1>
          <p className="text-sm leading-relaxed text-slate-600">
            {t(
              "languages.subtitle",
              "Configure independent languages for UI, explanations, voice, subtitles, questions, and answers with transparent provider capability tracking."
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-600">
          <StatusBadge tone={registrySource === "api" ? "healthy" : "neutral"}>
            {registrySource === "api" ? "Live Registry API" : "Baseline Registry"}
          </StatusBadge>
          <StatusBadge tone={voiceConfigured ? "healthy" : "degraded"}>
            {voiceConfigured ? "ElevenLabs Connected" : "Voice Key Not Set (Captions Fallback)"}
          </StatusBadge>
        </div>
      </div>

      {/* Quiet typographic empirical summary strip (clean wrapping without orphan dots) */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1.5 text-xs text-slate-600 tabular-nums">
        <span>
          <strong className="font-semibold text-slate-900">
            {capabilities.length}
          </strong>{" "}
          tracked languages ({productionCount} production, {betaCount} beta,{" "}
          {experimentalCount} experimental/planned)
        </span>
        <span>
          Active UI:{" "}
          <strong className="font-semibold text-slate-900">
            {activeCap
              ? `${activeCap.display_name} (${activeCap.native_name})`
              : preferences.ui_language}
          </strong>{" "}
          ({uiCoveragePct}% keys translated, {isRtl ? "RTL" : "LTR"})
        </span>
        <span className="text-slate-500">
          Unsupported modalities fall back transparently
        </span>
      </div>

      <nav
        aria-label="Multilingual studio sections"
        className="flex flex-wrap gap-2 pt-1"
        role="tablist"
      >
        {TABS.map((tab) => {
          const selected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => onSelectTab(tab.id)}
              className={`whitespace-nowrap shrink-0 rounded-md px-3.5 py-2 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
                selected
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
