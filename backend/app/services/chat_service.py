import json
import time
from collections.abc import AsyncGenerator
from datetime import date
from uuid import UUID

from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.chat import Conversation, Message, MessageCitation
from app.models.guest import GuestUsage
from app.rag.embeddings.dashscope_embedding import DashScopeEmbeddingClient
from app.rag.generators.deepseek_generator import DeepSeekChatClient
from app.rag.retrievers.vector_retriever import RetrievedChunk, PgVectorRetriever
from app.schemas.chat import ChatStreamRequest
from app.services.knowledge_base_service import get_or_create_default_knowledge_base
from app.services.settings_service import get_or_create_settings


REFUSAL_TEXT = "我没有在当前知识库中检索到足够可靠的依据，因此不能直接回答这个问题。你可以补充相关制度文档后再提问。"


def sse_event(event: str, data: dict) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def stream_chat_events(
    payload: ChatStreamRequest,
    *,
    client_host: str | None,
    authorization: str | None,
) -> AsyncGenerator[dict[str, str], None]:
    return _stream_chat_events(payload, client_host=client_host, authorization=authorization)


async def _stream_chat_events(
    payload: ChatStreamRequest,
    *,
    client_host: str | None,
    authorization: str | None,
) -> AsyncGenerator[dict[str, str], None]:
    started_at = time.perf_counter()

    with SessionLocal() as db:
        try:
            user_type = _resolve_user_type(authorization)
            guest_id = None if user_type == "admin" else (payload.guest_id or "anonymous")

            if user_type == "guest":
                limit_error = _check_and_increase_guest_usage(db, guest_id=guest_id, client_host=client_host)
                if limit_error:
                    yield sse_event("error", {"message": limit_error})
                    yield sse_event("done", {"message_id": None})
                    return

            yield sse_event("status", {"message": "正在读取 RAG 配置..."})
            app_settings = get_or_create_settings(db)
            knowledge_base = get_or_create_default_knowledge_base(db)
            conversation = _get_or_create_conversation(
                db,
                knowledge_base_id=knowledge_base.id,
                conversation_id=payload.conversation_id,
                user_type=user_type,
                guest_id=guest_id,
                question=payload.question,
            )

            user_message = Message(conversation_id=conversation.id, role="user", content=payload.question)
            db.add(user_message)
            db.commit()

            yield sse_event("status", {"message": "正在生成问题向量..."})
            query_embedding = DashScopeEmbeddingClient().embed_texts(db, [payload.question])[0]

            yield sse_event("status", {"message": "正在检索知识库..."})
            retriever = PgVectorRetriever()
            retrieved_chunks = retriever.search(
                db,
                knowledge_base_id=knowledge_base.id,
                query_embedding=query_embedding,
                query_text=payload.question,
                top_k=app_settings.retrieval.top_k,
                enable_hybrid_search=app_settings.retrieval.enable_hybrid_search,
                enable_rerank=app_settings.retrieval.enable_rerank,
            )

            best_score = retrieved_chunks[0].score if retrieved_chunks else 0.0
            should_refuse = app_settings.retrieval.strict_refusal and best_score < app_settings.retrieval.min_similarity
            yield sse_event(
                "retrieval_debug",
                {
                    "top_k": app_settings.retrieval.top_k,
                    "min_similarity": app_settings.retrieval.min_similarity,
                    "strict_refusal": app_settings.retrieval.strict_refusal,
                    "enable_hybrid_search": app_settings.retrieval.enable_hybrid_search,
                    "enable_rerank": app_settings.retrieval.enable_rerank,
                    "retrieval_mode": retriever.last_stats.mode,
                    "vector_candidates": retriever.last_stats.vector_candidates,
                    "keyword_candidates": retriever.last_stats.keyword_candidates,
                    "fused_candidates": retriever.last_stats.fused_candidates,
                    "embedding_model": settings.dashscope_embedding_model,
                    "generation_model": settings.deepseek_model,
                    "best_score": round(best_score, 4),
                    "refused": should_refuse,
                    "will_call_llm": not should_refuse,
                    "reason": (
                        f"Top1 相似度 {best_score:.4f} 低于阈值 {app_settings.retrieval.min_similarity:.2f}，严格拒答生效。"
                        if should_refuse
                        else f"Top1 相似度 {best_score:.4f} 达到阈值，将调用生成模型。"
                    ),
                },
            )
            if should_refuse:
                assistant_message = _save_assistant_message(
                    db,
                    conversation_id=conversation.id,
                    content=REFUSAL_TEXT,
                    chunks=[],
                    is_refused=True,
                    retrieval_score=best_score,
                    started_at=started_at,
                )
                yield sse_event("answer_delta", {"content": REFUSAL_TEXT})
                yield sse_event("citations", {"citations": []})
                yield sse_event("done", {"message_id": str(assistant_message.id), "conversation_id": str(conversation.id)})
                return

            citations = [_citation_payload(chunk) for chunk in retrieved_chunks]
            yield sse_event("citations", {"citations": citations})
            yield sse_event("status", {"message": "正在调用 DeepSeek 生成回答..."})

            answer_parts: list[str] = []
            async for delta in DeepSeekChatClient().stream_chat(
                db,
                system_prompt=_build_system_prompt(),
                user_prompt=_build_user_prompt(payload.question, retrieved_chunks),
                temperature=app_settings.generation.temperature,
                max_tokens=app_settings.generation.max_tokens,
            ):
                answer_parts.append(delta)
                yield sse_event("answer_delta", {"content": delta})

            assistant_message = _save_assistant_message(
                db,
                conversation_id=conversation.id,
                content="".join(answer_parts),
                chunks=retrieved_chunks,
                is_refused=False,
                retrieval_score=best_score,
                started_at=started_at,
            )
            yield sse_event("done", {"message_id": str(assistant_message.id), "conversation_id": str(conversation.id)})
        except Exception as exc:
            yield sse_event("error", {"message": str(exc)})
            yield sse_event("done", {"message_id": None})


