# Curriculum Architecture (`docs/CURRICULUM_ARCHITECTURE.md`)

**Scope:** Classes 6–12 | CBSE + Competitive Exams (JEE Main, JEE Advanced, NEET) | Multilingual & Versioned

---

## 1. Core Principles

1. **Zero Hardcoding in UI or Business Logic:** All boards, grades, subjects, books, chapters, topics, concepts, prerequisites, and exam mappings live in versioned PostgreSQL tables (`curriculum.*`).
2. **Immutable Curriculum Versioning:** Historical quiz/exam attempts, mastery records, and lesson plans pin `curriculum_version_id` and `concept_id` so syllabus revisions across academic years (e.g., CBSE rationalized NCERT editions 2024–25 vs 2026–27) never corrupt historical student records.
3. **Graph-Aware Concept Dependencies:** Concepts link via directed acyclic prerequisite edges (`concept_prerequisites`), allowing both remediation ("backtrack to Class 8 Linear Equations") and multi-concept competitive exam attribution ("JEE Adv problem requires Electrostatics + Rotational Mechanics").

---

## 2. 11-Level Academic Hierarchy

```text
BOARD (e.g., CBSE)
 └── ACADEMIC SESSION (e.g., 2026-27) [linked via curriculum_versions]
      └── GRADE (Class 6 .. Class 12)
           └── SUBJECT (Mathematics, Science, Physics, Chemistry, Biology, English, Social Science, ...)
                └── BOOK (e.g., NCERT Mathematics Class 10, Ganita Prakash Class 6/7)
                     └── CHAPTER (e.g., Ch 7: Fractions)
                          └── SECTION (e.g., 7.6 Equivalent Fractions)
                               └── TOPIC (e.g., Simplifying Fractions)
                                    └── CONCEPT (Atomic assessable unit, e.g., MATH-06-FRAC-EQV)
                                         ├── LEARNING OBJECTIVE (Bloom-tagged measurable outcome)
                                         └── PREREQUISITE (DAG edge to prior concept_ids)
```

---

## 3. Competitive Exam Cross-Mapping

Rather than duplicating concepts for CBSE vs JEE vs NEET, competitive exams attach via `exam_tracks` and `exam_concept_mappings`:
- **CBSE Board:** Maps Classes 6–12 core concepts, competency indicators, case-study clusters, and internal choice blueprints.
- **JEE Main & JEE Advanced:** Maps Physics, Chemistry, and Mathematics concepts across Classes 11–12 (plus Class 9–10 foundation bridges) with difficulty ceiling, multi-concept linkage, and historical weightage metadata.
- **NEET:** Maps Physics, Chemistry, and Biology (split into `Botany` and `Zoology` sub-disciplines) with explicit NCERT line/concept emphasis tags.

---

## 4. Tagging, Multilingual & Rights Integration

- **Concept Metadata:** `skill_tags` (`computational`, `conceptual`, `experimental`, `map_reading`, `grammar`), `exam_tags`, `difficulty_baseline` (`1..5`).
- **Multilingual Localization:** Each node (`subjects`, `chapters`, `topics`, `concepts`, `learning_objectives`) supports localized labels via `curriculum_translations` (or `terminology_glossary`) preserving canonical `concept.code` and standard scientific notation across languages.
- **Textbook Linking Policy:** `books.official_source_url` stores official NCERT portal links rather than republishing copyrighted PDFs; internal explanations/summaries come from rights-approved CMS items mapped to `chapter_id`/`concept_id`.

---

## 5. Versioning Workflow

1. Content Admin clones `2025-26-v1` → `2026-27-draft` (`curriculum_versions`).
2. Edits/rationalizes chapters/concepts; DAG validator verifies zero cycles in `concept_prerequisites`.
3. Published `2026-27-v1` becomes default for new enrollments while `2025-26-v1` stays read-accessible for existing assessments and historical analytics.
