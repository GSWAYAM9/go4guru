# Cost Model & Unit Economics (`docs/COST_MODEL.md`)

**Objective (Sections 45–46):** Engineer transparent, measurable unit economics across AI tokens, voice synthesis, storage, search, and compute—and enforce deterministic quotas & caching before scaling.

---

## 1. Tracked Cost Drivers (`provider_rate_cards` & `ai_cost_events`)

| Category | Measured Unit | Logging Point | Cost-Optimization Levers |
| :--- | :--- | :--- | :--- |
| **LLM Inference** | Input tokens, cached input tokens, output tokens, reasoning tokens | `LLMProvider` wrapper | Model routing (light model for intent/routing/simple hints; frontier model for JEE Adv proofs), prompt caching, concise structured outputs |
| **Voice TTS (ElevenLabs)** | Characters synthesized & audio seconds generated | `VoiceProviderInterface` | S3/CDN audio caching for static lesson segments (hit rate target > 70% on core curriculum), math-to-speech pre-normalization, text-only fallback on lower tiers |
| **Speech-to-Text (STT)** | Audio seconds transcribed | `VoiceProviderInterface` | Client VAD silence trimming, audio duration caps per turn |
| **OCR / Vision (Homework)** | Pages / image pixels processed | Homework worker | Client-side compression (< 1.5 MB), lightweight text-PDF extraction before Vision OCR |
| **Embeddings & RAG** | Tokens embedded | Ingestion + query | Embed only published approved chunks; cache frequent query embeddings in Redis |
| **Storage & Bandwidth** | GB stored (S3) + GB egress | S3 lifecycle & metrics | Dedup audio/assets by SHA-256; TTL purge on expired staging/temp files; CDN edge caching |
| **Compute & DB** | API/Worker CPU, PostgreSQL IOPS, Redis RAM, WS connections | Cloud metrics + Prometheus | Snapshot-based analytics (avoid live full-table scans), connection pooling (`asyncpg` / PgBouncer) |

---

## 2. Unit Economics Rollup Metrics (`cost_rollups`)

Automated daily aggregation computes:
1. **Cost per AI Tutor Session** = `(sum LLM costs + embedding + moderation) / sessions`
2. **Cost per Voice Minute** = `(ElevenLabs TTS/STT spend + audio egress) / total_audio_minutes`
3. **Cost per Live Classroom Lesson** = `(lesson gen LLM + TTS uncached synth + WS/storage overhead) / lessons_completed`
4. **Cost per Active Student (Monthly)** = `(AI + Voice + Homework + Infra share) / MAU`
5. **Gross Margin by Plan Tier** = `(Plan Revenue - Student COGS - Payment Gateway Fees) / Plan Revenue`

---

## 3. Configurable Quotas, Entitlements & Circuit Breakers

- **Zero Hardcoded Plan Limits:** All limits live in `plan_entitlements` (e.g., `daily_ai_turns`, `monthly_voice_minutes`, `monthly_homework_pages`, `allowed_exam_tracks`, `model_tier`).
- **Two-Layer Enforcement:**
  1. Fast pre-flight Redis token/minute bucket check (< 5ms) before invoking external AI/Voice APIs.
  2. Authoritative PostgreSQL `usage_ledgers` reconciliation.
- **Budget Alerts & Graceful Degradation:**
  - At 80% tenant/user monthly voice budget → notify user + switch non-critical feedback to text/captions.
  - At global anomaly spike (e.g., runaway loop or abuse attack) → automatic circuit breaker throttles abusive accounts and alerts `platform_admin`.
