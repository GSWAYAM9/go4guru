# Content Rights, Licensing & IP Governance (`docs/CONTENT_RIGHTS.md`)

**Core Mandate (Section 8):** Never assume publicly downloadable or locally present PDFs can be commercially hosted, redistributed, embedded, or indexed into AI RAG pipelines without verified legal authorization.

---

## 1. Critical Phase 0 Finding: Quarantine of Sibling `D:\class-*` PDFs

During Phase 0 inspection ([DATA_ASSET_AUDIT.md](file:///d:/go4guru/docs/DATA_ASSET_AUDIT.md)), 374 PDFs in sibling directories `D:\class-6` .. `D:\class-12` were audited. All inspected samples carry **ALLEN® Career Institute** logos, diagonal watermarks, internal network paths, promotional banners, and/or PDF `/Encrypt` permission restrictions.

**Mandatory Policy Decision:**
- All 374 external PDFs in `D:\class-*` are classified **`THIRD_PARTY_QUARANTINED`**.
- They **MUST NOT** be copied into `d:\go4guru`, hosted to users, parsed into CMS items, imported into the Question Bank, or embedded into `knowledge_chunks` unless the project owner supplies a signed commercial license agreement from the copyright holder and completes Legal/Content Rights sign-off.

---

## 2. Seven-Tier Source Classification

Every content item, question, flashcard, media asset, and RAG document in the database MUST belong to one explicit `source_category`:

| Category Code | Hosting Allowed | RAG Embedding Allowed | Attribution / Rules |
| :--- | :---: | :---: | :--- |
| `ORIGINAL_PLATFORM` | Yes | Yes | Authored in-house by our curriculum team; full platform IP ownership. |
| `LICENSED_PARTNER` | Per contract | Per contract | Driven strictly by `content_licenses` flags (`commercial_use_allowed`, `territory`, `expires_at`). |
| `OFFICIAL_LINK` | **Metadata/URL only** | **No** (unless explicitly OER licensed) | Links students lawfully to official portals (e.g., `ncert.nic.in` e-books) without re-hosting files. |
| `AI_GENERATED` | Yes (post-review) | Yes (post-approval) | Must carry `ai_generated = true`, model/prompt provenance, and pass Academic Reviewer QA before publishing. |
| `TEACHER_CREATED` | Tenant-scoped (or opted-in) | Tenant-scoped | Isolated to originating school/tenant unless explicitly contributed under a verified license. |
| `STUDENT_CREATED` | Private to student | **No** | Personal notes & homework uploads belong strictly to the student; never surfaced to other users or global RAG. |
| `THIRD_PARTY_QUARANTINED` | **NO** | **NO** | Blocked at DB/service layer (`legal_review_status = 'quarantined'`). |

---

## 3. Non-Endorsement & Attribution Standards

- **No Implied Official Endorsement:** Platform UI, marketing copy, and PDFs/exports must never claim or imply official endorsement, affiliation, or sponsorship by **NCERT**, **CBSE**, **NTA**, **IITs**, or **NMC**.
- **Public Curriculum Facts vs. Copyrighted Expression:** Syllabus hierarchy names (Board, Class, Subject, Chapter Titles) are factual taxonomy references used for lawful alignment; textbook prose, illustrations, and proprietary coaching solutions are NOT copied without license.
- **Verified PYQ Provenance:** Official past exam questions cited for practice must record exam year/session/shift/paper provenance and comply with applicable fair-dealing/licensing counsel guidance before commercial distribution.

---

## 4. Content Rights Review Checklist (Pre-Publish & Pre-Release)

- [ ] Every published `content_items`, `questions`, and `knowledge_documents` record has non-null `source_id` and `license_id`.
- [ ] `legal_review_status = 'approved'` enforced before any item moves to `PUBLISHED`.
- [ ] RAG query layer hard-filters `content_licenses.embedding_allowed = true` and `expiry_at IS NULL OR expiry_at > now()`.
- [ ] Expiring partner licenses emit 30-day renewal/unpublish alerts via scheduled worker.
- [ ] Zero copyrighted third-party PDFs (including `D:\class-*` ALLEN files) exist in `d:\go4guru`, S3 buckets, or vector indexes.
- [ ] Legal counsel sign-off documented for textbook reference linking, PYQ usage, and AI-generated derivative explanations.
