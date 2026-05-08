"""题目管理端点."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.question import (
    QuestionBatchImport,
    QuestionCreate,
    QuestionRead,
    QuestionUpdate,
)
from app.services.embedding_service import EmbeddingService
from app.services.question_service import QuestionService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.get("/")
async def list_questions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    stage: str | None = None,
    grade: str | None = None,
    question_type: str | None = None,
    difficulty_min: float | None = None,
    difficulty_max: float | None = None,
    review_status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """获取题目列表."""
    service = QuestionService(db)
    questions, total = await service.list_questions(
        page=page,
        page_size=page_size,
        stage=stage,
        grade=grade,
        question_type=question_type,
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
        review_status=review_status,
    )
    return UnifiedResponse(
        data=[QuestionRead.model_validate(q) for q in questions],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/search")
async def search_questions(
    q: str = Query(..., min_length=1),
    mode: str = Query(default="keyword", pattern="^(keyword|semantic|hybrid)$"),
    question_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """搜索题目."""
    retrieval_svc = RetrievalService(db)

    filters = {}
    if question_type:
        filters["question_type"] = question_type

    if mode == "keyword":
        results = await retrieval_svc.fulltext_search(q, limit=limit)
    elif mode == "semantic":
        results = await retrieval_svc.semantic_search(q, top_k=limit)
    else:
        results = await retrieval_svc.hybrid_search(q, filters=filters, top_k=limit)

    return UnifiedResponse(data=results)


@router.get("/stats")
async def question_stats(
    db: AsyncSession = Depends(get_db),
):
    """题目统计."""
    from datetime import datetime

    from sqlalchemy import func, select

    from app.models.paper import Paper
    from app.models.question import Question

    service = QuestionService(db)
    stats = await service.get_statistics()

    # 补充 Dashboard 需要的额外统计
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_result = await db.execute(
        select(func.count())
        .select_from(Question)
        .where(Question.is_deleted == False, Question.created_at >= month_start)
    )
    stats["monthly_new"] = monthly_result.scalar() or 0

    papers_result = await db.execute(select(func.count()).select_from(Paper))
    stats["total_papers"] = papers_result.scalar() or 0

    total = stats.get("total", 0)
    ai_count = stats.get("ai_generated", 0)
    stats["ai_ratio"] = round(ai_count / total * 100, 1) if total > 0 else 0

    return UnifiedResponse(data=stats)


@router.get("/similar/{question_id}")
async def find_similar(
    question_id: int,
    threshold: float = Query(default=0.92, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """查找相似题目."""
    retrieval_svc = RetrievalService(db)
    results = await retrieval_svc.find_similar_questions(
        question_id=question_id, threshold=threshold, limit=limit
    )
    return UnifiedResponse(data=results)


@router.get("/{question_id}")
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单个题目."""
    service = QuestionService(db)
    question = await service.get_question(question_id)
    return UnifiedResponse(data=QuestionRead.model_validate(question))


@router.post("/")
async def create_question(
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建题目."""
    service = QuestionService(db)
    question = await service.create_question(data)
    # Refresh to load relationships
    await db.refresh(question, ["knowledge_points"])
    return UnifiedResponse(data=QuestionRead.model_validate(question))


@router.put("/{question_id}")
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新题目."""
    service = QuestionService(db)
    question = await service.update_question(question_id, data)
    return UnifiedResponse(data=QuestionRead.model_validate(question))


@router.delete("/{question_id}")
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除题目（软删除）."""
    service = QuestionService(db)
    question = await service.get_question(question_id)
    question.is_deleted = True
    await db.flush()
    return UnifiedResponse(message="删除成功")


@router.post("/batch-import")
async def batch_import(
    data: QuestionBatchImport,
    db: AsyncSession = Depends(get_db),
):
    """批量导入题目."""
    service = QuestionService(db)
    result = await service.batch_import(data.questions)
    return UnifiedResponse(data=result)


@router.post("/{question_id}/embedding")
async def generate_embedding(
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    """为单个题目生成 embedding."""
    embedding_svc = EmbeddingService(db)
    embedding = await embedding_svc.generate_embedding(question_id)
    if not embedding:
        return UnifiedResponse(code=500, message="Embedding 生成失败")
    return UnifiedResponse(message="Embedding 生成成功")


@router.post("/batch-embedding")
async def batch_embedding(
    question_ids: list[int],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """批量生成 embeddings（异步）."""
    embedding_svc = EmbeddingService(db)
    background_tasks.add_task(embedding_svc.batch_generate_embeddings, question_ids)
    return UnifiedResponse(
        data={"task": "batch_embedding", "count": len(question_ids)},
        message="批量 Embedding 任务已提交",
    )
