"""Rights-enforced Curriculum Hybrid RAG (PostgreSQL 18 FTS + Dense Cosine RRF)."""

from __future__ import annotations

import hashlib
import math
import re
from uuid import UUID

from fastapi import status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.errors import AppError
from src.modules.ai.models import KnowledgeChunk, KnowledgeDocument
from src.modules.ai.schemas import CitedChunk, KnowledgeDocIngestRequest, KnowledgeDocOut
from src.modules.content.public import assert_license_usable

EMBEDDING_DIM = 64
_WORD_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


def compute_local_embedding(content: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Compute a deterministic L2-normalized dense semantic sketch (no external key required)."""
    vec = [0.0] * dim
    tokens = _WORD_RE.findall(content.lower())
    if not tokens:
        return vec
    # Include unigrams + bigrams so multi-word STEM terms align strongly in cosine rank
    features = list(tokens) + [f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)]
    for feat in features:
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[bucket] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [round(v / norm, 6) for v in vec]
    return vec


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def split_markdown_chunks(
    content_markdown: str, target_chars: int = 900
) -> list[tuple[str | None, str]]:
    """Split markdown along heading/paragraph boundaries keeping LaTeX blocks intact."""
    blocks = [b.strip() for b in re.split(r"\n{2,}", content_markdown.strip()) if b.strip()]
    chunks: list[tuple[str | None, str]] = []
    cur_section: str | None = None
    buf: list[str] = []
    cur_len = 0

    for block in blocks:
        if block.startswith("#"):
            if buf:
                chunks.append((cur_section, "\n\n".join(buf)))
                buf = []
                cur_len = 0
            cur_section = block.lstrip("#").strip()[:220]
        buf.append(block)
        cur_len += len(block)
        if cur_len >= target_chars:
            chunks.append((cur_section, "\n\n".join(buf)))
            buf = []
            cur_len = 0

    if buf:
        chunks.append((cur_section, "\n\n".join(buf)))
    return chunks or [(None, content_markdown.strip()[:target_chars])]


async def ingest_knowledge_document(
    db: AsyncSession,
    payload: KnowledgeDocIngestRequest,
    caller: AuthenticatedUser,
) -> KnowledgeDocOut:
    """Enforce license + embedding_allowed gate before splitting & indexing chunks."""
    await assert_license_usable(
        db,
        source_id=payload.source_id,
        license_id=payload.license_id,
        require_approved=True,
        for_embedding=True,
    )

    doc = KnowledgeDocument(
        source_id=payload.source_id,
        license_id=payload.license_id,
        curriculum_version_id=payload.curriculum_version_id,
        grade_id=payload.grade_id,
        subject_id=payload.subject_id,
        chapter_id=payload.chapter_id,
        topic_id=payload.topic_id,
        concept_id=payload.concept_id,
        title=payload.title.strip(),
        language_code=payload.language_code.strip(),
        status="PUBLISHED",
        embedding_allowed=True,
        attribution_text=payload.attribution_text,
        created_by=caller.id,
    )
    db.add(doc)
    await db.flush()

    sections = split_markdown_chunks(payload.content_markdown)
    for idx, (sec_title, chunk_body) in enumerate(sections, start=1):
        vec = compute_local_embedding(f"{payload.hierarchy_path} {sec_title or ''} {chunk_body}")
        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=idx,
            hierarchy_path=payload.hierarchy_path.strip(),
            section_title=sec_title,
            language_code=payload.language_code.strip(),
            chunk_text=chunk_body,
            embedding_vec=vec,
            token_estimate=max(1, len(chunk_body.split())),
            metadata_jsonb={"title": doc.title},
        )
        db.add(chunk)
        await db.flush()
        # Populate PostgreSQL tsvector deterministically for FTS GIN index queries
        await db.execute(
            text(
                "UPDATE knowledge_chunks SET fts_tsv = to_tsvector('english', :txt) WHERE id = :cid"
            ),
            {"txt": f"{payload.hierarchy_path} {sec_title or ''} {chunk_body}", "cid": chunk.id},
        )

    await db.commit()
    await db.refresh(doc)
    return KnowledgeDocOut(
        id=doc.id,
        title=doc.title,
        language_code=doc.language_code,
        status=doc.status,
        embedding_allowed=doc.embedding_allowed,
        chunk_count=len(sections),
        created_at=doc.created_at,
    )


class HybridRetrievalService:
    """Hybrid sparse FTS + dense vector RRF retriever enforcing PUBLISHED & rights filters."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def retrieve(
        self,
        *,
        query: str,
        grade_id: UUID | None = None,
        subject_id: UUID | None = None,
        chapter_id: UUID | None = None,
        language_code: str = "en",
        top_k: int = 5,
    ) -> list[CitedChunk]:
        if not query.strip():
            return []

        # Strict SQL pre-filter: PUBLISHED docs + embedding_allowed + unexpired approved license
        base_sql = """
            SELECT
                c.id,
                c.document_id,
                c.hierarchy_path,
                c.section_title,
                c.language_code,
                c.chunk_text,
                c.embedding_vec,
                d.attribution_text,
                ts_rank_cd(c.fts_tsv, plainto_tsquery('english', :q)) AS fts_score
            FROM knowledge_chunks c
            JOIN knowledge_documents d ON d.id = c.document_id
            JOIN content_sources s ON s.id = d.source_id
            JOIN content_licenses l ON l.id = d.license_id
            WHERE d.status = 'PUBLISHED'
              AND d.embedding_allowed = true
              AND s.source_category <> 'quarantined_third_party'
              AND l.legal_review_status = 'approved'
              AND l.embedding_allowed = true
              AND (l.expires_at IS NULL OR l.expires_at > now())
        """
        params: dict[str, object] = {"q": query.strip()}
        if grade_id is not None:
            base_sql += " AND (d.grade_id IS NULL OR d.grade_id = :grade_id)"
            params["grade_id"] = grade_id
        if subject_id is not None:
            base_sql += " AND (d.subject_id IS NULL OR d.subject_id = :subject_id)"
            params["subject_id"] = subject_id
        if chapter_id is not None:
            base_sql += " AND (d.chapter_id IS NULL OR d.chapter_id = :chapter_id)"
            params["chapter_id"] = chapter_id
        if language_code:
            base_sql += " AND (c.language_code = :lang OR c.language_code = 'en')"
            params["lang"] = language_code

        base_sql += " LIMIT 120"

        rows = (await self.db.execute(text(base_sql), params)).mappings().all()
        if not rows:
            return []

        q_vec = compute_local_embedding(query)
        scored_rows: list[tuple[dict[str, object], float, float]] = []
        for row in rows:
            fts_val = float(row["fts_score"] or 0.0)
            vec_raw = list(row["embedding_vec"] or [])
            dense_val = _cosine_similarity(q_vec, [float(x) for x in vec_raw])
            scored_rows.append((dict(row), fts_val, dense_val))

        # Reciprocal Rank Fusion (k=60) combining sparse FTS order & dense cosine order
        by_fts = sorted(range(len(scored_rows)), key=lambda idx: scored_rows[idx][1], reverse=True)
        by_dense = sorted(
            range(len(scored_rows)), key=lambda idx: scored_rows[idx][2], reverse=True
        )
        fts_rank = {idx: r for r, idx in enumerate(by_fts, start=1)}
        dense_rank = {idx: r for r, idx in enumerate(by_dense, start=1)}

        fused: list[tuple[float, dict[str, object], float]] = []
        k = 60.0
        for idx, (row_dict, fts_v, dense_v) in enumerate(scored_rows):
            # Ignore completely irrelevant noise when both FTS and cosine signal are ~0
            if fts_v <= 0.0 and dense_v < 0.08:
                continue
            rrf = (1.0 / (k + fts_rank[idx])) + (1.0 / (k + dense_rank[idx]))
            # Language preference bonus when matching requested language directly
            if row_dict["language_code"] == language_code:
                rrf += 0.002
            fused.append((rrf, row_dict, dense_v))

        fused.sort(key=lambda item: item[0], reverse=True)
        out: list[CitedChunk] = []
        for rrf_score, r, _dense in fused[:top_k]:
            out.append(
                CitedChunk(
                    chunk_id=UUID(str(r["id"])),
                    document_id=UUID(str(r["document_id"])),
                    hierarchy_path=str(r["hierarchy_path"]),
                    section_title=str(r["section_title"]) if r["section_title"] else None,
                    language_code=str(r["language_code"]),
                    excerpt=str(r["chunk_text"])[:500],
                    source_attribution=(
                        str(r["attribution_text"]) if r["attribution_text"] else None
                    ),
                    score=round(rrf_score, 5),
                )
            )
        return out


