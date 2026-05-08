"""题目 API 测试."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_questions(client: AsyncClient):
    """测试获取题目列表."""
    response = await client.get("/api/v1/questions/")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data


@pytest.mark.asyncio
async def test_create_question(client: AsyncClient):
    """测试创建题目."""
    question_data = {
        "content_latex": "$x^2 + 1 = 0$",
        "content_plain": "x^2 + 1 = 0",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$x = 1$"},
                {"label": "B", "content_latex": "$x = -1$"},
                {"label": "C", "content_latex": "$x = i$"},
                {"label": "D", "content_latex": "无实数解"},
            ]
        },
        "answer_latex": "D",
        "review_status": "approved",
    }
    response = await client.post("/api/v1/questions/", json=question_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["question_type"] == "choice"


@pytest.mark.asyncio
async def test_get_question(client: AsyncClient):
    """测试获取单个题目."""
    # 先创建题目
    question_data = {
        "content_latex": "$a + b = c$",
        "content_plain": "a + b = c",
        "question_type": "fill_blank",
        "difficulty": 1.5,
    }
    create_response = await client.post("/api/v1/questions/", json=question_data)
    question_id = create_response.json()["data"]["id"]

    # 获取题目
    response = await client.get(f"/api/v1/questions/{question_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == question_id
