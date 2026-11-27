"use client";

import type {
  ClassroomSessionDetailOut,
  ClassroomSessionSummaryOut,
  LanguageCapabilityOut,
  LessonPlanOut,
  SubjectOut,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import type { WhiteboardAction } from "@go4guru/whiteboard-schema";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MathText } from "@/components/math-text";
import { WhiteboardCanvas } from "@/components/whiteboard-canvas";
import {
  ApiClientError,
  askClassroomDoubt,
  buildClassroomWsUrl,
  controlClassroomSession,
  createClassroomSession,
  fetchLanguageCapabilities,
  fetchSubjects,
  generateClassroomLesson,
  getClassroomSession,
  listClassroomLessons,
  listClassroomSessions,
  postWhiteboardAction,
  redoWhiteboard,
  saveWhiteboardSnapshot,
  submitClassroomCheckpoint,
  undoWhiteboard,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { publicEnv } from "@/lib/env";

const SPEEDS = [0.75, 1.0, 1.25, 1.5, 1.75];

function stateTone(state: string): "healthy" | "degraded" | "neutral" {
  if (state === "PLAYING_SEGMENT" || state === "COMPLETED") return "healthy";
  if (state === "CHECKPOINT_WAIT" || state === "DOUBT_INTERRUPTION") return "degraded";
  return "neutral";
}

export default function ClassroomPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [capabilities, setCapabilities] = useState<LanguageCapabilityOut[]>([]);
  const [subjects, setSubjects] = useState<SubjectOut[]>([]);
  const [lessons, setLessons] = useState<LessonPlanOut[]>([]);
  const [sessions, setSessions] = useState<ClassroomSessionSummaryOut[]>([]);
  const [activeSession, setActiveSession] =
    useState<ClassroomSessionDetailOut | null>(null);

  const [topicTitle, setTopicTitle] = useState("Quadratic Kinematics");
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [voiceLang, setVoiceLang] = useState("en");
  const [subtitleLang, setSubtitleLang] = useState("en");

  const [elapsedMs, setElapsedMs] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);

  const [selectedCkptKey, setSelectedCkptKey] = useState("");
  const [numericAnswer, setNumericAnswer] = useState("");
  const [ckptFeedback, setCkptFeedback] = useState<string | null>(null);

  const [doubtInput, setDoubtInput] = useState("");
  const [doubtAnswer, setDoubtAnswer] = useState<{
    markdown: string;
    verification: string;
    safety: string;
  } | null>(null);

  const [snapshotNotice, setSnapshotNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  const refreshLists = useCallback(async (authToken: string) => {
    const [caps, subjs, lps, sessList] = await Promise.all([
      fetchLanguageCapabilities(),
      fetchSubjects(),
      listClassroomLessons(authToken),
      listClassroomSessions(authToken),
    ]);
    setCapabilities(caps);
    setSubjects(subjs);
    setLessons(lps);
    setSessions(sessList);
    if (sessList.length > 0) {
      const latest = await getClassroomSession(authToken, sessList[0].id);
      setActiveSession(latest);
      setElapsedMs(latest.playback_position_ms);
    }
  }, []);

  useEffect(() => {
    if (!initializing && !token) {
      router.replace("/login");
    }
  }, [initializing, token, router]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    setLoading(true);
    setError(null);
    refreshLists(token)
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Failed to load Live Classroom."
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token, refreshLists]);

  const activeSessionId = activeSession?.id ?? null;

  // WebSocket synchronization connection for active classroom session
  useEffect(() => {
    if (!token || !activeSessionId) {
      setWsConnected(false);
      return;
    }
    let closed = false;
    let socket: WebSocket | null = null;
    try {
      socket = new WebSocket(buildClassroomWsUrl(activeSessionId), ["go4guru.v1"]);
      wsRef.current = socket;
      socket.onopen = () => {
        if (!closed && socket) {
          socket.send(JSON.stringify({ action: "auth", token }));
        }
      };
      socket.onclose = () => {
        if (!closed) setWsConnected(false);
      };
      socket.onerror = () => {
        if (!closed) setWsConnected(false);
      };
      socket.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data)) as {
            type?: string;
            playback_speed?: number;
          };
          if (msg.type === "session.state" && !closed) {
            setWsConnected(true);
          }
          if (msg.type === "session.sync" && token) {
            getClassroomSession(token, activeSessionId)
              .then((detail) => setActiveSession(detail))
              .catch(() => {});
          }
        } catch {
          // Ignore malformed frame
        }
      };
    } catch {
      setWsConnected(false);
    }
    return () => {
      closed = true;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
      wsRef.current = null;
    };
  }, [token, activeSessionId]);

  const currentSegment = useMemo(() => {
    if (!activeSession) return null;
    return (
      activeSession.lesson_artifact.segments.find(
        (s) => s.sequence === activeSession.current_segment_seq
      ) ?? activeSession.lesson_artifact.segments[0] ?? null
    );
  }, [activeSession]);

  const isPlaying = activeSession?.state === "PLAYING_SEGMENT";
  const playbackSpeed = activeSession?.playback_speed ?? 1.0;
  const segmentDurationMs = currentSegment?.duration_ms ?? 12000;

  // Synchronized deterministic clock advancing subtitles & progressive whiteboard cues
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setElapsedMs((prev) =>
        Math.min(segmentDurationMs, prev + Math.round(250 * playbackSpeed))
      );
    }, 250);
    return () => clearInterval(timer);
  }, [isPlaying, playbackSpeed, segmentDurationMs]);

  const activeCue = useMemo(() => {
    if (!currentSegment || currentSegment.subtitle_cues.length === 0) return null;
    return (
      currentSegment.subtitle_cues.find(
        (c) => elapsedMs >= c.start_ms && elapsedMs <= c.end_ms
      ) ?? currentSegment.subtitle_cues[currentSegment.subtitle_cues.length - 1]
    );
  }, [currentSegment, elapsedMs]);

  const mergedBoardActions = useMemo(() => {
    if (!activeSession) return [];
    const base = activeSession.active_whiteboard_actions as WhiteboardAction[];
    // Ensure student actions remain visible regardless of timed cue filter
    return base.map((act) =>
      act.id.startsWith("student_") || act.id.startsWith("doubt_")
        ? { ...act, at_ms: 0 }
        : act
    );
  }, [activeSession]);

  function handleApiError(err: unknown) {
    if (err instanceof ApiClientError) {
      setError(`${err.code}: ${err.message}`);
    } else if (err instanceof Error) {
      setError(err.message);
    } else {
      setError("Classroom request failed.");
    }
  }

  async function handleGenerateAndStart(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !topicTitle.trim()) return;
    setBusy(true);
    setError(null);
    setCkptFeedback(null);
    setDoubtAnswer(null);
    setSnapshotNotice(null);
    try {
      const lp = await generateClassroomLesson(token, {
        topic_title: topicTitle.trim(),
        subject_id: selectedSubjectId || null,
        language_code: "en",
        voice_language: voiceLang,
        subtitle_language: subtitleLang,
      });
      const sess = await createClassroomSession(token, {
        lesson_plan_id: lp.id,
        playback_speed: 1.0,
        voice_language: voiceLang,
        subtitle_language: subtitleLang,
      });
      setLessons((prev) => [lp, ...prev]);
      const summaries = await listClassroomSessions(token);
      setSessions(summaries);
      setActiveSession(sess);
      setElapsedMs(0);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleStartFromLesson(lessonPlanId: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const sess = await createClassroomSession(token, {
        lesson_plan_id: lessonPlanId,
        voice_language: voiceLang,
        subtitle_language: subtitleLang,
      });
      const summaries = await listClassroomSessions(token);
      setSessions(summaries);
      setActiveSession(sess);
      setElapsedMs(0);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectSession(sessionId: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    setCkptFeedback(null);
    try {
      const detail = await getClassroomSession(token, sessionId);
      setActiveSession(detail);
      setElapsedMs(detail.playback_position_ms);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleControl(
    action:
      | "play"
      | "pause"
      | "resume"
      | "repeat"
      | "next"
      | "previous"
      | "seek"
      | "set_speed"
      | "set_language"
      | "complete",
    extra?: {
      playback_position_ms?: number;
      playback_speed?: number;
      voice_language?: string;
      subtitle_language?: string;
    }
  ) {
    if (!token || !activeSession) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await controlClassroomSession(token, activeSession.id, {
        action,
        playback_position_ms: extra?.playback_position_ms ?? elapsedMs,
        playback_speed: extra?.playback_speed,
        voice_language: extra?.voice_language,
        subtitle_language: extra?.subtitle_language,
      });
      setActiveSession(updated);
      if (action === "repeat" || action === "next" || action === "previous") {
        setElapsedMs(0);
        setSelectedCkptKey("");
        setNumericAnswer("");
        setCkptFeedback(null);
      }
      if (action === "play" || action === "resume") {
        setElapsedMs(updated.playback_position_ms);
      }
      const summaries = await listClassroomSessions(token);
      setSessions(summaries);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleCheckpointSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !activeSession || !currentSegment?.checkpoint) return;
    setBusy(true);
    setError(null);
    try {
      const res = await submitClassroomCheckpoint(token, activeSession.id, {
        selected_key:
          currentSegment.checkpoint.question_type === "mcq_single"
            ? selectedCkptKey
            : undefined,
        numeric_value:
          currentSegment.checkpoint.question_type === "numerical"
            ? Number(numericAnswer)
            : undefined,
      });
      setCkptFeedback(res.feedback);
      setActiveSession(res.session);
      if (res.passed) {
        setElapsedMs(0);
        setSelectedCkptKey("");
      }
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleAskDoubt(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !activeSession || !doubtInput.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await askClassroomDoubt(token, activeSession.id, doubtInput.trim());
      setDoubtAnswer({
        markdown: res.answer_markdown,
        verification: res.verification_status,
        safety: res.safety_verdict,
      });
      setActiveSession(res.session);
      setDoubtInput("");
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleStudentDraw(action: WhiteboardAction) {
    if (!token || !activeSession) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await postWhiteboardAction(token, activeSession.id, action);
      setActiveSession(updated);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleUndo() {
    if (!token || !activeSession) return;
    setBusy(true);
    setError(null);
    try {
      setActiveSession(await undoWhiteboard(token, activeSession.id));
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRedo() {
    if (!token || !activeSession) return;
    setBusy(true);
    setError(null);
    try {
      setActiveSession(await redoWhiteboard(token, activeSession.id));
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveSnapshot() {
    if (!token || !activeSession) return;
    setBusy(true);
    setError(null);
    try {
      const snap = await saveWhiteboardSnapshot(token, activeSession.id);
      setSnapshotNotice(`Saved snapshot v${snap.version} (${snap.actions.length} objects).`);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  if (initializing || loading) {
    return <LoadingCard message="Loading Interactive Live Classroom..." />;
  }

  const audioFullUrl =
    activeSession?.tts_preview?.audio_available && activeSession.tts_preview.audio_url
      ? `${publicEnv.apiBaseUrl.replace(/\/+$/, "")}${activeSession.tts_preview.audio_url}`
      : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Interactive Live AI Classroom &amp; Whiteboard
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Structured LessonArtifacts synchronized across server FSM, timed voice/subtitles, and deterministic SVG+KaTeX canvas.
          </p>
        </div>
        {activeSession && (
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={stateTone(activeSession.state)}>
              {activeSession.state}
            </StatusBadge>
            <StatusBadge tone={wsConnected ? "healthy" : "neutral"}>
              {wsConnected ? "WS Synchronized" : "HTTP Sync Active"}
            </StatusBadge>
          </div>
        )}
      </div>

      {error && <ErrorBanner title="Live Classroom Notice" message={error} />}
      {snapshotNotice && (
        <div
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-900"
        >
          {snapshotNotice}
        </div>
      )}

      {/* Lesson Generator & Language Capability Selector */}
      <form
        onSubmit={handleGenerateAndStart}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-5"
      >
        <div className="md:col-span-2">
          <label
            htmlFor="topic-title-input"
            className="block text-xs font-semibold uppercase tracking-wide text-slate-600"
          >
            Lesson Topic
          </label>
          <input
            id="topic-title-input"
            type="text"
            required
            value={topicTitle}
            onChange={(e) => setTopicTitle(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="e.g., Quadratic Kinematics, Ohm Law"
          />
        </div>
        <div>
          <label
            htmlFor="subject-select"
            className="block text-xs font-semibold uppercase tracking-wide text-slate-600"
          >
            Subject (Optional)
          </label>
          <select
            id="subject-select"
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">General STEM</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor="voice-lang-select"
            className="block text-xs font-semibold uppercase tracking-wide text-slate-600"
          >
            Voice / Subtitle Language
          </label>
          <select
            id="voice-lang-select"
            value={voiceLang}
            onChange={(e) => {
              setVoiceLang(e.target.value);
              setSubtitleLang(e.target.value);
            }}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {capabilities.map((cap) => (
              <option key={cap.language_code} value={cap.language_code}>
                {cap.display_name} ({cap.native_name}) —{" "}
                {cap.tts_supported ? "Voice + Subtitles" : "Subtitles Beta"}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Preparing..." : "Generate & Start Lesson"}
          </button>
        </div>
      </form>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Main Live Stage: Controls + Whiteboard + Subtitles + Checkpoints + Doubts */}
        <div className="space-y-4 lg:col-span-8">
          {!activeSession ? (
            <EmptyState
              title="No active Live Classroom session yet"
              description="Generate a structured lesson above to start synchronized narration, subtitles, and interactive whiteboard diagrams."
            />
          ) : (
            <>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">
                      {activeSession.lesson_artifact.title}
                    </h2>
                    <p className="text-xs text-slate-600">
                      Segment {activeSession.current_segment_seq} of{" "}
                      {activeSession.lesson_artifact.segments.length}:{" "}
                      <span className="font-semibold text-slate-800">
                        {currentSegment?.title}
                      </span>
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <label htmlFor="speed-select" className="text-xs text-slate-600">
                      Speed
                    </label>
                    <select
                      id="speed-select"
                      value={activeSession.playback_speed}
                      onChange={(e) =>
                        handleControl("set_speed", {
                          playback_speed: Number(e.target.value),
                        })
                      }
                      className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                    >
                      {SPEEDS.map((sp) => (
                        <option key={sp} value={sp}>
                          {sp}x
                        </option>
                      ))}
                    </select>
                    <label htmlFor="sub-lang-select" className="text-xs text-slate-600">
                      Captions
                    </label>
                    <select
                      id="sub-lang-select"
                      value={activeSession.subtitle_language}
                      onChange={(e) =>
                        handleControl("set_language", {
                          subtitle_language: e.target.value,
                        })
                      }
                      className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                    >
                      {capabilities.map((c) => (
                        <option key={c.language_code} value={c.language_code}>
                          {c.display_name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Transport Bar */}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {activeSession.state !== "PLAYING_SEGMENT" ? (
                    <button
                      type="button"
                      disabled={busy || activeSession.state === "CHECKPOINT_WAIT"}
                      onClick={() =>
                        handleControl(
                          activeSession.state === "READY" ? "play" : "resume"
                        )
                      }
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-40"
                    >
                      {activeSession.state === "READY" ? "Play Lesson" : "Resume"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleControl("pause")}
                      className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-40"
                    >
                      Pause
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => handleControl("repeat")}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                  >
                    Repeat Segment
                  </button>
                  <button
                    type="button"
                    disabled={busy || activeSession.current_segment_seq <= 1}
                    onClick={() => handleControl("previous")}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => handleControl("next")}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                  >
                    Next Segment
                  </button>
                  <button
                    type="button"
                    disabled={busy || activeSession.state === "COMPLETED"}
                    onClick={() => handleControl("complete")}
                    className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-800 hover:bg-indigo-100 disabled:opacity-40"
                  >
                    Complete Lesson
                  </button>
                </div>

                {/* Honest Audio Player OR Timed-Subtitle Fallback Banner */}
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                  {audioFullUrl ? (
                    <audio controls src={audioFullUrl} className="w-full" />
                  ) : (
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-700">
                      <span>
                        <strong>Voice Mode:</strong>{" "}
                        {activeSession.tts_preview?.fallback_mode ??
                          "timed_subtitles_only"}{" "}
                        —{" "}
                        {activeSession.tts_preview?.limitation_notice ??
                          "ElevenLabs audio is unconfigured; synchronized timed subtitles active."}
                      </span>
                      <span className="font-mono text-slate-500">
                        {(elapsedMs / 1000).toFixed(1)}s /{" "}
                        {(segmentDurationMs / 1000).toFixed(1)}s
                      </span>
                    </div>
                  )}
                </div>

                {/* Live Synchronized Subtitle Caption Bar */}
                {activeCue && (
                  <div
                    data-testid="live-subtitle-banner"
                    className="mt-3 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white"
                  >
                    <MathText text={activeCue.text} />
                  </div>
                )}
              </div>

              {/* Schema-Driven Deterministic Interactive Whiteboard */}
              <WhiteboardCanvas
                actions={mergedBoardActions}
                canUndo={activeSession.can_undo}
                canRedo={activeSession.can_redo}
                busy={busy}
                onStudentAction={handleStudentDraw}
                onUndo={handleUndo}
                onRedo={handleRedo}
                onSaveSnapshot={handleSaveSnapshot}
              />

              {/* Interactive Checkpoint Card */}
              {currentSegment?.checkpoint && (
                <form
                  onSubmit={handleCheckpointSubmit}
                  className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-4"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-amber-950">
                      Understanding Checkpoint
                    </h3>
                    <StatusBadge tone="degraded">Checkpoint</StatusBadge>
                  </div>
                  <div className="text-sm text-slate-900">
                    <MathText text={currentSegment.checkpoint.prompt} />
                  </div>
                  {currentSegment.checkpoint.question_type === "mcq_single" ? (
                    <div className="space-y-2">
                      {currentSegment.checkpoint.options.map((opt) => (
                        <label
                          key={opt.key}
                          className="flex cursor-pointer items-center gap-2 rounded-md border border-amber-200 bg-white px-3 py-2 text-sm"
                        >
                          <input
                            type="radio"
                            name="checkpoint-opt"
                            value={opt.key}
                            checked={selectedCkptKey === opt.key}
                            onChange={(e) => setSelectedCkptKey(e.target.value)}
                          />
                          <span className="font-semibold">{opt.key}.</span>
                          <MathText text={opt.text} />
                        </label>
                      ))}
                    </div>
                  ) : (
                    <input
                      type="number"
                      step="any"
                      value={numericAnswer}
                      onChange={(e) => setNumericAnswer(e.target.value)}
                      className="w-48 rounded-md border border-amber-300 bg-white px-3 py-1.5 text-sm"
                      placeholder="Enter numeric value"
                    />
                  )}
                  <div className="flex items-center gap-3">
                    <button
                      type="submit"
                      disabled={busy}
                      className="rounded-md bg-amber-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-800 disabled:opacity-40"
                    >
                      Submit Checkpoint Answer
                    </button>
                    {ckptFeedback && (
                      <span className="text-xs font-medium text-amber-950">
                        {ckptFeedback}
                      </span>
                    )}
                  </div>
                </form>
              )}

              {/* Student Doubt Interruption Drawer */}
              <form
                onSubmit={handleAskDoubt}
                className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <h3 className="text-sm font-bold text-slate-900">
                  Raise Hand / Ask a Live Doubt
                </h3>
                <div className="flex flex-wrap gap-2">
                  <input
                    type="text"
                    value={doubtInput}
                    onChange={(e) => setDoubtInput(e.target.value)}
                    placeholder="Pause & ask a question about this diagram or equation..."
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={busy || !doubtInput.trim()}
                    className="rounded-md bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Ask Doubt
                  </button>
                </div>
                {doubtAnswer && (
                  <div className="space-y-2 rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-sm text-slate-900">
                    <div className="flex items-center gap-2 text-xs font-semibold text-indigo-900">
                      <span>AI Classroom Clarification</span>
                      <StatusBadge tone="neutral">
                        {doubtAnswer.verification}
                      </StatusBadge>
                    </div>
                    <MathText text={doubtAnswer.markdown} />
                  </div>
                )}
              </form>
            </>
          )}
        </div>

        {/* Right Sidebar: Lesson Objectives, Full Transcript & Session History */}
        <aside className="space-y-4 lg:col-span-4">
          {activeSession && (
            <>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="text-sm font-bold text-slate-900">
                  Lesson Objectives
                </h3>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-700">
                  {activeSession.lesson_artifact.objectives.map((obj, idx) => (
                    <li key={idx}>{obj}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="text-sm font-bold text-slate-900">
                  Narration Transcript
                </h3>
                <div className="mt-2 space-y-2">
                  {activeSession.lesson_artifact.segments.map((seg) => (
                    <div
                      key={seg.sequence}
                      className={`rounded-md border p-2 text-xs ${
                        seg.sequence === activeSession.current_segment_seq
                          ? "border-indigo-300 bg-indigo-50"
                          : "border-slate-100 bg-slate-50"
                      }`}
                    >
                      <div className="font-semibold text-slate-900">
                        {seg.sequence}. {seg.title}
                      </div>
                      <div className="mt-1 text-slate-700">
                        <MathText text={seg.narration} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900">
              Classroom Session History
            </h3>
            {sessions.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">
                No past sessions recorded yet.
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {sessions.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      onClick={() => handleSelectSession(s.id)}
                      className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-xs ${
                        activeSession?.id === s.id
                          ? "border-indigo-400 bg-indigo-50"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      <div>
                        <div className="font-semibold text-slate-900">{s.title}</div>
                        <div className="text-slate-500">
                          Seg {s.current_segment_seq}/{s.total_segments} ·{" "}
                          {s.playback_speed}x
                        </div>
                      </div>
                      <StatusBadge tone={stateTone(s.state)}>
                        {s.state}
                      </StatusBadge>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {lessons.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-bold text-slate-900">
                Saved Lesson Plans
              </h3>
              <ul className="mt-2 space-y-1.5">
                {lessons.slice(0, 5).map((lp) => (
                  <li
                    key={lp.id}
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <span className="truncate text-slate-700">{lp.title}</span>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleStartFromLesson(lp.id)}
                      className="shrink-0 rounded border border-indigo-200 px-2 py-0.5 font-medium text-indigo-700 hover:bg-indigo-50"
                    >
                      Launch
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
