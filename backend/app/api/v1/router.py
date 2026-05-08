"""API v1 路由汇总."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    generation,
    knowledge,
    ocr,
    papers,
    questions,
    templates,
)

api_router = APIRouter()

api_router.include_router(questions.router, prefix="/questions", tags=["题目管理"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识点"])
api_router.include_router(templates.router, prefix="/templates", tags=["试卷模板"])
api_router.include_router(generation.router, prefix="/generation", tags=["试卷生成"])
api_router.include_router(papers.router, prefix="/papers", tags=["试卷管理"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["OCR识别"])
