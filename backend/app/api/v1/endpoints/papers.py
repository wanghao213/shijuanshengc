"""试卷管理端点."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.paper import PaperRead, PaperReviewRequest
from app.services.export_service import ExportService
from app.services.paper_service import PaperService

router = APIRouter()


@router.get("/")
async def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取试卷列表."""
    service = PaperService(db)
    papers, total = await service.list_papers(page=page, page_size=page_size)
    return UnifiedResponse(
        data=[PaperRead.model_validate(p) for p in papers],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{paper_id}")
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取试卷详情."""
    service = PaperService(db)
    paper = await service.get_paper(paper_id)
    if not paper:
        return UnifiedResponse(code=404, message="试卷不存在")
    return UnifiedResponse(data=PaperRead.model_validate(paper))


@router.get("/{paper_id}/detail")
async def get_paper_detail(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取试卷完整详情（含题目内容和分区信息）."""
    service = PaperService(db)
    paper_data = await service.get_paper_detail(paper_id)
    if not paper_data:
        return UnifiedResponse(code=404, message="试卷不存在")
    return UnifiedResponse(data=paper_data)


@router.post("/{paper_id}/export")
async def export_paper(
    paper_id: int,
    format: str = "pdf",
    include_answers: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """导出试卷.

    format: latex | pdf | docx
    include_answers: 是否包含参考答案
    """
    service = PaperService(db)
    paper_data = await service.get_paper_detail(paper_id)
    if not paper_data:
        return UnifiedResponse(code=404, message="试卷不存在")

    export_service = ExportService()

    if format == "latex":
        content = await export_service.export_to_latex(paper_data, include_answers)
        return UnifiedResponse(data={"latex": content})

    if format == "pdf":
        pdf_bytes = await export_service.export_to_pdf_bytes(paper_data, include_answers)
        if pdf_bytes:
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="paper_{paper_id}.pdf"'
                },
            )
        return UnifiedResponse(code=500, message="PDF 导出失败（请确认系统已安装 xelatex）")

    if format == "docx":
        docx_bytes = await export_service.export_to_docx(paper_data, include_answers)
        if docx_bytes:
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="paper_{paper_id}.docx"'
                },
            )
        return UnifiedResponse(code=500, message="DOCX 导出失败")

    return UnifiedResponse(code=422, message=f"不支持的导出格式: {format}")


@router.put("/{paper_id}/review")
async def review_paper(
    paper_id: int,
    data: PaperReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """审核试卷."""
    service = PaperService(db)
    paper = await service.get_paper(paper_id)
    if not paper:
        return UnifiedResponse(code=404, message="试卷不存在")
    await service.review_paper(paper_id, data.status)
    return UnifiedResponse(message="审核完成")


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除试卷."""
    service = PaperService(db)
    await service.delete_paper(paper_id)
    return UnifiedResponse(message="删除成功")
