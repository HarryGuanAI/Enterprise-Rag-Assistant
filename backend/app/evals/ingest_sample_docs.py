"""导入 sample_docs 目录下的示例知识库文档。

这个脚本用于本地演示和评测准备：它会把示例 Markdown/TXT/PDF/DOCX 文件复制到上传目录，
创建或更新 documents 记录，然后复用正式入库流程完成解析、分块和 Embedding。
"""

from __future__ import annotations

import argparse
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.document_service import ALLOWED_EXTENSIONS, process_document
from app.services.knowledge_base_service import get_or_create_default_knowledge_base


def ingest_sample_docs(sample_dir: Path) -> list[str]:
    if not sample_dir.exists():
        raise FileNotFoundError(f"Sample docs directory not found: {sample_dir}")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    processed: list[str] = []
    with SessionLocal() as db:
        knowledge_base = get_or_create_default_knowledge_base(db)
        files = sorted(path for path in sample_dir.iterdir() if path.suffix.lower() in ALLOWED_EXTENSIONS)

        for source_path in files:
            original_filename = source_path.name
            stored_filename = f"{datetime.now():%Y%m%d}_{uuid.uuid4().hex[:12]}_{source_path.stem}{source_path.suffix}"
            target_path = upload_dir / stored_filename
            shutil.copyfile(source_path, target_path)

            document = db.scalars(
                select(Document).where(
                    Document.knowledge_base_id == knowledge_base.id,
                    Document.original_filename == original_filename,
                    Document.deleted_at.is_(None),
                )
            ).first()

            if document is None:
                document = Document(
                    knowledge_base_id=knowledge_base.id,
                    original_filename=original_filename,
                    stored_filename=stored_filename,
                    file_path=str(target_path),
                    file_type=source_path.suffix.lower().removeprefix("."),
                    file_size=source_path.stat().st_size,
                    status="processing",
                    chunk_count=0,
                )
                db.add(document)
            else:
                document.stored_filename = stored_filename
                document.file_path = str(target_path)
                document.file_type = source_path.suffix.lower().removeprefix(".")
                document.file_size = source_path.stat().st_size
                document.status = "processing"
                document.error_message = None

            db.commit()
            db.refresh(document)
            process_document(str(document.id))
            processed.append(original_filename)

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest sample_docs into the default knowledge base.")
    parser.add_argument(
        "--sample-dir",
        default="/app/sample_docs",
        help="Directory containing sample knowledge documents.",
    )
    args = parser.parse_args()

    processed = ingest_sample_docs(Path(args.sample_dir))
    print(f"Ingested {len(processed)} sample docs:")
    for filename in processed:
        print(f"- {filename}")


if __name__ == "__main__":
    main()
