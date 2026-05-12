from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.schemas.document import DocumentListResponse, DocumentPreviewResponse, DocumentResponse
from app.services.document_service import (
    create_document_from_upload,
    get_document_preview,
    list_active_documents,
    mark_document_for_reprocess,
    process_document,
)

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    return DocumentListResponse(items=list_active_documents(db))


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
def preview_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentPreviewResponse:
    return get_document_preview(db, document_id)


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
) -> dict[str, str]:
    """管理员上传文档并创建入库记录。

    当前先完成“保存原始文件 + documents 记录”。下一阶段会在后台任务里接入解析、分块和 Embedding。
    """
    document = await create_document_from_upload(db, file)
    background_tasks.add_task(process_document, str(document.id))
    return {"status": document.status, "document_id": str(document.id), "filename": document.original_filename}


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
) -> DocumentResponse:
    document = mark_document_for_reprocess(db, document_id)
    background_tasks.add_task(process_document, str(document.id))
    return DocumentResponse.model_validate(document)
