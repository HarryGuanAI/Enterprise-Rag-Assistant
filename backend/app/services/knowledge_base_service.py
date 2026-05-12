from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import KnowledgeBase


DEFAULT_KNOWLEDGE_BASE_NAME = "云舟科技企业知识库"


def get_or_create_default_knowledge_base(db: Session) -> KnowledgeBase:
    """获取默认知识库；不存在时自动创建。

    第一版页面只展示一个知识库，但数据模型预留了多知识库扩展。
    """
    knowledge_base = db.scalars(select(KnowledgeBase).where(KnowledgeBase.is_default.is_(True))).first()
    if knowledge_base is not None:
        return knowledge_base

    knowledge_base = KnowledgeBase(
        name=DEFAULT_KNOWLEDGE_BASE_NAME,
        description="云舟科技内部制度、IT 指南、产品 FAQ 与销售客服话术。",
        is_default=True,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base

