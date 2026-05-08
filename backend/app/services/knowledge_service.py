"""知识点服务."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.knowledge import KnowledgeNode


class KnowledgeService:
    """知识点业务逻辑."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tree(self, stage: str | None = None) -> list[KnowledgeNode]:
        """获取知识点树."""
        stmt = select(KnowledgeNode).where(KnowledgeNode.parent_id.is_(None))
        if stage:
            stmt = stmt.where(KnowledgeNode.stage == stage)
        stmt = stmt.options(selectinload(KnowledgeNode.children))
        stmt = stmt.order_by(KnowledgeNode.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_node(self, node_id: int) -> KnowledgeNode:
        """获取单个节点."""
        stmt = select(KnowledgeNode).where(KnowledgeNode.id == node_id)
        result = await self.session.execute(stmt)
        node = result.scalar_one_or_none()
        if not node:
            raise NotFoundError("知识点", node_id)
        return node

    async def create_node(
        self,
        name: str,
        level: str,
        parent_id: int | None = None,
        stage: str | None = None,
        grade: str | None = None,
        description: str | None = None,
        sort_order: int = 0,
    ) -> KnowledgeNode:
        """创建知识点节点.

        The materialized_path is automatically maintained by the ORM
        event handler in app.models.knowledge.
        """
        node = KnowledgeNode(
            name=name,
            level=level,
            parent_id=parent_id,
            stage=stage,
            grade=grade,
            description=description,
            materialized_path="",  # Temporary; set by ORM event after flush
            sort_order=sort_order,
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def get_children(self, node_id: int) -> list[KnowledgeNode]:
        """获取子节点."""
        stmt = (
            select(KnowledgeNode)
            .where(KnowledgeNode.parent_id == node_id)
            .order_by(KnowledgeNode.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
