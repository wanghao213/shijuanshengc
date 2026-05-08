"""知识点模式."""

from pydantic import BaseModel, Field


class KnowledgeNodeBase(BaseModel):
    """知识点基础字段."""

    name: str = Field(max_length=200)
    level: str  # 'stage'/'grade'/'chapter'/'section'/'knowledge_point'
    stage: str | None = None
    grade: str | None = None
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0


class KnowledgeNodeCreate(KnowledgeNodeBase):
    """创建知识点."""

    pass


class KnowledgeNodeUpdate(BaseModel):
    """更新知识点."""

    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    sort_order: int | None = None


class KnowledgeNodeRead(KnowledgeNodeBase):
    """知识点响应."""

    id: int
    materialized_path: str
    children: list["KnowledgeNodeRead"] = []

    model_config = {"from_attributes": True}
