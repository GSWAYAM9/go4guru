# Voice & Multilingual Architecture (`docs/VOICE_MULTILINGUAL_ARCHITECTURE.md`)

**Design Mandate (Sections 21–22):** Use **ElevenLabs** as the initial voice provider behind a clean `VoiceProviderInterface` abstraction, and manage languages via an honest, empirical **Language Capability Registry** that never advertises unsupported voice or academic capabilities.

---

## 1. Pluggable Voice Provider Interface

```python
class VoiceProviderInterface(Protocol):
    async def synthesize_speech(self, req: TTSRequest) -> TTSResult: ...
    async def stream_speech(self, req: TTSRequest) -> AsyncIterator[AudioChunk]: ...
    async def transcribe_audio(self, req: STTRequest) -> STTResult: ...
    async def list_voices(self, language_code: str) -> list[VoiceProfile]: ...
    async def get_capabilities(self) -> ProviderCapabilities: ...
```

### Provider Adapter Stack
- **Primary Adapter (Phase 4):** `ElevenLabsVoiceAdapter` (streaming TTS, voice selection, multilingual v2/flash models, character-level alignment/timing cues where supported for subtitle sync).
- **Fallback / Future Adapters:** Google Cloud TTS/STT, Azure Neural Speech, Sarvam AI / Bhashini / Indic-specialized adapters for regional Indian languages (Phase 11), plus local open-source STT (`Vosk`/`Whisper`) where evaluated.
- **Operational Controls:**
  - **Text Chunking:** Splits lesson segments into sentence/clause chunks (< 400 chars) while converting math notation into speakable text (e.g., `x^2 + 3x = 0` → *"x squared plus 3 x equals zero"* via deterministic math-to-speech normalizer!).
  - **Audio Caching (Rights-Aware):** Cache static narration chunks for published lessons keyed by `SHA256(normalized_text + voice_id + speed + language_code)` in private S3 to drastically slash ElevenLabs repeat cost & latency.
  - **Telemetry & Circuit Breaker:** Every call logs latency, characters, audio duration, and estimated USD cost to `voice_usage_logs`; consecutive provider errors trip circuit breaker into graceful subtitle/text-only classroom mode.

---

## 2. Independent Language Preference Dimensions

Each student profile supports **6 independent language settings**:
1. `ui_language` (navigation chrome, buttons, accessibility labels)
2. `explanation_language` (AI tutor & concept lesson prose, including bilingual modes like Hindi explanation with English STEM terms)
3. `voice_language` (spoken TTS narration & voice input)
4. `subtitle_language` (live captions below whiteboard/audio player)
5. `question_language` (question stems/options where translated & reviewed)
6. `answer_language` (language in which student writes/speaks answers)

---

## 3. Language Capability Registry (`language_capabilities` Table)

The platform **never claims all languages work equally well**. UI selectors dynamically query `/api/v1/languages/capabilities` and visibly indicate exact capability tiers:

| Language (`code`) | Text Gen | Translation Status | TTS Support | STT Support | Pronunciation & Academic Notes (Initial Target Baseline — Verified Per Release) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| English (`en`) | Tier 1 (Native) | Native | Supported (ElevenLabs) | Supported | Full STEM terminology, math-to-speech, reviewed |
| Hindi (`hi`) | Tier 1 | High (Glossary-guided) | Supported (ElevenLabs) | Supported | Bilingual Hindi+English STEM mode recommended (`Devanagari` + English technical terms) |
| Bengali (`bn`), Tamil (`ta`), Telugu (`te`), Marathi (`mr`), Gujarati (`gu`), Kannada (`kn`), Malayalam (`ml`), Punjabi (`pa`), Odia (`or`), Urdu (`ur`), Assamese (`as`), Sanskrit (`sa`) | Tier 2 / Beta (Phased) | Phased human review | **Disabled until verified per provider** | **Disabled until verified** | Registry marks `tts_supported=false` / `academic_review_status='pending'` until native-speaker & ElevenLabs/Indic provider benchmarks pass! |

**Important Invariants:**
- If `tts_supported = false` for a user's selected `explanation_language`, the UI offers clear text + bilingual subtitle mode or English voice narration rather than broken robotic mispronunciation.
- Scientific symbols, SI units (`N`, `m/s^2`, `mol`), chemical equations (`H2SO4`), and LaTeX math remain universally rendered via KaTeX regardless of UI script, with RTL layout support prepared for Urdu (`ur`).
