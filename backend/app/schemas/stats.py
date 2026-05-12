from pydantic import BaseModel


class StatsResponse(BaseModel):
    document_count: int = 0
    ready_document_count: int = 0
    chunk_count: int = 0
    today_question_count: int = 0
    today_refused_count: int = 0
    today_model_call_count: int = 0
    today_embedding_task_count: int = 0
    guest_remaining: int | None = None
    guest_limit: int | None = None

