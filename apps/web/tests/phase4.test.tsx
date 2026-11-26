import {
  type WhiteboardAction,
  isValidWhiteboardAction,
  reduceWhiteboardActions,
} from "@go4guru/whiteboard-schema";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ClassroomPage from "@/app/classroom/page";
import { WhiteboardCanvas } from "@/components/whiteboard-canvas";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    token: "test-jwt-token",
    user: {
      id: "u1",
      email: "student@example.com",
      display_name: "Test Student",
      roles: ["student"],
      permissions: ["classroom:create", "classroom:attend", "whiteboard:write", "voice:tts"],
      is_minor: true,
      mfa_enabled: false,
      mfa_verified: false,
      status: "active",
    },
    initializing: false,
    mfaRequired: false,
    clearSession: vi.fn(),
  }),
}));

describe("Phase 4 Whiteboard Schema, Canvas & Live Classroom UI", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("blocks unsafe script payloads and reduces whiteboard opcodes deterministically", () => {
    expect(
      isValidWhiteboardAction({
        id: "xss1",
        opcode: "WRITE_TEXT",
        sequence: 1,
        at_ms: 0,
        aria_summary: "Bad payload",
        payload: { text: "<script>alert(1)</script>" },
      })
    ).toBe(false);

    const actions: WhiteboardAction[] = [
      {
        id: "shape-a",
        opcode: "DRAW_SHAPE",
        sequence: 1,
        at_ms: 0,
        aria_summary: "Primary box",
        payload: { shape: "rect", x: 20, y: 20, w: 120, h: 60 },
      },
      {
        id: "move-a",
        opcode: "MOVE",
        sequence: 2,
        at_ms: 100,
        aria_summary: "Move box",
        payload: { target_id: "shape-a", dx: 40, dy: 15 },
      },
      {
        id: "hl-a",
        opcode: "HIGHLIGHT",
        sequence: 3,
        at_ms: 200,
        aria_summary: "Highlight box",
        payload: { target_id: "shape-a", color: "#f59e0b" },
      },
    ];
    const reduced = reduceWhiteboardActions(actions);
    expect(reduced).toHaveLength(1);
    expect(reduced[0].dx).toBe(40);
    expect(reduced[0].dy).toBe(15);
    expect(reduced[0].highlighted).toBe(true);
  });

  it("renders SVG + KaTeX opcodes and accessible aria_summary list on WhiteboardCanvas", () => {
    render(
      <WhiteboardCanvas
        canUndo={true}
        canRedo={false}
        actions={[
          {
            id: "s1_text",
            opcode: "WRITE_TEXT",
            sequence: 1,
            at_ms: 0,
            aria_summary: "Heading for Parabola Lesson",
            payload: { x: 40, y: 40, text: "Parabola Symmetry" },
          },
          {
            id: "s2_formula",
            opcode: "INSERT_FORMULA",
            sequence: 2,
            at_ms: 0,
            aria_summary: "Formula y equals 0.5 x squared",
            payload: { x: 40, y: 120, latex: "y = 0.5x^2" },
          },
        ]}
      />
    );
    expect(screen.getByText("Parabola Symmetry")).toBeInTheDocument();
    expect(screen.getByText(/Heading for Parabola Lesson/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Redo" })).toBeDisabled();
  });

  it("displays Language Capability honesty tiers, timed_subtitles_only fallback, and live lesson controls", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              language_code: "en",
              display_name: "English",
              native_name: "English",
              rtl: false,
              text_quality_tier: "tier_1_native",
              translation_status: "native",
              tts_supported: true,
              stt_supported: true,
              voice_provider: "elevenlabs",
              pronunciation_tier: "high",
              subtitle_supported: true,
              academic_review_status: "approved",
              known_limitations: "Primary STEM language",
            },
            {
              language_code: "ta",
              display_name: "Tamil",
              native_name: "தமிழ்",
              rtl: false,
              text_quality_tier: "tier_2_beta",
              translation_status: "beta",
              tts_supported: false,
              stt_supported: false,
              voice_provider: null,
              pronunciation_tier: null,
              subtitle_supported: true,
              academic_review_status: "pending",
              known_limitations: "Subtitles only",
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "cls-1",
              lesson_plan_id: "lp-1",
              title: "STEM: Quadratic Kinematics",
              state: "READY",
              current_segment_seq: 1,
              total_segments: 1,
              playback_speed: 1.0,
              voice_language: "en",
              subtitle_language: "en",
              started_at: "2026-11-26T18:00:00Z",
              last_active_at: "2026-11-26T18:00:00Z",
              completed_at: null,
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "cls-1",
            lesson_plan_id: "lp-1",
            state: "READY",
            current_segment_seq: 1,
            playback_position_ms: 0,
            playback_speed: 1.0,
            voice_language: "en",
            subtitle_language: "en",
            checkpoint_results: {},
            lesson_artifact: {
              schema_version: "1.0.0",
              title: "STEM: Quadratic Kinematics",
              curriculum_context: {},
              language: "en",
              voice_language: "en",
              subtitle_language: "en",
              objectives: ["Understand quadratic symmetry"],
              segments: [
                {
                  sequence: 1,
                  type: "concept_explanation",
                  title: "Introduction",
                  narration: "Parabolas are symmetric around x equals zero.",
                  subtitle_cues: [
                    {
                      start_ms: 0,
                      end_ms: 8000,
                      text: "Parabolas are symmetric around x equals zero.",
                    },
                  ],
                  canvas_actions: [
                    {
                      id: "s1_h",
                      opcode: "WRITE_TEXT",
                      sequence: 1,
                      at_ms: 0,
                      aria_summary: "Lesson heading",
                      payload: { x: 40, y: 40, text: "STEM: Quadratic Kinematics" },
                    },
                  ],
                  checkpoint: null,
                  duration_ms: 8000,
                },
              ],
            },
            active_whiteboard_actions: [
              {
                id: "s1_h",
                opcode: "WRITE_TEXT",
                sequence: 1,
                at_ms: 0,
                aria_summary: "Lesson heading",
                payload: { x: 40, y: 40, text: "STEM: Quadratic Kinematics" },
              },
            ],
            can_undo: false,
            can_redo: false,
            tts_preview: {
              audio_available: false,
              audio_url: null,
              cache_key: null,
              normalized_speakable_text: "Parabolas are symmetric around x equals zero.",
              provider: "none_configured",
              voice_id: "test",
              language_code: "en",
              characters_count: 45,
              estimated_duration_ms: 4000,
              cache_hit: false,
              is_fallback: true,
              fallback_mode: "timed_subtitles_only",
              limitation_notice:
                "ELEVENLABS_API_KEY not configured; synchronized timed subtitles active.",
            },
            started_at: "2026-11-26T18:00:00Z",
            last_active_at: "2026-11-26T18:00:00Z",
            completed_at: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<ClassroomPage />);

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "STEM: Quadratic Kinematics" })
      ).toBeInTheDocument()
    );
    expect(screen.getByText(/timed_subtitles_only/i)).toBeInTheDocument();
    expect(screen.getByText(/Tamil .*Subtitles Beta/i)).toBeInTheDocument();
    expect(screen.getByTestId("live-subtitle-banner")).toHaveTextContent(
      "Parabolas are symmetric around x equals zero."
    );
    expect(screen.getByRole("button", { name: "Play Lesson" })).toBeEnabled();
  });
});
