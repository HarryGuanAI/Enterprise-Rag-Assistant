import json
import re
import time
from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
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
from app.schemas.chat import (
    ChatMessageResponse,
    ChatStreamRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
)
from app.services.knowledge_base_service import get_or_create_default_knowledge_base
from app.services.settings_service import get_or_create_settings


REFUSAL_TEXT = "我没有在当前知识库中检索到足够可靠的依据，因此不能直接回答这个问题。你可以补充相关制度文档后再提问。"
CAPABILITY_TEXT = (
    "我可以作为企业知识库 RAG 助手帮你做这些事：\n\n"
    "- **基于已入库文档回答问题**：例如 HR 制度、报销流程、IT 服务、产品 FAQ、客服工单、销售合同和数据安全规范。\n"
    "- **给出引用来源**：回答后会展示命中的文档片段、相似度分数，并支持打开全文预览定位到引用 chunk。\n"
    "- **多轮追问**：在同一个对话里，我会结合最近上下文理解“那这个呢”“上一条呢”这类问题。\n"
    "- **严格拒答**：如果知识库里没有可靠依据，我会明确说明不能回答，避免编造。\n"
    "- **管理员能力**：登录后可以上传 PDF、DOCX、Markdown、TXT，重新入库文档，并调整 TopK、相似度阈值、Hybrid Search 和 Rerank。"
)
MAX_HISTORY_MESSAGES = 8
_ASCII_WORD_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}")
_CJK_TEXT_RE = re.compile(r"[\u4e00-\u9fff]+")
_QUESTION_STOP_TERMS = {
    "什么",
    "哪些",
    "怎么",
    "如何",
    "是否",
    "可以",
    "需要",
    "的是",
    "一个",
    "一下",
    "多少",
    "多久",
}
_DOMAIN_SUPPORT_TERMS = {
    "入职",
    "转正",
    "离职",
    "试用期",
    "考勤",
    "补卡",
    "远程",
    "外勤",
    "年假",
    "病假",
    "婚假",
    "调休",
    "报销",
    "差旅",
    "住宿",
    "餐补",
    "发票",
    "审批",
    "招待",
    "礼品",
    "合同",
    "报价",
    "折扣",
    "用印",
    "回款",
    "采购",
    "供应商",
    "付款",
    "预付款",
    "黑名单",
    "工单",
    "客服",
    "响应",
    "研发",
    "日志",
    "发布",
    "故障",
    "复盘",
    "灰度",
    "回滚",
    "数据",
    "权限",
    "密钥",
    "脱敏",
    "薪酬",
    "绩效",
    "工资",
    "奖金",
    "福利",
    "培训",
    "预算",
    "格式",
    "文档",
    "引用",
    "游客",
    "管理员",
}


def sse_event(event: str, data: dict) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def stream_chat_events(
    payload: ChatStreamRequest,
    *,
    client_host: str | None,
    authorization: str | None,
) -> AsyncGenerator[dict[str, str], None]:
    return _stream_chat_events(payload, client_host=client_host, authorization=authorization)


def list_conversations(
    db: Session,
    *,
    authorization: str | None,
    guest_id: str | None,
) -> ConversationListResponse:
    user_type = _resolve_user_type(authorization)
    stmt = select(Conversation).order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
    if user_type == "guest":
        if not guest_id:
            return ConversationListResponse(items=[])
        stmt = stmt.where(Conversation.user_type == "guest", Conversation.guest_id == guest_id)

    conversations = list(db.scalars(stmt.limit(50)).all())
    items: list[ConversationSummary] = []
    for conversation in conversations:
        message_count = db.scalar(
            select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
        ) or 0
        last_message = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        ).first()
        items.append(
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                user_type=conversation.user_type,
                guest_id=conversation.guest_id,
                message_count=int(message_count),
                last_message_preview=last_message.content[:120] if last_message else None,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
        )
    return ConversationListResponse(items=items)


