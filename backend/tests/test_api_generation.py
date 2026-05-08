"""试卷生成 API 集成测试."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.generation.run_generation_pipeline")
async def test_start_generation(mock_pipeline, client: AsyncClient):
    """测试发起生成任务."""
    # 先创建模板
    template_data = {
        "name": "生成测试模板",
        "stage": "初中",
        "grade": "七年级",
        "subject": "数学",
        "total_score": 100,
        "duration_minutes": 120,
        "structure": {"sections": []},
    }
    template_resp = await client.post("/api/v1/templates/", json=template_data)
    template_id = template_resp.json()["data"]["id"]

    # 发起生成
    request_data = {
        "template_id": template_id,
        "custom_params": {
            "difficulty_target": 3.0,
            "prefer_real_questions": True,
        },
    }
    response = await client.post("/api/v1/generation/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "task_id" in data["data"]
    assert data["data"]["status"] in ("pending", "planning")


@pytest.mark.asyncio
async def test_get_task_status(client: AsyncClient):
    """测试查询任务状态."""
    # 先创建一个任务
    template_data = {
        "name": "状态测试模板",
        "stage": "初中",
        "grade": "七年级",
        "subject": "数学",
        "total_score": 100,
        "duration_minutes": 120,
        "structure": {"sections": []},
    }
    template_resp = await client.post("/api/v1/templates/", json=template_data)
    template_id = template_resp.json()["data"]["id"]

    with patch("app.api.v1.endpoints.generation.run_generation_pipeline"):
        gen_resp = await client.post(
            "/api/v1/generation/generate",
            json={"template_id": template_id},
        )
    task_id = gen_resp.json()["data"]["task_id"]

    # 查询状态
    response = await client.get(f"/api/v1/generation/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["task_id"] == task_id


@pytest.mark.asyncio
async def test_get_task_status_not_found(client: AsyncClient):
    """测试查询不存在的任务."""
    response = await client.get("/api/v1/generation/tasks/99999")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient):
    """测试任务列表."""
    response = await client.get("/api/v1/generation/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert "meta" in data


@pytest.mark.asyncio
async def test_list_tasks_with_pagination(client: AsyncClient):
    """测试任务列表分页."""
    response = await client.get("/api/v1/generation/tasks?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 5
