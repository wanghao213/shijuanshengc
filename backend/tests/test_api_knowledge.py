"""知识点 API 集成测试."""

import pytest
from httpx import AsyncClient


def _node_data(**overrides):
    """构建知识点创建数据."""
    data = {
        "name": "代数",
        "level": "chapter",
        "stage": "初中",
        "grade": "七年级",
        "description": "代数基础知识",
        "sort_order": 1,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_get_knowledge_tree(client: AsyncClient):
    """测试获取知识点树."""
    response = await client.get("/api/v1/knowledge/tree")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_knowledge_tree_with_stage(client: AsyncClient):
    """测试按学段获取知识点树."""
    # 先创建一个节点
    await client.post("/api/v1/knowledge/", json=_node_data(stage="初中"))

    response = await client.get("/api/v1/knowledge/tree?stage=初中")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_create_knowledge_node(client: AsyncClient):
    """测试创建知识点节点."""
    node_data = _node_data()
    response = await client.post("/api/v1/knowledge/", json=node_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == "代数"
    assert data["data"]["level"] == "chapter"
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_create_knowledge_child_node(client: AsyncClient):
    """测试创建子知识点节点."""
    # 先创建父节点
    parent_data = _node_data(name="代数", level="chapter")
    parent_resp = await client.post("/api/v1/knowledge/", json=parent_data)
    parent_id = parent_resp.json()["data"]["id"]

    # 创建子节点
    child_data = _node_data(name="一元一次方程", level="knowledge_point", parent_id=parent_id)
    child_resp = await client.post("/api/v1/knowledge/", json=child_data)
    assert child_resp.status_code == 200
    assert child_resp.json()["data"]["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_get_subtree(client: AsyncClient):
    """测试获取子树."""
    # 创建父节点
    parent_resp = await client.post("/api/v1/knowledge/", json=_node_data(name="几何", level="chapter"))
    parent_id = parent_resp.json()["data"]["id"]

    # 创建子节点
    await client.post(
        "/api/v1/knowledge/",
        json=_node_data(name="三角形", level="section", parent_id=parent_id),
    )

    # 获取子树
    response = await client.get(f"/api/v1/knowledge/tree/{parent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["node"]["id"] == parent_id
    assert isinstance(data["data"]["children"], list)


@pytest.mark.asyncio
async def test_update_knowledge_node(client: AsyncClient):
    """测试更新知识点节点."""
    # 创建
    create_resp = await client.post("/api/v1/knowledge/", json=_node_data())
    node_id = create_resp.json()["data"]["id"]

    # 更新
    update_data = {"name": "更新后代数", "description": "更新后的描述"}
    response = await client.put(f"/api/v1/knowledge/{node_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == "更新后代数"


@pytest.mark.asyncio
async def test_delete_knowledge_node(client: AsyncClient):
    """测试删除知识点节点."""
    # 创建
    create_resp = await client.post("/api/v1/knowledge/", json=_node_data(name="待删除"))
    node_id = create_resp.json()["data"]["id"]

    # 删除
    response = await client.delete(f"/api/v1/knowledge/{node_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "删除成功"


@pytest.mark.asyncio
async def test_delete_knowledge_node_with_children(client: AsyncClient):
    """测试删除有子节点的知识点."""
    # 创建父节点
    parent_resp = await client.post("/api/v1/knowledge/", json=_node_data(name="父节点"))
    parent_id = parent_resp.json()["data"]["id"]

    # 创建子节点
    await client.post(
        "/api/v1/knowledge/",
        json=_node_data(name="子节点", parent_id=parent_id),
    )

    # 尝试删除父节点（应该失败）
    response = await client.delete(f"/api/v1/knowledge/{parent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 400
    assert "子节点" in data["message"]
