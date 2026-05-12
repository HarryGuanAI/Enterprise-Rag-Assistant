from fastapi import APIRouter, Header, Request
from sse_starlette.sse import EventSourceResponse

from app.schemas.chat import ChatStreamRequest
from app.services.chat_service import stream_chat_events

router = APIRouter()


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