def _resolve_user_type(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return "guest"

    token = authorization.removeprefix("Bearer ").strip()
    try:
        subject = decode_access_token(token)
    except JWTError:
        return "guest"
    return "admin" if subject == settings.admin_username else "guest"


def _check_and_increase_guest_usage(db: Session, *, guest_id: str, client_host: str | None) -> str | None:
    today = date.today()
    usage = db.scalars(select(GuestUsage).where(GuestUsage.guest_id == guest_id, GuestUsage.usage_date == today)).first()
    if usage and usage.question_count >= settings.guest_question_limit:
        return f"游客模式每天只能提问 {settings.guest_question_limit} 次，请登录管理员账号后继续使用。"

    ip_count = (
        db.scalar(
            select(func.coalesce(func.sum(GuestUsage.question_count), 0)).where(
                GuestUsage.ip_address == client_host,
                GuestUsage.usage_date == today,
            )
        )
        or 0
    )
    if client_host and int(ip_count) >= settings.guest_ip_daily_limit:
        return "当前 IP 今日游客提问次数已达上限，请登录管理员账号后继续使用。"

    if usage is None:
        usage = GuestUsage(guest_id=guest_id, ip_address=client_host, usage_date=today, question_count=0)
        db.add(usage)
    usage.question_count += 1
    db.commit()
    return None


def _get_or_create_conversation(
    db: Session,
    *,
    knowledge_base_id: UUID,
    conversation_id: UUID | None,
    user_type: str,
    guest_id: str | None,
    question: str,
) -> Conversation:
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation:
            return conversation

    conversation = Conversation(
        knowledge_base_id=knowledge_base_id,
        user_type=user_type,
        guest_id=guest_id,
        title=question[:80],
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _save_assistant_message(
    db: Session,
    *,
    conversation_id: UUID,
    content: str,
    chunks: list[RetrievedChunk],
    is_refused: bool,
    retrieval_score: float,
    started_at: float,
) -> Message:
    citations = [_citation_payload(chunk) for chunk in chunks]
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        citations_json=citations,
        retrieval_score=retrieval_score,
        is_refused=is_refused,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        model_name=settings.deepseek_model,
    )
    db.add(message)
    db.flush()

    for chunk in chunks:
        db.add(
            MessageCitation(
                message_id=message.id,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                rank=chunk.rank,
                score=chunk.score,
                citation_snapshot=_citation_payload(chunk),
            )
        )
    db.commit()
    db.refresh(message)
    return message


def _citation_payload(chunk: RetrievedChunk) -> dict:
    return {
        "document_id": str(chunk.document_id),
        "chunk_id": str(chunk.chunk_id),
        "title": chunk.title,
        "section": chunk.section,
        "text": chunk.content[:500],
        "score": round(chunk.score, 4),
        "vector_score": round(chunk.vector_score, 4),
        "keyword_score": round(chunk.keyword_score, 4),
        "source": chunk.source,
        "rank": chunk.rank,
    }


def _build_system_prompt() -> str:
    return (
        "你是企业内部知识库 RAG 助手。"
        "你必须只依据用户问题下方提供的知识库片段回答。"
        "如果片段不足以支持结论，要明确说明知识库依据不足。"
        "回答要简洁、准确，并尽量指出来自哪些制度或章节。"
    )


def _build_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_blocks = []
    for chunk in chunks:
        section = f" / 章节：{chunk.section}" if chunk.section else ""
        context_blocks.append(
            f"[来源 {chunk.rank}] 文档：{chunk.title}{section}\n"
            f"相似度：{chunk.score:.4f}\n"
            f"内容：{chunk.content}"
        )

    return (
        "请根据以下知识库片段回答问题。\n\n"
        "【知识库片段】\n"
        + "\n\n".join(context_blocks)
        + "\n\n【用户问题】\n"
        + question
    )
