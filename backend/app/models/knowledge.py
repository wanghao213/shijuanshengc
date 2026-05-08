"""知识点树模型."""

from sqlalchemy import ForeignKey, Index, String, Text, event, inspect, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class KnowledgeNode(TimestampMixin, Base):
    """知识点节点."""

    __tablename__ = "knowledge_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_nodes.id"), nullable=True
    )
    level: Mapped[str] = mapped_column(String(50))  # 'stage'/'grade'/'chapter'/'section'/'knowledge_point'
    name: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str | None] = mapped_column(String(20))  # '小学'/'初中'/'高中'
    grade: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    materialized_path: Mapped[str] = mapped_column(String(500))  # "1/5/12/34"
    sort_order: Mapped[int] = mapped_column(default=0)

    # 关系
    parent: Mapped["KnowledgeNode | None"] = relationship(
        back_populates="children", remote_side=[id]
    )
    children: Mapped[list["KnowledgeNode"]] = relationship(
        back_populates="parent", order_by="KnowledgeNode.sort_order"
    )
    questions: Mapped[list["Question"]] = relationship(
        secondary="question_knowledge", back_populates="knowledge_points"
    )

    # 索引
    __table_args__ = (
        Index("ix_knowledge_path", "materialized_path"),
        Index("ix_knowledge_stage_grade", "stage", "grade"),
    )


# ---------------------------------------------------------------------------
# materialized_path 自动维护
# ---------------------------------------------------------------------------

# 标记需要在 flush 后更新 materialized_path 的实例
_pending_path_updates: set[int] = set()


def _get_parent_path(session: Session, parent_id: int | None) -> str:
    """获取父节点的 materialized_path."""
    if parent_id is None:
        return ""
    parent = session.get(KnowledgeNode, parent_id)
    if parent is not None:
        return parent.materialized_path or str(parent.id)
    # 父节点不在 identity_map 中，从数据库查询
    result = session.execute(
        select(KnowledgeNode.materialized_path).where(KnowledgeNode.id == parent_id)
    )
    row = result.scalar_one_or_none()
    return row or str(parent_id)


@event.listens_for(KnowledgeNode, "after_insert")
def _on_knowledge_node_insert(mapper, connection, target):
    """插入后标记需要更新 materialized_path."""
    _pending_path_updates.add(id(target))


@event.listens_for(KnowledgeNode, "after_update")
def _on_knowledge_node_update(mapper, connection, target):
    """parent_id 变更后标记需要更新 materialized_path."""
    state = inspect(target)
    history = state.attrs.parent_id.history
    if history.has_changes():
        _pending_path_updates.add(id(target))


@event.listens_for(Session, "after_flush_postexec")
def _update_materialized_paths(session, flush_context):
    """flush 完成后，为新插入或移动的节点计算 materialized_path 并级联更新子节点."""
    if not _pending_path_updates:
        return

    to_update = [
        obj for obj in session.new if id(obj) in _pending_path_updates
    ] + [
        obj for obj in session.dirty if id(obj) in _pending_path_updates
    ]
    _pending_path_updates.clear()

    for node in to_update:
        if not isinstance(node, KnowledgeNode):
            continue
        parent_path = _get_parent_path(session, node.parent_id)
        new_path = f"{parent_path}/{node.id}" if parent_path else str(node.id)
        object.__setattr__(node, "materialized_path", new_path)
        # 级联更新子节点
        _cascade_path_update(session, node.id, new_path)


def _cascade_path_update(session: Session, parent_id: int, parent_path: str) -> None:
    """级联更新子节点的 materialized_path."""
    children = session.execute(
        select(KnowledgeNode).where(KnowledgeNode.parent_id == parent_id)
    ).scalars().all()
    for child in children:
        child_path = f"{parent_path}/{child.id}"
        object.__setattr__(child, "materialized_path", child_path)
        _cascade_path_update(session, child.id, child_path)
