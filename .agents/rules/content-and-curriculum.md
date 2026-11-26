---
trigger: model_decision
description: Rules for versioned curriculum hierarchy, CMS lifecycle, content licensing, NCERT/CBSE non-endorsement, and quarantine of unlicensed third-party PDFs.
---

# Content & Curriculum Rules

Reference: [docs/CURRICULUM_ARCHITECTURE.md](../../docs/CURRICULUM_ARCHITECTURE.md), [docs/CONTENT_RIGHTS.md](../../docs/CONTENT_RIGHTS.md), [docs/DATA_ASSET_AUDIT.md](../../docs/DATA_ASSET_AUDIT.md).

1. **Data-Driven 11-Level Curriculum:** Model curriculum strictly via versioned DB entities (`Board → Academic Session → Grade (6–12) → Subject → Book → Chapter → Section → Topic → Concept → Learning Objective → Prerequisite`) + `exam_concept_mappings` (`CBSE`, `JEE Main`, `JEE Advanced`, `NEET`). Never hardcode syllabus trees in frontend components.
2. **Immutable Curriculum Versions & DAG Validity:** Pin `curriculum_version_id` on historical exams and mastery records. Validate `concept_prerequisites` to forbid cycles.
3. **Editorial Lifecycle Gate:** Enforce `DRAFT → VALIDATION → REVIEW → APPROVED → PUBLISHED → ARCHIVED`. Unreviewed drafts MUST never appear in student learning, exam blueprints, or RAG retrieval.
4. **Content Rights & Quarantine Enforcement:**
   - Every content item requires `source_id`, `license_id`, and `legal_review_status = 'approved'` before publishing.
   - **Strict Quarantine:** The 374 third-party ALLEN® PDFs observed in sibling `D:\class-*` folders are `THIRD_PARTY_QUARANTINED`. Never copy, host, parse, or embed them into RAG without written licensing.
   - Prefer `OFFICIAL_LINK` (linking to official NCERT portals without re-hosting) and `ORIGINAL_PLATFORM` authored content. Never imply NCERT, CBSE, or NTA endorsement.
