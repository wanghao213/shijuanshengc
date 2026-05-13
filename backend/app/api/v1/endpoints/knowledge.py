"""知识点管理端点."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.knowledge import KnowledgeNode
from app.schemas.common import UnifiedResponse
from app.schemas.knowledge import KnowledgeNodeCreate, KnowledgeNodeRead, KnowledgeNodeUpdate
from app.services.knowledge_service import KnowledgeService

router = APIRouter()


@router.get("/tree")
async def get_knowledge_tree(
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """获取完整知识点树."""
    service = KnowledgeService(db)
    tree = await service.get_tree(stage=stage)
    return UnifiedResponse(
        data=[KnowledgeNodeRead.model_validate(node) for node in tree]
    )


@router.get("/tree/{node_id}")
async def get_subtree(
    node_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取指定节点及其子树."""
    service = KnowledgeService(db)
    
    # Eager-load the node with its children
    stmt = (
        select(KnowledgeNode)
        .where(KnowledgeNode.id == node_id)
        .options(selectinload(KnowledgeNode.children))
    )
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    
    if node is None:
        from app.exceptions import NotFoundError
        raise NotFoundError("知识点节点不存在")

    # Eager-load children with their own children in a single query
    stmt = (
        select(KnowledgeNode)
        .where(KnowledgeNode.parent_id == node_id)
        .options(selectinload(KnowledgeNode.children))
        .order_by(KnowledgeNode.sort_order)
    )
    result = await db.execute(stmt)
    children = list(result.scalars().all())

    return UnifiedResponse(
        data={
            "node": KnowledgeNodeRead.model_validate(node),
            "children": [KnowledgeNodeRead.model_validate(c) for c in children],
        }
    )


@router.post("/")
async def create_knowledge_node(
    data: KnowledgeNodeCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建知识点节点."""
    service = KnowledgeService(db)
    node = await service.create_node(
        name=data.name,
        level=data.level,
        parent_id=data.parent_id,
        stage=data.stage,
        grade=data.grade,
        description=data.description,
        sort_order=data.sort_order,
    )
    await db.refresh(node, ["children"])
    return UnifiedResponse(data=KnowledgeNodeRead.model_validate(node))


@router.put("/{node_id}")
async def update_knowledge_node(
    node_id: int,
    data: KnowledgeNodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新知识点节点."""
    service = KnowledgeService(db)
    node = await service.get_node(node_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(node, key, value)
    await db.flush()
    await db.refresh(node, ["children"])

    return UnifiedResponse(data=KnowledgeNodeRead.model_validate(node))


@router.delete("/{node_id}")
async def delete_knowledge_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除知识点节点."""
    service = KnowledgeService(db)
    node = await service.get_node(node_id)

    # 检查是否有子节点
    children = await service.get_children(node_id)
    if children:
        return UnifiedResponse(code=400, message="该节点下有子节点，无法删除")

    await db.delete(node)
    await db.flush()
    return UnifiedResponse(message="删除成功")