def get_conversation_detail(
    db: Session,
    *,
    conversation_id: UUID,
    authorization: str | None,
    guest_id: str | None,
) -> ConversationDetailResponse:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError("会话不存在")

    user_type = _resolve_user_type(authorization)
    if user_type == "guest" and (conversation.user_type != "guest" or conversation.guest_id != guest_id):
        raise ValueError("无权访问该会话")

    messages = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        messages=[
            ChatMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                citations=message.citations_json or [],
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


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
            capability_answer = CAPABILITY_TEXT if _is_capability_question(payload.question) else None
            yield sse_event(
                "status",
                {"message": "已识别为能力咨询，正在直接生成说明..." if capability_answer else "正在读取 RAG 配置..."},
            )
            knowledge_base = get_or_create_default_knowledge_base(db)
            conversation = _get_or_create_conversation(
                db,
                knowledge_base_id=knowledge_base.id,
                conversation_id=payload.conversation_id,
                user_type=user_type,
                guest_id=guest_id,
                question=payload.question,
            )
            history_messages = _load_recent_messages(db, conversation.id)
            retrieval_query, used_history_for_retrieval = _build_retrieval_query(payload.question, history_messages)

            if not capability_answer and user_type == "guest":
                limit_error = _check_and_increase_guest_usage(db, guest_id=guest_id, client_host=client_host)
                if limit_error:
                    yield sse_event("error", {"message": limit_error})
                    yield sse_event("done", {"message_id": None, "conversation_id": str(conversation.id)})
                    return

            user_message = Message(conversation_id=conversation.id, role="user", content=payload.question)
            db.add(user_message)
            conversation.updated_at = datetime.now(timezone.utc)
            db.commit()

            if capability_answer:
                assistant_message = _save_direct_assistant_message(
                    db,
                    conversation_id=conversation.id,
                    content=capability_answer,
                    model_name="intent-router",
                    started_at=started_at,
                )
                yield sse_event("answer_delta", {"content": capability_answer})
                yield sse_event("citations", {"citations": []})
                yield sse_event("done", {"message_id": str(assistant_message.id), "conversation_id": str(conversation.id)})
                return

            app_settings = get_or_create_settings(db)
            yield sse_event("status", {"message": "正在生成问题向量..."})
            query_embedding = DashScopeEmbeddingClient().embed_texts(db, [retrieval_query])[0]

            yield sse_event("status", {"message": "正在检索知识库..."})
            retriever = PgVectorRetriever()
            retrieved_chunks = retriever.search(
                db,
                knowledge_base_id=knowledge_base.id,
                query_embedding=query_embedding,
                query_text=retrieval_query,
                top_k=app_settings.retrieval.top_k,
                enable_hybrid_search=app_settings.retrieval.enable_hybrid_search,
                enable_rerank=app_settings.retrieval.enable_rerank,
            )

            best_score = retrieved_chunks[0].score if retrieved_chunks else 0.0
            current_question_supported = _has_current_question_support(
                payload.question,
                retrieved_chunks,
                used_history_for_retrieval=used_history_for_retrieval,
            )
            should_refuse = app_settings.retrieval.strict_refusal and (
                best_score < app_settings.retrieval.min_similarity or not current_question_supported
            )
            refusal_reason = _retrieval_refusal_reason(
                best_score=best_score,
                min_similarity=app_settings.retrieval.min_similarity,
                current_question_supported=current_question_supported,
            )
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
                    "used_history_for_retrieval": used_history_for_retrieval,
                    "current_question_supported": current_question_supported,
                    "reason": refusal_reason
                    if should_refuse
                    else f"Top1 相似度 {best_score:.4f} 达到阈值，且命中片段能支撑当前问题，将调用生成模型。",
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
                user_prompt=_build_user_prompt(payload.question, retrieved_chunks, history_messages),
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
            if user_type == "guest" and (conversation.user_type != "guest" or conversation.guest_id != guest_id):
                raise ValueError("无权访问该会话")
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


def _load_recent_messages(db: Session, conversation_id: UUID) -> list[Message]:
    messages = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(MAX_HISTORY_MESSAGES)
        ).all()
    )
    return list(reversed(messages))


def _build_retrieval_query(question: str, history_messages: list[Message]) -> tuple[str, bool]:
    if not history_messages or not _is_contextual_followup(question):
        return question, False

    history_lines = [
        f"{'用户' if message.role == 'user' else '助手'}：{message.content[:300]}"
        for message in history_messages[-4:]
    ]
    return "历史对话：\n" + "\n".join(history_lines) + "\n\n当前问题：\n" + question, True


def _is_contextual_followup(question: str) -> bool:
    normalized = _normalize_question(question)
    contextual_markers = (
        "那",
        "这个",
        "那个",
        "它",
        "其",
        "上述",
        "上面",
        "前面",
        "刚才",
        "上一",
        "下一",
        "继续",
        "还有",
        "同样",
        "呢",
        "再说",
        "再讲",
    )
    if any(marker in normalized for marker in contextual_markers):
        return True
    # “P1 呢？”、“第二条？”这类短追问常依赖上一轮主题。
    return len(normalized) <= 12 and bool(re.search(r"(p[0-9]|第[一二三四五六七八九十0-9]+|[0-9]+)$", normalized))


