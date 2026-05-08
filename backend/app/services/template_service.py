"""试卷模板服务."""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.paper_template import PaperTemplate
from app.schemas.template import TemplateCreate, TemplateUpdate

logger = structlog.get_logger()


class TemplateService:
    """试卷模板业务逻辑."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_templates(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[PaperTemplate], int]:
        """获取模板列表."""
        count_stmt = select(func.count()).select_from(PaperTemplate)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(PaperTemplate)
            .order_by(PaperTemplate.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        templates = list(result.scalars().all())
        return templates, total

    async def get_template(self, template_id: int) -> PaperTemplate:
        """获取单个模板."""
        template = await self.session.get(PaperTemplate, template_id)
        if not template:
            raise NotFoundError("模板", template_id)
        return template

    async def create_template(self, data: TemplateCreate) -> PaperTemplate:
        """创建模板."""
        template = PaperTemplate(**data.model_dump())
        self.session.add(template)
        await self.session.flush()
        logger.info("template_created", template_id=template.id)
        return template

    async def update_template(
        self, template_id: int, data: TemplateUpdate
    ) -> PaperTemplate:
        """更新模板."""
        template = await self.get_template(template_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)
        await self.session.flush()
        logger.info("template_updated", template_id=template_id)
        return template

    async def delete_template(self, template_id: int) -> None:
        """删除模板."""
        template = await self.get_template(template_id)
        await self.session.delete(template)
        await self.session.flush()
        logger.info("template_deleted", template_id=template_id)

    async def duplicate_template(self, template_id: int) -> PaperTemplate:
        """复制模板."""
        original = await self.get_template(template_id)
        new_template = PaperTemplate(
            name=f"{original.name} (副本)",
            stage=original.stage,
            grade=original.grade,
            subject=original.subject,
            total_score=original.total_score,
            duration_minutes=original.duration_minutes,
            structure=original.structure,
            is_default=False,
            description=original.description,
        )
        self.session.add(new_template)
        await self.session.flush()
        logger.info("template_duplicated", original_id=template_id, new_id=new_template.id)
        return new_template
