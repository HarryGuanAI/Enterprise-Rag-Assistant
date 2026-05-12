import json
import time
from collections.abc import AsyncGenerator

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.model_call import ModelCallLog


class DeepSeekChatClient:
    """DeepSeek Chat Completions 流式适配器。

    DeepSeek 接口兼容 OpenAI Chat Completions，因此后续替换成 Qwen/OpenAI 时，
    主要改这个适配器即可，业务层不用跟着改。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.deepseek_api_key
        self.model = model or settings.deepseek_model

    async def stream_chat(
        self,
        db: Session,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key or self.api_key.startswith("your_"):
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 DeepSeek 生成回答")

        started_at = time.perf_counter()
        success = False
        error_message = None

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line.removeprefix("data: ").strip()
                        if data == "[DONE]":
                            break
                        delta = json.loads(data)["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
            success = True
        except Exception as exc:
            error_message = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            db.add(
                ModelCallLog(
                    provider="deepseek",
                    model_name=self.model,
                    call_type="chat",
                    success=success,
                    latency_ms=latency_ms,
                    error_message=error_message,
                )
            )
            db.commit()

