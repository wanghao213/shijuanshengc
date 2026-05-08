"""OCR API 集成测试."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.ocr_service import ExtractedQuestion, OCRResult


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.ocr.OcrService")
async def test_process_text(mock_ocr_cls, client: AsyncClient):
    """测试手动输入模式处理."""
    mock_service = AsyncMock()
    mock_service.process_and_save = AsyncMock(
        return_value=OCRResult(
            status="success",
            raw_text="1. 计算 $1+1$",
            cleaned_text="1. 计算 1+1",
            questions=[
                ExtractedQuestion(
                    number="1",
                    content_latex="$1+1=2$",
                    question_type="short_answer",
                    answer_latex="2",
                    knowledge_points=["算术"],
                    estimated_difficulty=1.0,
                ),
            ],
            corrections=[],
            confidence=0.9,
            notes="",
            saved_question_ids=[1],
        )
    )
    mock_ocr_cls.return_value = mock_service

    request_data = {
        "text": "1. 计算 $1+1$ 的值。2. 解方程 $x+2=5$。",
        "source": "测试来源",
        "auto_tag": True,
    }
    response = await client.post("/api/v1/ocr/process", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["status"] == "success"
    assert len(data["data"]["questions"]) == 1
    assert data["data"]["confidence"] == 0.9


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.ocr.OcrService")
async def test_process_text_partial(mock_ocr_cls, client: AsyncClient):
    """测试部分识别结果."""
    mock_service = AsyncMock()
    mock_service.process_and_save = AsyncMock(
        return_value=OCRResult(
            status="partial",
            raw_text="模糊文本",
            cleaned_text="模糊文本",
            questions=[],
            corrections=[{"original": "模湖", "corrected": "模糊"}],
            confidence=0.4,
            notes="部分文本无法识别",
        )
    )
    mock_ocr_cls.return_value = mock_service

    request_data = {
        "text": "这是一段模糊的文本，难以识别。",
    }
    response = await client.post("/api/v1/ocr/process", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "partial"


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.ocr.OcrService")
async def test_process_text_failed(mock_ocr_cls, client: AsyncClient):
    """测试处理失败."""
    mock_service = AsyncMock()
    mock_service.process_and_save = AsyncMock(
        return_value=OCRResult(
            status="failed",
            error="处理失败",
        )
    )
    mock_ocr_cls.return_value = mock_service

    request_data = {"text": "测试文本内容，足够长以通过验证。"}
    response = await client.post("/api/v1/ocr/process", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "failed"


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.ocr.OcrService")
async def test_process_text_with_metadata(mock_ocr_cls, client: AsyncClient):
    """测试带元数据的处理."""
    mock_service = AsyncMock()
    mock_service.process_and_save = AsyncMock(
        return_value=OCRResult(status="success", questions=[])
    )
    mock_ocr_cls.return_value = mock_service

    request_data = {
        "text": "2024年中考数学真题，包含代数和几何内容。",
        "source": "2024年中考真题",
        "source_year": 2024,
        "region": "北京",
        "exam_type": "中考",
        "auto_tag": False,
    }
    response = await client.post("/api/v1/ocr/process", json=request_data)
    assert response.status_code == 200

    # 验证 metadata 传递
    call_kwargs = mock_service.process_and_save.call_args
    assert call_kwargs.kwargs["metadata"]["source"] == "2024年中考真题"
    assert call_kwargs.kwargs["metadata"]["source_year"] == 2024
