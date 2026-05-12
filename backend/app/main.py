from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.bootstrap import bootstrap_database
from app.db.session import SessionLocal


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="企业知识库 RAG 助手后端 API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 确保上传目录存在。Docker 部署时该目录会挂载到宿主机，避免容器重启后文件丢失。
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    @app.on_event("startup")
    def startup() -> None:
        """应用启动时初始化默认知识库和 RAG 设置。

        Docker 启动时会先运行 Alembic 迁移，保证表结构存在后再执行这里。
        """
        with SessionLocal() as db:
            bootstrap_database(db)

    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
