# Data Asset Audit (`docs/DATA_ASSET_AUDIT.md`)

**Audit Date:** 2026-11-26  
**Scope Searched:**  
- Active Workspace: `d:\go4guru`  
- Adjacent Sibling Educational Directories (read-only inspection): `D:\class-6`, `D:\class-7`, `D:\class-8`, `D:\class-8-socialscience`, `D:\class-9`, `D:\class-10`, `D:\class-10-english`, `D:\class-11`, `D:\class-12`

---

## 1. Workspace Search Results (`d:\go4guru`)

| Asset Category | Extensions Searched | Count in `d:\go4guru` | Notes |
| :--- | :--- | :---: | :--- |
| Excel Workbooks | `.xlsx`, `.xls` | 0 | No question bank or curriculum Excel workbooks present in workspace |
| Delimited Datasets | `.csv`, `.tsv` | 0 | None present |
| Structured Data | `.json`, `.yaml`, `.sql` | 0 | None present |
| Documents / Textbooks | `.pdf`, `.docx` | 0 | None present inside `d:\go4guru` |
| Question Bank / PYQ / Quiz Datasets | All | 0 | None present inside `d:\go4guru` |

**Conclusion for Excel Assets:** Because **0** `.xlsx`/`.xls`/`.csv` files exist anywhere in `d:\go4guru` or `D:\class-*`, **no column structures are assumed**. The ingestion pipeline specified in [EXCEL_IMPORT_SPECIFICATION.md](file:///d:/go4guru/docs/EXCEL_IMPORT_SPECIFICATION.md) is designed with dynamic sheet inspection and interactive column mapping rather than hardcoded column names.

---

## 2. Adjacent Sibling Asset Discovery (`D:\class-*`, Outside Workspace)

Outside `d:\go4guru`, 9 directories exist directly on `D:\` containing **374 `.pdf` files** totaling **450.79 MB**. All 374 files were hashed (SHA-256) and scanned for PDF headers/metadata, and 10 representative PDFs across all 9 directories were visually and textually inspected. Original files were **not modified**.

### 2.1 Quantitative Inventory by Directory

| Directory | Files | Total Size | Named Files | `original*.pdf` | `/Encrypt` Flag | Min Size | Max Size |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `D:\class-6` | 51 | 61.16 MB | 0 | 51 | 5 | 127 KB | 8.45 MB |
| `D:\class-7` | 47 | 14.84 MB | 0 | 47 | 32 | 145 KB | 1.76 MB |
| `D:\class-8` | 41 | 11.47 MB | 0 | 41 | 12 | 96 KB | 0.55 MB |
| `D:\class-8-socialscience` | 7 | 1.19 MB | 0 | 7 | 7 | 166 KB | 0.18 MB |
| `D:\class-9` | 41 | 15.32 MB | 12 | 29 | 12 | 131 KB | 3.87 MB |
| `D:\class-10` | 48 | 15.00 MB | 6 | 42 | 6 | 119 KB | 1.15 MB |
| `D:\class-10-english` | 27 | 5.19 MB | 0 | 27 | 1 | 139 KB | 1.22 MB |
| `D:\class-11` | 56 | 23.86 MB | 0 | 56 | 0 | 182 KB | 0.94 MB |
| `D:\class-12` | 56 | 302.77 MB | 0 | 56 | 0 | 311 KB | 53.84 MB |
| **Total** | **374** | **450.79 MB** | **18** | **356** | **75** | **96 KB** | **53.84 MB** |

*(Note: 1 MB = 1,048,576 bytes in size reporting; 365 unique SHA-256 hashes out of 374 total files.)*

### 2.2 Named Files Observed

- **`D:\class-10` (6 named):** `Forest-&-Wildlife-Resources.pdf`, `Lifelines of National Economy.pdf`, `Manufacturing Industries.pdf`, `Minerals and Energy Resources.pdf`, `Nationalism-in-India.pdf`, `Water-Resources.pdf` (plus 42 `original*.pdf`).
- **`D:\class-9` (12 named):** `Constitutional+Design+-+Exercise.pdf`, `Electoral Politics.pdf`, `Food Security in India.pdf`, `Forest Society & Colonialism.pdf`, `Nazism+and+the+Rise+of+Hitler+-+Exercise.pdf`, `Pastoralists in the Modern World.pdf`, `People+as+Resource+-+Exercise.pdf`, `Poverty As a Challenge.pdf`, `Socialism+in+Europe+and+the+Russian+Revolution+-+Exercise.pdf`, `The+French+Revolution+-+Exercise.pdf`, `The+Story+of+Village+Palampur+-+Exercise.pdf`, `What+is+Democracy%2C+Why+Democracy+-+Exercise.pdf` (plus 29 `original*.pdf`).

---

## 3. Exact Duplicate Analysis (SHA-256 Verified)

Across all 374 PDFs, there are **365 unique SHA-256 hashes** and **6 duplicate groups** producing **9 redundant copies**:

| Group | Identical Byte Size | Identical Files | Critical Anomaly Observed |
| :---: | :---: | :--- | :--- |
| 1 | 518,116 bytes | `D:\class-6\original (6).pdf`<br>`D:\class-9\Constitutional+Design+-+Exercise.pdf`<br>`D:\class-9\The+French+Revolution+-+Exercise.pdf`<br>`D:\class-9\What+is+Democracy%2C+Why+Democracy+-+Exercise.pdf` | **Severe Mislabeling:** All 3 Class 9 Social Science exercise files are byte-for-byte identical to Class 6 Maths Chapter 7 ("7. Fractions", NCERT Basics: Class 6, ALLEN). |
| 2 | 984,308 bytes | `D:\class-12\original.pdf`<br>`D:\class-12\original (1).pdf` | Exact duplicate (`Chapter 1: Electric Charges & Fields`, Physics Class XII). |
| 3 | 30,676,929 bytes | `D:\class-12\original (29).pdf`<br>`D:\class-12\original (30).pdf` | Exact duplicate (`NCERT Solutions: Class 12 Maths Chapter 5`, 205 pages). |
| 4 | 1,360,039 bytes | `D:\class-12\original (32).pdf`<br>`D:\class-12\original (35).pdf` | Exact duplicate (`NCERT Solutions for Class 12 Maths Ch8`). |
| 5 | 56,454,814 bytes | `D:\class-12\original (33).pdf`<br>`D:\class-12\original (34).pdf` | Exact duplicate (`NCERT Solutions: Class 12 Maths Chapter 7`, ~53.84 MB). |
| 6 | 555,685 bytes | `D:\class-12\original (53).pdf`<br>`D:\class-12\original (53) - Copy.pdf`<br>`D:\class-12\original (53) - Copy - Copy.pdf` | 3 identical copies (`- Copy` suffix artifacts). |

---

## 4. PDF Metadata & Content Inspection Findings

### 4.1 Producer & Creator Scan (Literal Metadata Header/Trailer)

- **Microsoft® Word for Microsoft 365:** 81 files (UTF-16BE + ASCII)
- **Skia/PDF Google Docs Renderer (`m136`, `m145`, `m147`, `m149`):** 61 files
- **Microsoft® Word 2010 / 2019:** 6 files
- **Other / Compressed Object Streams or Encrypted Trailers:** 226 files
- **PDF `/Encrypt` Permission Dictionaries:** 75 files (mostly Class 7: 32/47; Class 8: 12/41; Class 8 SST: 7/7; Class 9: 12/41; Class 10: 6/48; Class 6: 5/51; Class 10 English: 1/27). Sampled encrypted file (`D:\class-8-socialscience\original.pdf`) opens without a user password, indicating owner/permission restrictions (copy/print/edit DRM flags).

### 4.2 Inspected Sample Files (Observed Content & Provenance)

| Sample File Inspected | Actual Subject / Grade / Content | Author / Branding | Technical & Rights Issues Observed |
| :--- | :--- | :--- | :--- |
| `D:\class-6\original.pdf` | Class 6 Maths, Ch 1 ("1.1 What is Mathematics?", "1.2 Patterns in Numbers") | **ALLEN®** ("NCERT Basics: Class 6 — NCERT QUESTIONS WITH SOLUTIONS") | Internal share path watermark: `SMD_Data$\PNCF\2025-26\Print Module\SET-1\NCERT\Maths\6th\M-1`; proprietary ALLEN® branding. |
| `D:\class-7\original.pdf` | Class 7 Maths, Ch 1 ("1. Large number around us", "FIGURE IT OUT-01..06") | **ALLEN®** ("NCERT Basics: Class 7") | Internal IP share watermark: `\\172.26.70.208\SMD_Data$\PNCF\2026-27\Print Module\SET-1\NCERT\Mathematics\7th\1. Large number around us`; proprietary ALLEN® branding. |
| `D:\class-8\original.pdf` | Class 8 Maths, Ch 1 ("1. A Square and A Cube") | **ALLEN®** ("NCERT Basics: Class 8") | Internal IP watermark `\\172.26.70.208\smd_data$\PNCF\2026-27\...`; proprietary ALLEN® branding. |
| `D:\class-8-socialscience\original.pdf` | Class 8 Social Science (Natural Resources, Ecosystem Functions) | **ALLEN®** ("NCERT Basics: Class 8") | `/Encrypt` dictionary present; internal IP watermark; typo in numbering `(iii)` twice (`(iii) Soil Fertility`); proprietary ALLEN® branding. |
| `D:\class-9\The+French+Revolution+-+Exercise.pdf` | **Class 6 Maths Ch 7 ("7. Fractions")** — **MISLABELED!** | **ALLEN®** ("NCERT Basics: Class 6") | File is named Class 9 French Revolution, but content is Class 6 Maths Fractions (`SET-2\NCERT\Maths\6th\7. Fractions`), identical SHA-256 to `D:\class-6\original (6).pdf` and two other Class 9 SST files. |
| `D:\class-10\Nationalism-in-India.pdf` | Class 10 Social Science (History: Nationalism in India, Q1–Q7) | **ALLEN®** ("NCERT Basics: Class 10") | Watermark `Publishing$\PNCF\2024-25\LIVE Module\NCERT\10th\Social Science`; proprietary ALLEN® branding. |
| `D:\class-10\Forest-&-Wildlife-Resources.pdf` | Class 10 Social Science (Geography: Forest & Wildlife Resources) | **ALLEN®** ("NCERT Basics: Class 10") | Watermark `Publishing$\PNCF\2024-25\LIVE Module\SET-1\NCERT\10th\Social Science`; typo `So,e villagers`, `Sancturies`. |
| `D:\class-10-english\original.pdf` | Class 10 English ("A Letter to God" — Lencho) | **ALLEN®** ("NCERT Basics: Class 10") | Watermark `Publishing\PNCF\2024-25\LIVE Module\SET-1\NCERT\10th\English`; proprietary ALLEN® branding. |
| `D:\class-11\original.pdf` | Class 11 Maths, Ch 1 ("CHAPTER - 1 : SETS") | **ALLEN®** ("NCERT Questions and Solutions") | Bottom promo banner ("NCERT SOLUTIONS for LEARNING CORE CONCEPTS — SHOP NOW", "CBSE Class XII Books"); proprietary ALLEN® branding. |
| `D:\class-12\original.pdf` | Class 12 Physics, Ch 1 ("ELECTRIC CHARGES & FIELDS") | **ALLEN®** ("Physics CBSE : Class-XII") | Bottom promo banner ("SHOP NOW"); proprietary ALLEN® branding. |
| `D:\class-12\original (25).pdf` | Class 12 Maths, Ch 1 ("Relations and Functions") | **ALLEN®** (Google Docs/Skia export with diagonal ALLEN® watermark) | Typographic/LaTeX errors: `a ≤ b 2` instead of `a ≤ b²`, `1 x` instead of `1/x`, `f x x x ( ) , , , = > = < 1 0 0 0 1 0`, broken line breaks (`S\no`). |
| `D:\class-12\original (29).pdf` | Class 12 Maths, Ch 5 ("Continuity and Differentiability", 205 pages, 30.6 MB) | **ALLEN®** (Google Docs/Skia export with diagonal ALLEN® watermark) | Severe rendering defects: `[cite_start]` raw tags on pages 11 & 61, raw LaTeX `\quad \text{(since}` on page 25, `$$` leaks on page 84, `f(x) = ... $at$x=2` on pages 47/50, plus mathematical extraction loss (`f'(x)` stripped in OCR layer). |

---

## 5. Academic Coverage, Question Types & Quality Summary (Sibling PDFs)

- **Observed Grades Covered:** Classes 6, 7, 8, 9, 10, 11, 12.
- **Observed Subjects:** Mathematics, Science/Physics (at least Physics in Class 12; full subject breakdown across the 356 `original*.pdf` files cannot be inferred from filenames alone), Social Science, English.
- **Observed Question Types:** NCERT exercise subjective short/long answers, fill-in-the-blanks, match-the-following, picture/diagram questions, true/false with reasoning, and a few NCERT MCQs. **No verified JEE Main / JEE Advanced / NEET PYQs** were observed in the inspected sample.
- **PYQ Metadata:** **None** observed in inspected files (these are NCERT textbook exercise solutions).
- **Difficulty Distribution:** Not tagged; predominantly NCERT foundational level.

---

## 6. Recommended Canonical Mapping & Import Risk Assessment

| Risk | Severity | Details | Required Mitigation |
| :--- | :---: | :--- | :--- |
| **Copyright / Trademark / IP Infringement** | **CRITICAL** | All inspected PDFs belong to **ALLEN® Career Institute** with trademarks, commercial banners, internal file-server paths, and 75 `/Encrypt` permissions dictionaries. | **QUARANTINE IMMEDIATELY.** Do NOT ingest, host, redistribute, or index into RAG without a written commercial license from ALLEN. |
| **Misleading File Names** | **HIGH** | Class 9 Social Science filenames contain Class 6 Maths PDFs; 356 files are anonymously named `original (N).pdf`. | Never map grade/subject/chapter from filename. Any future licensed ingestion must extract content-level headers/titles and verify via human review. |
| **Corrupted LaTeX / OCR Defects** | **HIGH** | Google Docs Skia PDFs (`Class 12 Maths`) drop math formatting in text extraction and contain `[cite_start]` / raw `$$` defects. | Reject automated scraping of defective PDFs; enforce QA validation gates and mathematical verification before any content reaches students. |
| **Duplicate Files** | **MEDIUM** | 9 redundant copies across 6 SHA-256 groups (including 87 MB of duplicate Class 12 Maths PDFs). | Enforce SHA-256 deduplication at upload/staging before parsing. |
| **Missing Excel / CSV Question Banks** | **HIGH** | 0 `.xlsx`/`.xls`/`.csv` datasets found in workspace or sibling dirs. | Do not fabricate question bank records; build dynamic Excel staging pipeline and request real licensed/authored `.xlsx` source files from the user. |

**Canonical Mapping Status:** `BLOCKED_BY_RIGHTS_AND_QUALITY` — External `D:\class-*` PDFs must NOT be mapped into production tables. Instead, Phase 1 curriculum seeding should use clean NCERT syllabus structure metadata (board/grade/subject/chapter titles, which are public curriculum facts, linked to official NCERT URLs) plus originally authored sample items clearly marked `ORIGINAL_AUTHORED` / `DEVELOPMENT_SEED`.
