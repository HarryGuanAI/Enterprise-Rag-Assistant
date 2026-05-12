from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
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


class PgVectorRetriever:
    """pgvector 向量检索器。

    第一版使用 cosine distance 做 Top-K 检索；后续可以在这里扩展 Hybrid Search、
    Rerank、多知识库过滤和更多元数据过滤。
    """

    def search(
        self,
        db: Session,
        *,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        top_k: int,
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
            .limit(top_k)
        )

        results: list[RetrievedChunk] = []
        for rank, (chunk, document, raw_distance) in enumerate(db.execute(statement).all(), start=1):
            # cosine distance 越小越相似；转成 0-1 左右的相似度分数，便于阈值判断和前端展示。
            score = max(0.0, min(1.0, 1.0 - float(raw_distance)))
            results.append(
                RetrievedChunk(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    title=document.original_filename,
                    section=chunk.section_path,
                    content=chunk.content,
                    score=score,
                    rank=rank,
                )
            )
        return results

