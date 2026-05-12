"""试卷 API 集成测试."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.paper import Paper


def _template_data():
    """模板数据."""
    return {
        "name": "测试模板",
        "stage": "初中",
        "grade": "七年级",
        "subject": "数学",
        "total_score": 100,
        "duration_minutes": 120,
        "structure": {
            "sections": [
                {"name": "选择题", "type": "choice", "score": 40, "count": 10, "per_question_score": 4}
            ]
        },
    }


async def _create_template(client: AsyncClient) -> int:
    """创建模板并返回 ID."""
    resp = await client.post("/api/v1/templates/", json=_template_data())
    return resp.json()["data"]["id"]


async def _create_paper_in_db(client: AsyncClient, template_id: int, db_session) -> int:
    """直接在数据库中创建试卷."""
    paper = Paper(
        title="测试试卷",
        template_id=template_id,
        generation_params={},
        total_score=100,
        difficulty_average=3.0,
        knowledge_coverage={},
        review_status="draft",
    )
    db_session.add(paper)
    await db_session.flush()
    return paper.id


@pytest.mark.asyncio
async def test_list_papers(client: AsyncClient):
    """测试获取试卷列表."""
    response = await client.get("/api/v1/papers/")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert "meta" in data


@pytest.mark.asyncio
async def test_list_papers_empty(client: AsyncClient):
    """测试空试卷列表."""
    response = await client.get("/api/v1/papers/")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_paper(client: AsyncClient, db_session):
    """测试获取单个试卷."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    response = await client.get(f"/api/v1/papers/{paper_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["id"] == paper_id


@pytest.mark.asyncio
async def test_get_paper_not_found(client: AsyncClient):
    """测试获取不存在的试卷."""
    response = await client.get("/api/v1/papers/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_paper_detail(client: AsyncClient, db_session):
    """测试获取试卷详情."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    response = await client.get(f"/api/v1/papers/{paper_id}/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_get_paper_detail_not_found(client: AsyncClient):
    """测试获取不存在试卷的详情."""
    response = await client.get("/api/v1/papers/99999/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_export_paper_latex(client: AsyncClient, db_session):
    """测试导出 LaTeX."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    response = await client.post(f"/api/v1/papers/{paper_id}/export?format=latex")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "latex" in data["data"]


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.papers.ExportService")
async def test_export_paper_pdf(mock_export_cls, client: AsyncClient, db_session):
    """测试导出 PDF."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    mock_export = AsyncMock()
    mock_export.export_to_pdf_bytes = AsyncMock(return_value=b"%PDF-1.4 fake")
    mock_export_cls.return_value = mock_export

    response = await client.post(f"/api/v1/papers/{paper_id}/export?format=pdf")
    assert response.status_code == 200


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.papers.ExportService")
async def test_export_paper_docx(mock_export_cls, client: AsyncClient, db_session):
    """测试导出 DOCX."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    mock_export = AsyncMock()
    mock_export.export_to_docx = AsyncMock(return_value=b"PK fake docx")
    mock_export_cls.return_value = mock_export

    response = await client.post(f"/api/v1/papers/{paper_id}/export?format=docx")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_paper_not_found(client: AsyncClient):
    """测试导出不存在的试卷."""
    response = await client.post("/api/v1/papers/99999/export?format=latex")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_export_paper_unsupported_format(client: AsyncClient, db_session):
    """测试不支持的导出格式."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    response = await client.post(f"/api/v1/papers/{paper_id}/export?format=xyz")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 422


@pytest.mark.asyncio
async def test_review_paper(client: AsyncClient, db_session):
    """测试审核试卷."""
    template_id = await _create_template(client)
    paper_id = await _create_paper_in_db(client, template_id, db_session)
    await db_session.commit()

    response = await client.put(
        f"/api/v1/papers/{paper_id}/review",
        json={"status": "approved", "comment": "审核通过"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "审核完成"


@pytest.mark.asyncio
async def test_review_paper_not_found(client: AsyncClient):
    """测试审核不存在的试卷."""
    response = await client.put(
        "/api/v1/papers/99999/review",
        json={"status": "approved"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_papers_pagination(client: AsyncClient, db_session):
    """测试试卷列表分页."""
    template_id = await _create_template(client)

    # 创建多张试卷
    for i in range(3):
        paper = Paper(
            title=f"试卷{i}",
            template_id=template_id,
            generation_params={},
            total_score=100,
            difficulty_average=3.0,
            knowledge_coverage={},
        )
        db_session.add(paper)
    await db_session.commit()

    response = await client.get("/api/v1/papers/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 2
    assert data["meta"]["page"] == 1
