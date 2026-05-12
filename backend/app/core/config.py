from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。

    所有敏感信息都从环境变量读取，避免 API Key 或管理员密码出现在代码仓库中。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise RAG Assistant"
    app_env: str = "development"
    backend_cors_origins: str = "http://localhost:3000"

    admin_username: str = "admin"
    admin_password: str = "change-me-please"
    jwt_secret_key: str = "please-change-this-secret"
    jwt_expire_minutes: int = 720

    database_url: str = "postgresql+psycopg://rag_user:rag_password@localhost:5432/enterprise_rag"

    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    dashscope_api_key: str | None = None
    dashscope_embedding_model: str = "text-embedding-v4"
    dashscope_rerank_model: str = "gte-rerank-v2"

    upload_dir: str = "storage/uploads"
    max_upload_mb: int = 10
    guest_question_limit: int = Field(default=15, ge=1)
    guest_ip_daily_limit: int = Field(default=100, ge=1)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
