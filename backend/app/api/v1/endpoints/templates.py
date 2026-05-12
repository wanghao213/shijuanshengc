"""试卷模板管理端点."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.template import TemplateCreate, TemplateRead, TemplateUpdate
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("/")
async def list_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取模板列表."""
    service = TemplateService(db)
    templates, total = await service.list_templates(page=page, page_size=page_size)
    return UnifiedResponse(
        data=[TemplateRead.model_validate(t) for t in templates],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情."""
    service = TemplateService(db)
    template = await service.get_template(template_id)
    if not template:
        return UnifiedResponse(code=404, message="模板不存在")
    return UnifiedResponse(data=TemplateRead.model_validate(template))


@router.post("/")
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建模板."""
    service = TemplateService(db)
    template = await service.create_template(data)
    return UnifiedResponse(data=TemplateRead.model_validate(template))


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模板."""
    service = TemplateService(db)
    template = await service.update_template(template_id, data)
    if not template:
        return UnifiedResponse(code=404, message="模板不存在")
    return UnifiedResponse(data=TemplateRead.model_validate(template))


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除模板."""
    service = TemplateService(db)
    deleted = await service.delete_template(template_id)
    if not deleted:
        return UnifiedResponse(code=404, message="模板不存在")
    return UnifiedResponse(message="删除成功")


@router.post("/{template_id}/duplicate")
async def duplicate_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """复制模板."""
    service = TemplateService(db)
    template = await service.duplicate_template(template_id)
    return UnifiedResponse(data=TemplateRead.model_validate(template))
