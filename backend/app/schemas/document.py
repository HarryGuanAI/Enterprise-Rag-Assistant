from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


class DocumentPreviewChunk(BaseModel):
    id: UUID
    chunk_index: int
    section_path: str | None = None
    content: str
    start_offset: int | None = None
    end_offset: int | None = None

    model_config = {"from_attributes": True}


class DocumentPreviewResponse(BaseModel):
    id: UUID
    original_filename: str
    file_type: str
    status: str
    content: str
    chunks: list[DocumentPreviewChunk]