def validate_citations(cited_ids: list[str], retrieved: list[CitedChunk]) -> list[CitedChunk]:
    """Post-generation filter dropping any fabricated citation UUID not present in retrieved set."""
    by_id = {str(c.chunk_id): c for c in retrieved}
    valid: list[CitedChunk] = []
    seen: set[str] = set()
    for raw_id in cited_ids:
        clean = raw_id.strip()
        if clean in by_id and clean not in seen:
            seen.add(clean)
            valid.append(by_id[clean])
    return valid


async def list_knowledge_documents(db: AsyncSession) -> list[KnowledgeDocOut]:
    """List indexed knowledge documents with actual chunk counts."""
    docs = (
        await db.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).limit(50)
        )
    ).all()
    if not docs:
        return []
    out: list[KnowledgeDocOut] = []
    for doc in docs:
        cnt = int(
            await db.scalar(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE document_id = :did"),
                {"did": doc.id},
            )
            or 0
        )
        out.append(
            KnowledgeDocOut(
                id=doc.id,
                title=doc.title,
                language_code=doc.language_code,
                status=doc.status,
                embedding_allowed=doc.embedding_allowed,
                chunk_count=cnt,
                created_at=doc.created_at,
            )
        )
    return out


async def raise_if_no_rights_doc(doc: KnowledgeDocument | None) -> None:
    if doc is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="KNOWLEDGE_DOC_NOT_FOUND",
            message="Knowledge document not found.",
        )
