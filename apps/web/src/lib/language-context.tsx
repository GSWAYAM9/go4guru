"use client";

import type {
  BilingualMode,
  LanguageCapabilityOut,
  LanguageModalityKey,
  ModalityResolutionOut,
  UserLanguagePreferencesOut,
} from "@go4guru/contracts";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  fetchLanguageCapabilities,
  fetchLanguagePreferences,
  fetchUiLocalizationBundle,
  updateLanguagePreferences,
} from "./api-client";
import { useAuth } from "./auth-context";
import {
  FALLBACK_LANGUAGE_REGISTRY,
  computeUiLocalizationCoverage,
  resolveModalityFallbackClient,
  translateUiKey,
} from "./multilingual-helpers";

const STORAGE_KEY = "go4guru_language_preferences_v1";

export interface LanguagePreferencesState {
  ui_language: string;
  preferred_explanation_language: string;
  preferred_voice_language: string;
  preferred_subtitle_language: string;
  preferred_question_language: string;
  preferred_answer_language: string;
  bilingual_explanation_mode: BilingualMode;
}

const DEFAULT_PREFERENCES: LanguagePreferencesState = {
  ui_language: "en",
  preferred_explanation_language: "en",
  preferred_voice_language: "en",
  preferred_subtitle_language: "en",
  preferred_question_language: "en",
  preferred_answer_language: "en",
  bilingual_explanation_mode: "bilingual_stem_en",
};

