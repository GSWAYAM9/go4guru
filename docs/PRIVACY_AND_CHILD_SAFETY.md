# Privacy & Child Safety Architecture (`docs/PRIVACY_AND_CHILD_SAFETY.md`)

**Core Principle (Section 42):** Because this platform serves minors (Classes 6–12), child safety, privacy-by-design, and data minimization are non-negotiable engineering requirements.  
**Legal Disclaimer Gate:** We **will not claim legal compliance** (including under India's **Digital Personal Data Protection (DPDP) Act, 2023** and DPDP Rules) until qualified legal counsel reviews the implemented consent, retention, residency, and deletion workflows prior to launch.

---

## 1. Age-Aware & Verifiable Guardian Consent Architecture

1. **Age Gate at Registration:** Collect birth year/age band (minimum required data) during onboarding. Users under 18 (or applicable statutory threshold) are flagged `is_minor = true` and enter `pending_parent_consent` status for features requiring guardian authorization.
2. **Verifiable Guardian Consent Workflow:**
   - Minor provides parent/guardian contact (or Parent initiates registration).
   - Platform sends time-limited consent verification link/OTP + plain-language notice explaining what data is collected, AI usage, and rights.
   - Consent is persisted in `consents` with timestamp, `policy_version`, verification method, and withdrawal capability.
3. **Parent Privacy Boundary (Psychological Safety vs. Oversight):**
   - Parents view **learning summaries** (lessons completed, practice accuracy, weak concepts, upcoming tests, revision adherence, goal progress).
   - Parents do **NOT** automatically receive unrestricted read access to raw private AI tutor chat transcripts (`ai_messages`), preventing chilling effects when students ask basic doubts or sensitive academic questions.
   - Exceptions occur only via explicit safety/welfare escalation policies reviewed by legal/trust & safety teams.

---

## 2. Data Minimization & External AI Provider Hygiene

- **Never transmit student PII** (`display_name`, `email`, `phone`, `school_name`, `roll_number`) in prompts sent to external LLM, TTS, STT, or OCR providers.
- Send only anonymized session IDs and academic context (`grade=9`, `board=CBSE`, `concept=Linear Equations`, `mastery_band=developing`).
- Prefer enterprise/API zero-data-retention (ZDR) agreements with external AI/voice providers so student queries are never used for third-party model training.
- Zero third-party behavioral advertising SDKs, trackers, or profiling cookies on student workspaces.

---

## 3. Child-Safe AI Guardrails, Moderation & Support Pathways

1. **Pre-Prompt & Post-Response Filtering:** Safety layer blocks grooming, sexual content, violence, self-harm encouragement, hate speech, academic-dishonesty abuse (e.g., cheating live during proctored exams), and unsafe off-topic manipulation.
2. **Distress / Self-Harm Safe Redirection:** If a student expresses severe distress or self-harm ideation, the AI immediately halts tutoring, responds with a calm supportive message + verified regional/national helpline resources (e.g., Tele-MANAS / Childline India 1098, verified pre-launch), and logs a high-priority alert to the safety escalation queue.
3. **One-Click Reporting:** Every AI chat turn, classroom segment, question, and content page includes an accessible "Report Issue / Unsafe Content" control creating a `safety_incidents` record for human review.

---

## 4. Data Retention, Export & Erasure Workflows

- **Data Export (`GET /api/v1/users/me/data-export`):** User/verified guardian can request a structured JSON/ZIP export of personal profile, notes, and learning records.
- **Deletion / Right to Erasure (`POST /api/v1/users/me/deletion-request`):**
  - Triggers verifiable confirmation + cooling-off/immediate execution policy.
  - Purges S3 artifacts (homework images/PDFs, voice clips), deletes/anonymizes `users`, `user_profiles`, `sessions`, `ai_messages`, and `devices`.
  - Preserves only non-reidentifiable aggregate metrics and statutory tax/invoice records where legally mandated.

---

## 5. Pre-Launch Privacy & Child Safety Checklist

- [ ] Qualified legal counsel review of DPDP Act & Rules completed (verifiable parental consent mechanism, data fiduciary notices in English & regional languages, data localization/cross-border transfer rules).
- [ ] Guardian consent gate blocks unconsented minor AI/homework/billing flows.
- [ ] Parent API endpoints verified never to expose raw `ai_messages`.
- [ ] Automated test confirms external AI request payloads contain zero PII fields.
- [ ] Moderation safety red-team suite (self-harm, abuse, NSFW, PII exfiltration) passes 100%.
- [ ] End-to-end account deletion job verified across PostgreSQL, Redis, and S3/MinIO.
