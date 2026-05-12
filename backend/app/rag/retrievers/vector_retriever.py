import re
from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: UUID
    chunk_id: UUID
    title: str
    section: str | None
    content: str
    score: float
    rank: int
    vector_score: float = 0.0
    keyword_score: float = 0.0
    rerank_score: float | None = None
    source: str = "vector"


@dataclass(frozen=True)
class RetrievalStats:
    mode: str
    vector_candidates: int
    keyword_candidates: int
    fused_candidates: int


_ASCII_WORD_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}")
_CJK_TEXT_RE = re.compile(r"[\u4e00-\u9fff]+")
_CJK_STOP_CHARS = set("的是了和与及或在对中为把被有无吗呢哪些什么如何怎么需要是否可以一个")


class PgVectorRetriever:
    """pgvector 检索器，支持向量召回、关键词召回融合和轻量 Rerank。"""

    def __init__(self) -> None:
        self.last_stats = RetrievalStats(mode="vector", vector_candidates=0, keyword_candidates=0, fused_candidates=0)

    def search(
        self,
        db: Session,
        *,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        query_text: str = "",
        top_k: int,
        enable_hybrid_search: bool = False,
        enable_rerank: bool = False,
    ) -> list[RetrievedChunk]:
        candidate_limit = top_k if not (enable_hybrid_search or enable_rerank) else min(max(top_k * 4, 12), 40)
        vector_results = self._vector_search(
            db,
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            limit=candidate_limit,
        )

        keyword_results: list[RetrievedChunk] = []
        if enable_hybrid_search:
            keyword_results = self._keyword_search(
                db,
                knowledge_base_id=knowledge_base_id,
                query_text=query_text,
                limit=candidate_limit,
            )

        fused_results = self._fuse_results(vector_results, keyword_results, top_k=top_k, hybrid=enable_hybrid_search)

        if enable_rerank:
            fused_results = self._rerank(query_text=query_text, chunks=fused_results, top_k=top_k)
            mode = "hybrid+rerank" if enable_hybrid_search else "vector+rerank"
        else:
            fused_results = [replace(chunk, rank=rank) for rank, chunk in enumerate(fused_results[:top_k], start=1)]
            mode = "hybrid" if enable_hybrid_search else "vector"

        self.last_stats = RetrievalStats(
            mode=mode,
            vector_candidates=len(vector_results),
            keyword_candidates=len(keyword_results),
            fused_candidates=len(fused_results),
        )
        return fused_results

    def _vector_search(
        self,
        db: Session,
        *,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[RetrievedChunk]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
        statement = (
            select(DocumentChunk, Document, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.knowledge_base_id == knowledge_base_id,
                DocumentChunk.embedding.is_not(None),
                Document.status == "ready",
                Document.deleted_at.is_(None),
            )
            .order_by(distance.asc())
            .limit(limit)
        )

        results: list[RetrievedChunk] = []
        for rank, (chunk, document, raw_distance) in enumerate(db.execute(statement).all(), start=1):
            # cosine distance 越小越相似；转成 0-1 分数，便于阈值判断和前端展示。
            score = _clamp01(1.0 - float(raw_distance))
            results.append(
                RetrievedChunk(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    title=document.original_filename,
                    section=chunk.section_path,
                    content=chunk.content,
                    score=score,
                    rank=rank,
                    vector_score=score,
                    keyword_score=0.0,
                    source="vector",
                )
            )
        return results

    def _keyword_search(
        self,
        db: Session,
        *,
        knowledge_base_id: UUID,
        query_text: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        terms = _extract_keyword_terms(query_text)
        if not terms:
            return []

        conditions = []
        for term in terms:
            pattern = f"%{term}%"
            conditions.extend(
                [
                    DocumentChunk.content.ilike(pattern),
                    DocumentChunk.section_path.ilike(pattern),
                    Document.original_filename.ilike(pattern),
                ]
            )

        statement = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.knowledge_base_id == knowledge_base_id,
                Document.status == "ready",
                Document.deleted_at.is_(None),
                or_(*conditions),
            )
            .limit(limit * 4)
        )

        scored: list[RetrievedChunk] = []
        for chunk, document in db.execute(statement).all():
            keyword_score = _keyword_score(
                query_text=query_text,
                terms=terms,
                title=document.original_filename,
                section=chunk.section_path,
                content=chunk.content,
            )
            if keyword_score <= 0:
                continue
            scored.append(
                RetrievedChunk(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    title=document.original_filename,
                    section=chunk.section_path,
                    content=chunk.content,
                    score=keyword_score,
                    rank=0,
                    vector_score=0.0,
                    keyword_score=keyword_score,
                    source="keyword",
                )
            )

        scored.sort(key=lambda item: item.keyword_score, reverse=True)
        return [replace(chunk, rank=rank) for rank, chunk in enumerate(scored[:limit], start=1)]

    def _fuse_results(
        self,
        vector_results: list[RetrievedChunk],
        keyword_results: list[RetrievedChunk],
        *,
        top_k: int,
        hybrid: bool,
    ) -> list[RetrievedChunk]:
        if not hybrid:
            return [replace(chunk, rank=rank) for rank, chunk in enumerate(vector_results[:top_k], start=1)]

        by_id: dict[UUID, RetrievedChunk] = {}
        vector_ranks = {chunk.chunk_id: chunk.rank for chunk in vector_results}
        keyword_ranks = {chunk.chunk_id: chunk.rank for chunk in keyword_results}

        for chunk in [*vector_results, *keyword_results]:
            existing = by_id.get(chunk.chunk_id)
            if existing is None:
                by_id[chunk.chunk_id] = chunk
                continue
            by_id[chunk.chunk_id] = replace(
                existing,
                vector_score=max(existing.vector_score, chunk.vector_score),
                keyword_score=max(existing.keyword_score, chunk.keyword_score),
                source="hybrid",
            )

        fused: list[RetrievedChunk] = []
        for chunk in by_id.values():
            rrf_score = 0.0
            if chunk.chunk_id in vector_ranks:
                rrf_score += 1.0 / (60 + vector_ranks[chunk.chunk_id])
            if chunk.chunk_id in keyword_ranks:
                rrf_score += 1.0 / (60 + keyword_ranks[chunk.chunk_id])

            if chunk.vector_score > 0 and chunk.keyword_score > 0:
                score = _clamp01(0.78 * chunk.vector_score + 0.22 * chunk.keyword_score + 0.04)
                source = "hybrid"
            elif chunk.vector_score > 0:
                score = chunk.vector_score
                source = "vector"
            else:
                # 关键词独有命中能补召回，但分数上限保守，避免轻易绕过严格拒答。
                score = min(0.72, 0.5 + 0.22 * chunk.keyword_score)
                source = "keyword"

            fused.append(replace(chunk, score=score, rank=0, source=source, rerank_score=rrf_score))

        fused.sort(key=lambda item: (item.rerank_score or 0.0, item.score), reverse=True)
        return [replace(chunk, rank=rank) for rank, chunk in enumerate(fused[:top_k], start=1)]

    def _rerank(self, *, query_text: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        terms = _extract_keyword_terms(query_text)
        reranked: list[RetrievedChunk] = []
        for chunk in chunks:
            keyword_score = max(
                chunk.keyword_score,
                _keyword_score(
                    query_text=query_text,
                    terms=terms,
                    title=chunk.title,
                    section=chunk.section,
                    content=chunk.content,
                ),
            )
            rerank_score = _clamp01(0.82 * chunk.score + 0.18 * keyword_score)
            if chunk.vector_score > 0 and keyword_score > 0:
                rerank_score = _clamp01(rerank_score + 0.03)
            # Rerank 只改变排序和小幅加权，不降低向量召回已有的置信度，避免阈值校准被精排阶段破坏。
            rerank_score = max(rerank_score, chunk.score, chunk.vector_score)
            reranked.append(
                replace(
                    chunk,
                    score=rerank_score,
                    keyword_score=keyword_score,
                    rerank_score=rerank_score,
                    source="rerank" if chunk.source == "vector" else f"{chunk.source}+rerank",
                )
            )

        reranked.sort(key=lambda item: (item.rerank_score or item.score, item.vector_score), reverse=True)
        return [replace(chunk, rank=rank) for rank, chunk in enumerate(reranked[:top_k], start=1)]


def _extract_keyword_terms(query_text: str) -> list[str]:
    normalized = query_text.strip().lower()
    if not normalized:
        return []

    terms: list[str] = []
    terms.extend(match.group(0) for match in _ASCII_WORD_RE.finditer(normalized))

    for match in _CJK_TEXT_RE.finditer(normalized):
        phrase = match.group(0)
        if 2 <= len(phrase) <= 12:
            terms.append(phrase)
        for size in (4, 3, 2):
            if len(phrase) < size:
                continue
            for index in range(0, len(phrase) - size + 1):
                gram = phrase[index : index + size]
                if all(char in _CJK_STOP_CHARS for char in gram):
                    continue
                terms.append(gram)

    deduped: list[str] = []
    seen: set[str] = set()
    for term in sorted(terms, key=lambda item: (-len(item), item)):
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
        if len(deduped) >= 24:
            break
    return deduped


def _keyword_score(
    *,
    query_text: str,
    terms: list[str],
    title: str,
    section: str | None,
    content: str,
) -> float:
    if not terms:
        return 0.0

    haystack = f"{title}\n{section or ''}\n{content}".lower()
    title_section = f"{title}\n{section or ''}".lower()
    raw_score = 0.0
    max_score = 0.0

    for term in terms:
        weight = 1.0 + min(len(term), 6) / 6
        max_score += weight
        if term not in haystack:
            continue
        raw_score += weight
        if term in title_section:
            raw_score += weight * 0.5
        raw_score += min(haystack.count(term) - 1, 2) * weight * 0.12

    compact_query = re.sub(r"\s+", "", query_text.strip().lower())
    if len(compact_query) >= 4 and compact_query in haystack:
        raw_score += max_score * 0.35

    return _clamp01(raw_score / max(max_score * 0.55, 1.0))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
