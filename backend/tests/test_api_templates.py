"""模板 API 集成测试."""

import pytest
from httpx import AsyncClient


def _template_data(**overrides):
    """构建模板创建数据."""
    data = {
        "name": "七年级期中考试",
        "stage": "初中",
        "grade": "七年级",
        "subject": "数学",
        "total_score": 100,
        "duration_minutes": 120,
        "structure": {
            "sections": [
                {
                    "name": "选择题",
                    "type": "choice",
                    "score": 40,
                    "count": 10,
                    "per_question_score": 4,
                    "difficulty_range": [1.0, 3.0],
                }
            ]
        },
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient):
    """测试获取模板列表."""
    response = await client.get("/api/v1/templates/")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert "meta" in data


@pytest.mark.asyncio
async def test_create_template(client: AsyncClient):
    """测试创建模板."""
    template_data = _template_data()
    response = await client.post("/api/v1/templates/", json=template_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == "七年级期中考试"
    assert data["data"]["total_score"] == 100
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_get_template(client: AsyncClient):
    """测试获取单个模板."""
    # 先创建
    template_data = _template_data(name="获取测试模板")
    create_resp = await client.post("/api/v1/templates/", json=template_data)
    template_id = create_resp.json()["data"]["id"]

    # 获取
    response = await client.get(f"/api/v1/templates/{template_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["id"] == template_id


@pytest.mark.asyncio
async def test_get_template_not_found(client: AsyncClient):
    """测试获取不存在的模板."""
    response = await client.get("/api/v1/templates/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_template(client: AsyncClient):
    """测试更新模板."""
    # 先创建
    template_data = _template_data(name="待更新模板")
    create_resp = await client.post("/api/v1/templates/", json=template_data)
    template_id = create_resp.json()["data"]["id"]

    # 更新
    update_data = {"name": "已更新模板", "total_score": 120}
    response = await client.put(f"/api/v1/templates/{template_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == "已更新模板"
    assert data["data"]["total_score"] == 120


@pytest.mark.asyncio
async def test_update_template_not_found(client: AsyncClient):
    """测试更新不存在的模板."""
    response = await client.put(
        "/api/v1/templates/99999",
        json={"name": "不存在"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_template(client: AsyncClient):
    """测试删除模板."""
    # 先创建
    template_data = _template_data(name="待删除模板")
    create_resp = await client.post("/api/v1/templates/", json=template_data)
    template_id = create_resp.json()["data"]["id"]

    # 删除
    response = await client.delete(f"/api/v1/templates/{template_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "删除成功"

    # 验证已删除
    get_resp = await client.get(f"/api/v1/templates/{template_id}")
    assert get_resp.json()["code"] == 404


@pytest.mark.asyncio
async def test_delete_template_not_found(client: AsyncClient):
    """测试删除不存在的模板."""
    response = await client.delete("/api/v1/templates/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_templates_pagination(client: AsyncClient):
    """测试模板列表分页."""
    # 创建多个模板
    for i in range(3):
        await client.post("/api/v1/templates/", json=_template_data(name=f"模板{i}"))

    response = await client.get("/api/v1/templates/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 2