interface LanguageContextValue {
  capabilities: LanguageCapabilityOut[];
  registrySource: "api" | "fallback";
  loadingRegistry: boolean;
  preferences: LanguagePreferencesState;
  resolutions: Record<LanguageModalityKey, ModalityResolutionOut>;
  savingPreferences: boolean;
  isRtl: boolean;
  uiCoveragePct: number;
  t: (key: string, fallbackText?: string) => string;
  refreshCapabilities: () => Promise<void>;
  savePreferences: (
    patch: Partial<LanguagePreferencesState>
  ) => Promise<{ persistedToServer: boolean; error?: string }>;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

function computeAllResolutions(
  prefs: LanguagePreferencesState,
  registry: LanguageCapabilityOut[]
): Record<LanguageModalityKey, ModalityResolutionOut> {
  return {
    ui: resolveModalityFallbackClient(prefs.ui_language, "ui", registry),
    explanation: resolveModalityFallbackClient(
      prefs.preferred_explanation_language,
      "explanation",
      registry
    ),
    voice: resolveModalityFallbackClient(
      prefs.preferred_voice_language,
      "voice",
      registry
    ),
    subtitle: resolveModalityFallbackClient(
      prefs.preferred_subtitle_language,
      "subtitle",
      registry
    ),
    question: resolveModalityFallbackClient(
      prefs.preferred_question_language,
      "question",
      registry
    ),
    answer: resolveModalityFallbackClient(
      prefs.preferred_answer_language,
      "answer",
      registry
    ),
  };
}

function normalizeServerPrefs(
  data: UserLanguagePreferencesOut
): LanguagePreferencesState {
  const mode = data.bilingual_explanation_mode;
  const safeMode: BilingualMode =
    mode === "monolingual" || mode === "side_by_side"
      ? mode
      : "bilingual_stem_en";
  return {
    ui_language: data.ui_language || "en",
    preferred_explanation_language: data.preferred_explanation_language || "en",
    preferred_voice_language: data.preferred_voice_language || "en",
    preferred_subtitle_language: data.preferred_subtitle_language || "en",
    preferred_question_language: data.preferred_question_language || "en",
    preferred_answer_language: data.preferred_answer_language || "en",
    bilingual_explanation_mode: safeMode,
  };
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [capabilities, setCapabilities] = useState<LanguageCapabilityOut[]>(
    FALLBACK_LANGUAGE_REGISTRY
  );
  const [registrySource, setRegistrySource] = useState<"api" | "fallback">(
    "fallback"
  );
  const [loadingRegistry, setLoadingRegistry] = useState<boolean>(true);
  const [preferences, setPreferences] =
    useState<LanguagePreferencesState>(DEFAULT_PREFERENCES);
  const [serverResolutions, setServerResolutions] = useState<
    Record<string, ModalityResolutionOut> | null
  >(null);
  const [remoteUiStrings, setRemoteUiStrings] = useState<Record<string, string>>(
    {}
  );
  const [remoteCoveragePct, setRemoteCoveragePct] = useState<number | null>(
    null
  );
  const [savingPreferences, setSavingPreferences] = useState<boolean>(false);

  // Hydrate persisted browser language preferences on mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<LanguagePreferencesState>;
        setPreferences((prev) => ({
          ...prev,
          ...parsed,
        }));
      }
    } catch {
      // Ignore malformed storage entries.
    }
  }, []);

  const refreshCapabilities = useCallback(async () => {
    setLoadingRegistry(true);
    try {
      const rows = await fetchLanguageCapabilities();
      if (Array.isArray(rows) && rows.length > 0) {
        setCapabilities(rows);
        setRegistrySource("api");
      }
    } catch {
      setCapabilities(FALLBACK_LANGUAGE_REGISTRY);
      setRegistrySource("fallback");
    } finally {
      setLoadingRegistry(false);
    }
  }, []);

  useEffect(() => {
    void refreshCapabilities();
  }, [refreshCapabilities]);

  // Sync user preferences from backend when authenticated.
  useEffect(() => {
    if (!token) {
      setServerResolutions(null);
      return;
    }
    let cancelled = false;
    fetchLanguagePreferences(token)
      .then((data) => {
        if (cancelled) return;
        const normalized = normalizeServerPrefs(data);
        setPreferences(normalized);
        setServerResolutions(data.resolutions ?? null);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
        }
      })
      .catch(() => {
        // Keep local preferences gracefully if backend is unreachable.
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  // Fetch backend UI bundle when UI language changes; fall back cleanly to client catalog.
  useEffect(() => {
    let cancelled = false;
    const lang = preferences.ui_language || "en";
    fetchUiLocalizationBundle(lang)
      .then((bundle) => {
        if (cancelled) return;
        setRemoteUiStrings(bundle.strings ?? {});
        setRemoteCoveragePct(bundle.coverage_pct);
      })
      .catch(() => {
        if (cancelled) return;
        setRemoteUiStrings({});
        setRemoteCoveragePct(null);
      });
    return () => {
      cancelled = true;
    };
  }, [preferences.ui_language]);

  const resolutions = useMemo(() => {
    const clientRes = computeAllResolutions(preferences, capabilities);
    if (!serverResolutions) return clientRes;
    const merged = { ...clientRes };
    (Object.keys(clientRes) as LanguageModalityKey[]).forEach((mod) => {
      const srv = serverResolutions[mod];
      if (srv && srv.requested_language === clientRes[mod].requested_language) {
        merged[mod] = srv;
      }
    });
    return merged;
  }, [preferences, capabilities, serverResolutions]);

  const activeUiCap = useMemo(
    () =>
      capabilities.find(
        (c) => c.language_code === resolutions.ui.effective_language
      ) ??
      capabilities.find((c) => c.language_code === preferences.ui_language),
    [capabilities, resolutions.ui.effective_language, preferences.ui_language]
  );

  const isRtl = Boolean(activeUiCap?.rtl);
  const localCoverage = useMemo(
    () => computeUiLocalizationCoverage(preferences.ui_language),
    [preferences.ui_language]
  );
  const uiCoveragePct = remoteCoveragePct ?? localCoverage.coveragePct;

  // Apply <html lang="..." dir="ltr|rtl"> dynamically so RTL Urdu works across the app.
  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.lang = resolutions.ui.effective_language || "en";
    document.documentElement.dir = isRtl ? "rtl" : "ltr";
  }, [resolutions.ui.effective_language, isRtl]);

  const t = useCallback(
    (key: string, fallbackText?: string): string => {
      const resolved = translateUiKey(
        preferences.ui_language,
        key,
        remoteUiStrings
      );
      if (resolved === key && fallbackText) return fallbackText;
      return resolved;
    },
    [preferences.ui_language, remoteUiStrings]
  );

  const savePreferences = useCallback(
    async (
      patch: Partial<LanguagePreferencesState>
    ): Promise<{ persistedToServer: boolean; error?: string }> => {
      const next: LanguagePreferencesState = {
        ...preferences,
        ...patch,
      };
      setPreferences(next);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      }

      if (!token) {
        setServerResolutions(null);
        return { persistedToServer: false };
      }

      setSavingPreferences(true);
      try {
        const updated = await updateLanguagePreferences(token, next);
        const normalized = normalizeServerPrefs(updated);
        setPreferences(normalized);
        setServerResolutions(updated.resolutions ?? null);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
        }
        return { persistedToServer: true };
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Saved locally; server sync unavailable.";
        return { persistedToServer: false, error: msg };
      } finally {
        setSavingPreferences(false);
      }
    },
    [preferences, token]
  );

  const value = useMemo<LanguageContextValue>(
    () => ({
      capabilities,
      registrySource,
      loadingRegistry,
      preferences,
      resolutions,
      savingPreferences,
      isRtl,
      uiCoveragePct,
      t,
      refreshCapabilities,
      savePreferences,
    }),
    [
      capabilities,
      registrySource,
      loadingRegistry,
      preferences,
      resolutions,
      savingPreferences,
      isRtl,
      uiCoveragePct,
      t,
      refreshCapabilities,
      savePreferences,
    ]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return ctx;
}
