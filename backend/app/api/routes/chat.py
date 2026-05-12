from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db.session import get_db
from app.schemas.chat import ChatStreamRequest, ConversationDetailResponse, ConversationListResponse
from app.services.chat_service import get_conversation_detail, list_conversations, stream_chat_events

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
def conversations(
    guest_id: str | None = Query(default=None, max_length=120),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return list_conversations(db, authorization=authorization, guest_id=guest_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def conversation_detail(
    conversation_id: UUID,
    guest_id: str | None = Query(default=None, max_length=120),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    try:
        return get_conversation_detail(
            db,
            conversation_id=conversation_id,
            authorization=authorization,
            guest_id=guest_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> EventSourceResponse:
    client_host = request.client.host if request.client else None
    return EventSourceResponse(
        stream_chat_events(payload, client_host=client_host, authorization=authorization),
        ping=15,
    )
