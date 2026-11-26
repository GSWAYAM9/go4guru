# Phase 4 Implementation Plan & Acceptance Checklist — AI Live Classroom & Synchronized Whiteboard

> **Status:** COMPLETED & VERIFIED (`Phase 4`)  
> **Scope:** Implements `F-022` (Interactive Live AI Classroom & Server State Machine), `F-023` (Schema-Driven Whiteboard), `F-024` (Voice Provider Abstraction & ElevenLabs Adapter), `language_capabilities` registry foundation (`F-025`), and completes `voice_usage_logs` telemetry (`F-037`).  
> **Gate Rule:** All `AC-4.01`–`AC-4.07` checks verified passing after final edit. Ready for Phase 5 (`docs/PHASE_5_IMPLEMENTATION_PLAN.md`).

---

## 1. Work Breakdown & Dependencies

| Stream | Deliverables | Dependencies |
|---|---|---|
| **4A. Migration (`0005_phase4_classroom_whiteboard_voice.py`)** | `language_capabilities`, `whiteboard_assets`, `lesson_plans`, `classroom_sessions`, `classroom_events`, `whiteboard_snapshots`, `whiteboard_events`, `voice_usage_logs`, Phase 4 RBAC seeds & language registry seeds | `0004_phase3_ai_tutor_rag` |
| **4B. Whiteboard Evaluation & Shared Schema (`ADR-010`)** | Evaluate `tldraw` vs `Excalidraw` vs deterministic SVG+KaTeX engine in `DECISION_LOG.md`; expand `@go4guru/whiteboard-schema` with 12-opcode strict validators + deterministic reducer | 4A |
| **4C. Voice Provider Abstraction & ElevenLabs** | `classroom/voice/` (`VoiceProviderInterface`, math-to-speech normalizer + chunker, `ElevenLabsVoiceAdapter`, SHA-256 cached storage, `voice_usage_logs` metering, graceful timed-subtitle fallback when key absent or degraded) | 4A |
| **4D. Lesson Planner, Server FSM, Whiteboard Persistence & WS** | `LessonArtifact` Pydantic schema & planner (objectives, segments, synchronized `at_ms` narration/subtitle cues/canvas actions, checkpoints), authoritative classroom FSM (`IDLE->READY->PLAYING_SEGMENT->PAUSED->CHECKPOINT_WAIT->DOUBT_INTERRUPTION->COMPLETED`), `repeat`/`skip`/`speed`/`language`/`doubt`/`complete`, `whiteboard_events` undo/redo + `whiteboard_snapshots`, REST `/api/v1/{classroom,whiteboard,voice,languages}/*` & `WS /ws/v1/classroom/{session_id}` | 4A, 4B, 4C |
| **4E. Live Classroom Web UI & Whiteboard Canvas** | `/classroom` (Lesson Generator + Session History + Interactive Synchronized Whiteboard Canvas rendering all 12 opcodes safely + KaTeX formulas + graphs/diagrams + student annotation/undo/redo/save/restore/PNG export + Pause/Resume/Repeat/Skip/Speed/Language controls + Synchronized Subtitles & Transcript + Checkpoints & Doubt Interruption) | 4B, 4D |
| **4F. Phase 4 Verification Gate** | Unit tests (FSM transitions, math-to-speech normalizer, whiteboard XSS/script block & undo/redo replay, ElevenLabs `httpx.MockTransport` & fallback), PG18 integration tests (persistence, reload/reconnect recovery, undo/redo snapshots, pause/resume/doubt/checkpoint, WebSocket state broadcast), Vitest component tests, Playwright Chromium E2E | All above |

---

## 2. Phase 4 Acceptance Checklist

- [x] **AC-4.01 Whiteboard Evaluation Recorded (`ADR-010`):** Evaluated `tldraw` (commercial watermark license) vs `Excalidraw` (MIT) and documented deterministic schema-driven SVG+KaTeX architecture.
- [x] **AC-4.02 Structured Lesson Artifacts:** Lessons generate & persist schema-validated `objectives`, ordered `segments[]` with `narration`, `subtitle_cues[]`, timed `canvas_actions[]` (`at_ms`), `checkpoint`, and `duration_ms`.
- [x] **AC-4.03 Server-Controlled FSM & Transitions:** Server enforces `IDLE -> READY -> PLAYING_SEGMENT -> PAUSED -> CHECKPOINT_WAIT -> DOUBT_INTERRUPTION -> COMPLETED` over REST + `WS /ws/v1/classroom/{session_id}`, persisting `classroom_events` for replay/reconnect.
- [x] **AC-4.04 Synchronized Playback Controls:** Supports `play`, `pause`, `resume`, `repeat`, `next`/`skip`, `previous`, `seek`, `speed` (`0.75x..1.75x`), `language`, checkpoint answering/remediation, doubt interruption & resume, and completion.
- [x] **AC-4.05 Safe Schema-Driven Whiteboard & Undo/Redo:** Validates all 12 opcodes (`WRITE_TEXT`, `INSERT_FORMULA`, `DRAW_LINE`, `DRAW_ARROW`, `DRAW_SHAPE`, `DRAW_GRAPH`, `DRAW_DIAGRAM`, `INSERT_IMAGE`, `HIGHLIGHT`, `ERASE`, `MOVE`, `TRANSFORM`); blocks `<script>` / `javascript:` / unvetted image URLs; persists `whiteboard_events` & `whiteboard_snapshots` supporting student drawing, undo/redo, save/restore, and accessible `aria_summary`.
- [x] **AC-4.06 Voice Provider & Language Capability Registry:** Abstracts TTS via `VoiceProviderInterface` + `ElevenLabsVoiceAdapter` with math-to-speech normalization, SHA-256 audio caching, `voice_usage_logs` metering, truthful `/api/v1/languages/capabilities`, and honest timed-subtitle fallback without fake audio.
- [x] **AC-4.07 Full Test & E2E Gate:** Unit (5/5 `test_phase4_whiteboard_voice.py`), PG18 integration + WebSocket (2/2 `test_phase4_classroom_pg.py`), Vitest (3/3 `phase4.test.tsx`), `next build` (17 routes), and Playwright Chromium E2E (4/4 incl. `phase4.spec.ts`) pass.
