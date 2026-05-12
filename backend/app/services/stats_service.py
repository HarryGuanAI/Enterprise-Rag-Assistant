from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import Message
from app.models.document import Document, DocumentChunk
from app.models.model_call import ModelCallLog
from app.schemas.stats import StatsResponse


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)


def get_stats(db: Session, guest_remaining: int | None = None) -> StatsResponse:
    today = _start_of_today()

    document_count = db.scalar(select(func.count()).select_from(Document).where(Document.deleted_at.is_(None))) or 0
    ready_document_count = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.deleted_at.is_(None), Document.status == "ready")
        )
        or 0
    )
    chunk_count = db.scalar(select(func.count()).select_from(DocumentChunk)) or 0
    today_question_count = (
        db.scalar(select(func.count()).select_from(Message).where(Message.role == "user", Message.created_at >= today))
        or 0
    )
    today_refused_count = (
        db.scalar(
            select(func.count()).select_from(Message).where(Message.is_refused.is_(True), Message.created_at >= today)
        )
        or 0
    )
    today_model_call_count = (
        db.scalar(
            select(func.count())
            .select_from(ModelCallLog)
            .where(ModelCallLog.call_type == "chat", ModelCallLog.created_at >= today)
        )
        or 0
    )
    today_embedding_task_count = (
        db.scalar(
            select(func.count())
            .select_from(ModelCallLog)
            .where(ModelCallLog.call_type == "embedding", ModelCallLog.created_at >= today)
        )
        or 0
    )

    return StatsResponse(
        document_count=document_count,
        ready_document_count=ready_document_count,
        chunk_count=chunk_count,
        today_question_count=today_question_count,
        today_refused_count=today_refused_count,
        today_model_call_count=today_model_call_count,
        today_embedding_task_count=today_embedding_task_count,
        guest_remaining=guest_remaining if guest_remaining is not None else settings.guest_question_limit,
        guest_limit=settings.guest_question_limit,
    )

