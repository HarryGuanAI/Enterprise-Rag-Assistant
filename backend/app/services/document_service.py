import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.document import DocumentChunk
from app.rag.embeddings.dashscope_embedding import DashScopeEmbeddingClient
from app.rag.loaders.document_loader import load_document_text
from app.rag.splitters.hybrid_splitter import split_text
from app.services.knowledge_base_service import get_or_create_default_knowledge_base
from app.services.settings_service import get_or_create_settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


def list_active_documents(db: Session) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def mark_document_for_reprocess(db: Session, document_id: uuid.UUID) -> Document:
    """把已有文档重新放回待处理状态。

    常见场景是第一次上传时还没配置 Embedding Key，文档处理失败；用户补齐 Key 后，
    可以直接重试入库，不需要重新选择文件上传。
    """
    document = db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    document.status = "processing"
    document.error_message = None
    document.chunk_count = 0
    db.commit()
    db.refresh(document)
    return document


def _safe_filename(filename: str) -> str:
    """生成适合服务器保存的文件名片段。

    用户原始文件名仍会保存在数据库中，展示时不受影响。
    """
    stem = Path(filename).stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
    return safe or "document"


def _normalize_filename(filename: str) -> str:
    """修正常见的 multipart 中文文件名编码问题。

    某些 Windows 命令行工具上传中文文件名时，会把 UTF-8 字节按 latin-1 展示。
    浏览器上传通常正常；这里做兜底，避免文档列表出现乱码。
    """
    try:
        decoded = filename.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return filename
    return decoded if decoded else filename


async def create_document_from_upload(db: Session, file: UploadFile) -> Document:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名不能为空")

    original_filename = _normalize_filename(file.filename)
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 PDF、DOCX、Markdown 和 TXT 文件")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件大小不能超过 {settings.max_upload_mb}MB")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    date_prefix = datetime.now().strftime("%Y%m%d")
    stored_filename = f"{date_prefix}_{uuid.uuid4().hex[:12]}_{_safe_filename(original_filename)}{extension}"
    file_path = upload_dir / stored_filename
    file_path.write_bytes(content)

    knowledge_base = get_or_create_default_knowledge_base(db)
    document = Document(
        knowledge_base_id=knowledge_base.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_type=extension.removeprefix("."),
        file_size=len(content),
        status="processing",
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def process_document(document_id: str) -> None:
    """后台处理文档入库。

    当前阶段完成解析和混合分块，生成 `document_chunks`。
    下一阶段会在这里接入 DashScope Embedding，把向量写入 chunk.embedding。
    """
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:
            return

        try:
            document.status = "processing"
            document.error_message = None
            db.commit()

            app_settings = get_or_create_settings(db)
            text = load_document_text(document.file_path, document.file_type)
            drafts = split_text(text, app_settings.chunking)
            embeddings = DashScopeEmbeddingClient().embed_texts(db, [draft.content for draft in drafts]) if drafts else []

            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            for index, draft in enumerate(drafts):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        knowledge_base_id=document.knowledge_base_id,
                        chunk_index=index,
                        content=draft.content,
                        section_path=draft.section_path,
                        chunk_metadata=draft.metadata,
                        embedding=embeddings[index] if embeddings else None,
                    )
                )

            document.chunk_count = len(drafts)
            document.status = "ready"
            db.commit()
        except Exception as exc:  # noqa: BLE001 - 后台任务需要兜住异常并写入文档状态。
            document.status = "failed"
            document.error_message = str(exc)
            db.commit()
