from uuid import UUID

from pydantic import BaseModel, Field
from datetime import datetime


class ChatStreamRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    guest_id: str | None = Field(default=None, max_length=120)


class CitationResponse(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    section: str | None = None
    text: str
    score: float
    rank: int


class ConversationSummary(BaseModel):
    id: UUID
    title: str | None = None
    user_type: str
    guest_id: str | None = None
    message_count: int
    last_message_preview: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[dict] = []
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str | None = None
    messages: list[ChatMessageResponse]
