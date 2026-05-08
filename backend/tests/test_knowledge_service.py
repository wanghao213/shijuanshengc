"""KnowledgeService 单元测试."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.services.knowledge_service import KnowledgeService


def _make_mock_node(**kwargs):
    """创建 mock KnowledgeNode."""
    node = MagicMock()
    node.id = kwargs.get("id", 1)
    node.name = kwargs.get("name", "代数")
    node.level = kwargs.get("level", "chapter")
    node.parent_id = kwargs.get("parent_id")
    node.stage = kwargs.get("stage", "初中")
    node.grade = kwargs.get("grade", "七年级")
    node.description = kwargs.get("description", "")
    node.materialized_path = kwargs.get("materialized_path", "1")
    node.sort_order = kwargs.get("sort_order", 0)
    node.children = kwargs.get("children", [])
    return node


@pytest.mark.asyncio
async def test_get_tree_empty():
    """测试空知识点树."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    tree = await svc.get_tree()

    assert tree == []


@pytest.mark.asyncio
async def test_get_tree_with_nodes():
    """测试有数据的知识点树."""
    session = AsyncMock()
    node1 = _make_mock_node(id=1, name="代数")
    node2 = _make_mock_node(id=2, name="几何")

    result = MagicMock()
    result.scalars.return_value.all.return_value = [node1, node2]
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    tree = await svc.get_tree()

    assert len(tree) == 2


@pytest.mark.asyncio
async def test_get_tree_with_stage_filter():
    """测试按学段过滤."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [_make_mock_node(stage="初中")]
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    tree = await svc.get_tree(stage="初中")

    assert len(tree) == 1


@pytest.mark.asyncio
async def test_get_node_found():
    """测试获取存在的节点."""
    session = AsyncMock()
    mock_node = _make_mock_node(id=42, name="方程")
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_node
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    node = await svc.get_node(42)

    assert node.id == 42
    assert node.name == "方程"


@pytest.mark.asyncio
async def test_get_node_not_found():
    """测试获取不存在的节点."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    with pytest.raises(NotFoundError):
        await svc.get_node(999)


@pytest.mark.asyncio
async def test_create_node_root():
    """测试创建根节点."""
    session = AsyncMock()

    created_node = None

    def capture_add(obj):
        nonlocal created_node
        created_node = obj
        obj.id = 1

    session.add = MagicMock(side_effect=capture_add)
    session.flush = AsyncMock()

    svc = KnowledgeService(session)
    await svc.create_node(
        name="代数",
        level="chapter",
        stage="初中",
        sort_order=1,
    )

    session.add.assert_called_once()
    assert session.flush.call_count == 2  # initial flush + path update flush


@pytest.mark.asyncio
async def test_create_node_with_parent():
    """测试创建子节点."""
    session = AsyncMock()

    # mock parent node lookup
    parent = _make_mock_node(id=5, materialized_path="1/5")
    parent_result = MagicMock()
    parent_result.scalar_one_or_none.return_value = parent

    session.execute = AsyncMock(return_value=parent_result)

    created_node = None

    def capture_add(obj):
        nonlocal created_node
        created_node = obj
        obj.id = 6

    session.add = MagicMock(side_effect=capture_add)
    session.flush = AsyncMock()

    svc = KnowledgeService(session)
    await svc.create_node(
        name="一元一次方程",
        level="knowledge_point",
        parent_id=5,
    )

    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_children():
    """测试获取子节点."""
    session = AsyncMock()
    child1 = _make_mock_node(id=2, name="子节点1")
    child2 = _make_mock_node(id=3, name="子节点2")

    result = MagicMock()
    result.scalars.return_value.all.return_value = [child1, child2]
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    children = await svc.get_children(1)

    assert len(children) == 2


@pytest.mark.asyncio
async def test_get_children_empty():
    """测试获取空子节点."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)

    svc = KnowledgeService(session)
    children = await svc.get_children(1)

    assert children == []
