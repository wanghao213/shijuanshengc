"""试卷管理服务."""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.paper import Paper, PaperQuestion
from app.models.question import Question

logger = structlog.get_logger()


class PaperService:
    """试卷管理业务逻辑."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_papers(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Paper], int]:
        """获取试卷列表."""
        count_stmt = select(func.count()).select_from(Paper)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(Paper)
            .options(selectinload(Paper.questions))
            .order_by(Paper.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        papers = list(result.scalars().all())
        return papers, total

    async def get_paper(self, paper_id: int) -> Paper:
        """获取单个试卷."""
        stmt = (
            select(Paper)
            .where(Paper.id == paper_id)
            .options(selectinload(Paper.questions))
        )
        result = await self.session.execute(stmt)
        paper = result.scalar_one_or_none()
        if not paper:
            raise NotFoundError("试卷", paper_id)
        return paper

    async def get_paper_detail(self, paper_id: int) -> dict | None:
        """获取试卷完整详情（含题目内容和分区信息）."""
        from app.models.paper_template import PaperTemplate

        stmt = (
            select(Paper)
            .where(Paper.id == paper_id)
            .options(
                selectinload(Paper.questions).joinedload(PaperQuestion.question),
                selectinload(Paper.template),
            )
        )
        result = await self.session.execute(stmt)
        paper = result.scalar_one_or_none()
        if not paper:
            return None

        sections: dict[int, list] = {}
        for pq in paper.questions:
            q = pq.question
            if q:
                q_data = {
                    "id": q.id,
                    "content_latex": q.content_latex,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "score": pq.assigned_score,
                    "answer_latex": q.answer_latex,
                    "options": q.options,
                }
                sections.setdefault(pq.section_index, []).append(q_data)

        section_names = []
        template = paper.template
        if template and template.structure:
            for s in template.structure.get("sections", []):
                section_names.append(s.get("name", ""))

        return {
            "id": paper.id,
            "title": paper.title,
            "total_score": paper.total_score,
            "sections": [
                {
                    "name": section_names[i] if i < len(section_names) else f"第{i+1}部分",
                    "questions": qs,
                }
                for i, qs in sorted(sections.items())
            ],
        }

    async def review_paper(self, paper_id: int, status: str) -> None:
        """审核试卷."""
        paper = await self.get_paper(paper_id)
        paper.review_status = status
        await self.session.flush()
        logger.info("paper_reviewed", paper_id=paper_id, status=status)

    async def delete_paper(self, paper_id: int) -> None:
        """删除试卷."""
        paper = await self.get_paper(paper_id)
        await self.session.delete(paper)
        await self.session.flush()
        logger.info("paper_deleted", paper_id=paper_id)
