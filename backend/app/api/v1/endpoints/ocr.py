"""OCR 文档识别端点."""

import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.ocr import OCRProcessRequest, OCRResultResponse
from app.services.ocr_service import OcrService

logger = structlog.get_logger()

router = APIRouter()


@router.post("/process")
async def process_text(
    data: OCRProcessRequest,
    db: AsyncSession = Depends(get_db),
):
    """手动输入模式：用户粘贴文本，LLM 结构化提取题目.

    当 MinerU 不可用时的降级方案。
    """
    service = OcrService(db)
    metadata = {
        "source": data.source,
        "source_year": data.source_year,
        "region": data.region,
        "exam_type": data.exam_type,
    }

    result = await service.process_and_save(
        raw_text=data.text,
        metadata=metadata,
        auto_tag=data.auto_tag,
    )

    response = OCRResultResponse(
        status=result.status,
        raw_text=result.raw_text,
        cleaned_text=result.cleaned_text,
        questions=[
            {
                "number": q.number,
                "content_latex": q.content_latex,
                "question_type": q.question_type,
                "options": q.options,
                "answer_latex": q.answer_latex,
                "knowledge_points": q.knowledge_points,
                "estimated_difficulty": q.estimated_difficulty,
            }
            for q in result.questions
        ],
        corrections=result.corrections,
        confidence=result.confidence,
        notes=result.notes,
        error=result.error,
        saved_question_ids=result.saved_question_ids,
    )

    return UnifiedResponse(data=response.model_dump())


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    source: str | None = Form(default=None),
    source_year: int | None = Form(default=None),
    region: str | None = Form(default=None),
    exam_type: str | None = Form(default=None),
    auto_tag: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
):
    """文件上传模式：上传 PDF/图片，MinerU OCR + LLM 清洗提取.

    如果 MinerU 不可用，返回错误提示用户使用手动输入模式。
    """
    # 验证文件类型
    allowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_suffixes:
        return UnifiedResponse(
            code=422,
            message=f"不支持的文件格式: {suffix}，支持: {', '.join(allowed_suffixes)}",
        )

    # 保存到临时目录
    upload_dir = Path(settings.upload_dir) / "ocr"
    upload_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / unique_name

    try:
        content = await file.read()
        file_path.write_bytes(content)

        service = OcrService(db)
        metadata = {
            "source": source,
            "source_year": source_year,
            "region": region,
            "exam_type": exam_type,
        }

        result = await service.process_and_save(
            file_path=str(file_path),
            metadata=metadata,
            auto_tag=auto_tag,
        )

        response = OCRResultResponse(
            status=result.status,
            raw_text=result.raw_text,
            cleaned_text=result.cleaned_text,
            questions=[
                {
                    "number": q.number,
                    "content_latex": q.content_latex,
                    "question_type": q.question_type,
                    "options": q.options,
                    "answer_latex": q.answer_latex,
                    "knowledge_points": q.knowledge_points,
                    "estimated_difficulty": q.estimated_difficulty,
                }
                for q in result.questions
            ],
            corrections=result.corrections,
            confidence=result.confidence,
            notes=result.notes,
            error=result.error,
            saved_question_ids=result.saved_question_ids,
        )

        return UnifiedResponse(data=response.model_dump())

    finally:
        # 清理上传文件
        if file_path.exists():
            file_path.unlink()
