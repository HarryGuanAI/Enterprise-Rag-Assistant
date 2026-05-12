from uuid import UUID

from pydantic import BaseModel, Field


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

