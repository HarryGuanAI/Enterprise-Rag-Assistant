import time

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.model_call import ModelCallLog

DASHSCOPE_COMPATIBLE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_DIMENSIONS = 1024
MAX_BATCH_SIZE = 10


class DashScopeEmbeddingClient:
    """DashScope text-embedding-v4 适配器。

    阿里云百炼 Embedding 模型兼容 OpenAI Embeddings 接口。
    第一版固定使用 1024 维，和 pgvector `vector(1024)` 对齐。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.dashscope_api_key
        self.model = model or settings.dashscope_embedding_model

    def embed_texts(self, db: Session, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key or self.api_key.startswith("your_"):
            raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法生成 Embedding")

        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[start : start + MAX_BATCH_SIZE]
            all_embeddings.extend(self._embed_batch(db, batch))
        return all_embeddings

    def _embed_batch(self, db: Session, texts: list[str]) -> list[list[float]]:
        started_at = time.perf_counter()
        success = False
        error_message = None

        try:
            response = httpx.post(
                f"{DASHSCOPE_COMPATIBLE_BASE_URL}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float",
                    "dimensions": EMBEDDING_DIMENSIONS,
                },
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
            embeddings = [item["embedding"] for item in data]
            if len(embeddings) != len(texts):
                raise RuntimeError("Embedding 返回数量与输入文本数量不一致")
            success = True
            return embeddings
        except Exception as exc:
            error_message = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            db.add(
                ModelCallLog(
                    provider="dashscope",
                    model_name=self.model,
                    call_type="embedding",
                    success=success,
                    latency_ms=latency_ms,
                    error_message=error_message,
                )
            )
            db.commit()

