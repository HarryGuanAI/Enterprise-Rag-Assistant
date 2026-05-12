from sqlalchemy.orm import Session

from app.services.knowledge_base_service import get_or_create_default_knowledge_base
from app.services.settings_service import get_or_create_settings


def bootstrap_database(db: Session) -> None:
    """初始化运行所需的基础数据。

    当前只创建默认知识库和默认 RAG 设置；真实业务数据仍通过上传文档生成。
    """
    get_or_create_default_knowledge_base(db)
    get_or_create_settings(db)