def _has_current_question_support(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    used_history_for_retrieval: bool,
) -> bool:
    if not chunks:
        return False
    if used_history_for_retrieval:
        return True

    terms = _extract_question_terms(question)
    if not terms:
        return True

    haystack = "\n".join(f"{chunk.title}\n{chunk.section or ''}\n{chunk.content}" for chunk in chunks).lower()
    if any(term in haystack for term in terms):
        return True

    # 兜底处理“薪酬绩效”和“绩效薪酬”这类中文词序变化：
    # 连续 n-gram 可能因为顺序不同未命中，但制度领域关键词已经共同出现时，应认为候选片段可支撑当前问题。
    domain_terms = [term for term in _DOMAIN_SUPPORT_TERMS if term in question and term in haystack]
    if len(domain_terms) >= 2:
        return True
    return len(domain_terms) == 1 and len(terms) <= 3


def _retrieval_refusal_reason(
    *,
    best_score: float,
    min_similarity: float,
    current_question_supported: bool,
) -> str:
    if best_score < min_similarity:
        return f"Top1 相似度 {best_score:.4f} 低于阈值 {min_similarity:.2f}，严格拒答生效。"
    if not current_question_supported:
        return "虽然历史上下文或向量召回给出了候选片段，但命中内容不能支撑当前问题，严格拒答生效。"
    return f"Top1 相似度 {best_score:.4f} 低于阈值 {min_similarity:.2f}，严格拒答生效。"


def _normalize_question(question: str) -> str:
    return (
        question.lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("？", "?")
        .replace("，", ",")
        .replace("。", ".")
        .replace("！", "!")
    )


def _extract_question_terms(question: str) -> list[str]:
    normalized = _normalize_question(question)
    terms: list[str] = []
    terms.extend(match.group(0) for match in _ASCII_WORD_RE.finditer(normalized))

    for match in _CJK_TEXT_RE.finditer(normalized):
        phrase = match.group(0)
        if 2 <= len(phrase) <= 12 and phrase not in _QUESTION_STOP_TERMS:
            terms.append(phrase)
        for size in (4, 3, 2):
            if len(phrase) < size:
                continue
            for index in range(0, len(phrase) - size + 1):
                gram = phrase[index : index + size]
                if gram in _QUESTION_STOP_TERMS:
                    continue
                terms.append(gram)

    deduped: list[str] = []
    seen: set[str] = set()
    for term in sorted(terms, key=lambda item: (-len(item), item)):
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
        if len(deduped) >= 12:
            break
    return deduped


def _is_capability_question(question: str) -> bool:
    normalized = (
        question.lower()
        .replace(" ", "")
        .replace("？", "?")
        .replace("，", ",")
        .replace("。", ".")
        .replace("！", "!")
    )
    capability_patterns = (
        "你能做什么",
        "你可以做什么",
        "你会做什么",
        "你有什么功能",
        "你有哪些功能",
        "你能干什么",
        "你可以干什么",
        "怎么使用你",
        "怎么用你",
        "如何使用你",
        "你是谁",
        "介绍一下你",
        "介绍下你",
        "使用说明",
        "功能介绍",
        "能帮我做什么",
        "可以帮我做什么",
        "你支持什么",
        "你支持哪些",
        "whatcanyoudo",
        "whatdoyoudo",
        "help",
    )
    return any(pattern in normalized for pattern in capability_patterns)


def _save_direct_assistant_message(
    db: Session,
    *,
    conversation_id: UUID,
    content: str,
    model_name: str,
    started_at: float,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        citations_json=[],
        retrieval_score=None,
        is_refused=False,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        model_name=model_name,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


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


def _build_user_prompt(question: str, chunks: list[RetrievedChunk], history_messages: list[Message]) -> str:
    context_blocks = []
    for chunk in chunks:
        section = f" / 章节：{chunk.section}" if chunk.section else ""
        context_blocks.append(
            f"[来源 {chunk.rank}] 文档：{chunk.title}{section}\n"
            f"相似度：{chunk.score:.4f}\n"
            f"内容：{chunk.content}"
        )

    history_block = ""
    if history_messages:
        history_lines = [
            f"{'用户' if message.role == 'user' else '助手'}：{message.content}"
            for message in history_messages[-MAX_HISTORY_MESSAGES:]
        ]
        history_block = "【最近对话】\n" + "\n".join(history_lines) + "\n\n"

    return (
        "请结合最近对话理解当前问题，但事实依据必须来自知识库片段。\n\n"
        + history_block
        + "【知识库片段】\n"
        + "\n\n".join(context_blocks)
        + "\n\n【用户问题】\n"
        + question
    )
