---
trigger: model_decision
description: Rules for the interactive Live AI Classroom, structured LessonArtifact JSON, WebSocket state machine, schema-driven whiteboard, and VoiceProvider ElevenLabs abstraction.
---

# Classroom, Whiteboard & Voice Rules

Reference: [docs/CLASSROOM_ARCHITECTURE.md](../../docs/CLASSROOM_ARCHITECTURE.md), [docs/WHITEBOARD_SPECIFICATION.md](../../docs/WHITEBOARD_SPECIFICATION.md), [docs/VOICE_MULTILINGUAL_ARCHITECTURE.md](../../docs/VOICE_MULTILINGUAL_ARCHITECTURE.md).

1. **Structured Lesson Artifacts:** Live AI classrooms MUST run on schema-validated `LessonArtifact` JSON (`objectives`, ordered `segments[]` with `narration`, `subtitle_cues`, `canvas_actions`, `checkpoint`, `duration_ms`)—never raw unstructured LLM chat streams.
2. **Server-Controlled State Machine:** Maintain classroom state (`IDLE → READY → PLAYING_SEGMENT → PAUSED → CHECKPOINT_WAIT → DOUBT_INTERRUPTION → COMPLETED`), segment index, speed, and language on the server over `WS /ws/v1/classroom/{session_id}` so browser reloads and doubt interruptions resume seamlessly.
3. **Schema-Driven Whiteboard Security:** Emit only validated `WhiteboardAction` opcodes (`WRITE_TEXT`, `INSERT_FORMULA`, `DRAW_LINE`, `DRAW_ARROW`, `DRAW_SHAPE`, `DRAW_GRAPH`, `DRAW_DIAGRAM`, `INSERT_IMAGE`, `HIGHLIGHT`, `ERASE`, `MOVE`, `TRANSFORM`). Never execute AI-generated JS/HTML/SVG `<script>`; restrict `INSERT_IMAGE` to vetted `asset_id`s; attach `aria_summary` for screen readers.
4. **Snapshot + Event Replay:** Persist append-only `whiteboard_events` and segment-boundary `whiteboard_snapshots` so lessons replay deterministically. Keep the action schema engine-agnostic until `Excalidraw` (MIT) vs `tldraw` (commercial license) is resolved in `DECISION_LOG.md`.
5. **Voice Provider Abstraction:** Route all TTS/STT through `VoiceProviderInterface` (with **ElevenLabs** as initial adapter). Pre-normalize math notation to speakable text, cache static lesson audio by hash in private S3, meter latency/characters/cost in `voice_usage_logs`, and degrade cleanly to timed subtitles/text on outage or quota limits.
