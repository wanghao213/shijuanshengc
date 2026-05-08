"""题目服务."""

import json

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.llm_gateway import structured_chat
from app.models.knowledge import KnowledgeNode
from app.models.question import Question, QuestionKnowledge, QuestionTag, QuestionVersion
from app.schemas.question import QuestionCreate, QuestionUpdate

logger = structlog.get_logger()


class QuestionService:
    """题目业务逻辑."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_questions(
        self,
        page: int = 1,
        page_size: int = 20,
        stage: str | None = None,
        grade: str | None = None,
        question_type: str | None = None,
        difficulty_min: float | None = None,
        difficulty_max: float | None = None,
        review_status: str | None = None,
    ) -> tuple[list[Question], int]:
        """获取题目列表."""
        stmt = select(Question).where(Question.is_deleted == False)

        if question_type:
            stmt = stmt.where(Question.question_type == question_type)
        if difficulty_min is not None:
            stmt = stmt.where(Question.difficulty >= difficulty_min)
        if difficulty_max is not None:
            stmt = stmt.where(Question.difficulty <= difficulty_max)
        if review_status:
            stmt = stmt.where(Question.review_status == review_status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.options(selectinload(Question.knowledge_points))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Question.id.desc())

        result = await self.session.execute(stmt)
        questions = list(result.scalars().all())
        return questions, total

    async def get_question(self, question_id: int) -> Question:
        """获取单个题目."""
        stmt = (
            select(Question)
            .where(Question.id == question_id, Question.is_deleted == False)
            .options(
                selectinload(Question.knowledge_points),
                selectinload(Question.versions),
                selectinload(Question.tags),
            )
        )
        result = await self.session.execute(stmt)
        question = result.scalar_one_or_none()
        if not question:
            raise NotFoundError("题目", question_id)
        return question

    async def create_question(self, data: QuestionCreate) -> Question:
        """创建题目."""
        question = Question(
            content_latex=data.content_latex,
            content_plain=data.content_plain,
            question_type=data.question_type,
            difficulty=data.difficulty,
            score=data.score,
            answer_latex=data.answer_latex,
            solution_steps=data.solution_steps,
            options=data.options,
            source=data.source,
            source_year=data.source_year,
            region=data.region,
            exam_type=data.exam_type,
            is_ai_generated=data.is_ai_generated,
            review_status=data.review_status,
        )
        self.session.add(question)
        await self.session.flush()

        for kid in data.knowledge_point_ids:
            assoc = QuestionKnowledge(question_id=question.id, knowledge_id=kid)
            self.session.add(assoc)

        version = QuestionVersion(
            question_id=question.id,
            version_number=1,
            content_latex=data.content_latex,
            answer_latex=data.answer_latex,
            solution_steps=data.solution_steps,
            change_reason="初始创建",
        )
        self.session.add(version)
        await self.session.flush()

        return question

    async def update_question(self, question_id: int, data: QuestionUpdate) -> Question:
        """更新题目（版本记录由 ORM 事件自动创建）."""
        question = await self.get_question(question_id)

        # 设置变更原因，供 ORM before_update 事件读取
        if data.change_reason:
            question._change_reason = data.change_reason

        update_data = data.model_dump(exclude_unset=True, exclude={"change_reason"})
        for key, value in update_data.items():
            setattr(question, key, value)

        await self.session.flush()
        return question

    async def batch_import(self, questions_data: list[QuestionCreate]) -> dict:
        """批量导入题目.

        Uses savepoints so that a single failed item doesn't roll back
        the entire batch.

        Returns:
            {"created": int, "failed": int, "errors": list[str]}
        """
        created = 0
        errors = []

        for i, data in enumerate(questions_data):
            # Use a savepoint per item so failures are isolated
            try:
                async with self.session.begin_nested():
                    await self.create_question(data)
                created += 1
            except Exception as e:
                # begin_nested() already rolled back the savepoint
                errors.append(f"第 {i + 1} 题导入失败: {str(e)}")
                logger.error("batch_import_error", index=i, error=str(e))

        logger.info("batch_import_complete", created=created, failed=len(errors))

        return {
            "created": created,
            "failed": len(errors),
            "errors": errors,
        }

    async def auto_tag(self, question_id: int) -> dict:
        """调用 AI 自动提取知识点和评估难度.

        Returns:
            {"knowledge_points": list[str], "difficulty": float, "tags": list[dict]}
        """
        question = await self.get_question(question_id)

        # 获取所有知识点供 AI 参考
        kp_result = await self.session.execute(
            select(KnowledgeNode.name).where(KnowledgeNode.level == "knowledge_point")
        )
        all_kps = [row[0] for row in kp_result]

        prompt = f"""你是一位数学教育专家，请分析以下数学题，提取考查的知识点并评估难度。

## 题目内容
{question.content_latex}

## 题型
{question.question_type}

## 可选知识点列表（从中选择，也可添加新的）
{', '.join(all_kps[:100])}

## 请输出 JSON 格式：
{{
  "knowledge_points": ["知识点1", "知识点2"],
  "difficulty": 3.5,
  "difficulty_reason": "难度评估理由",
  "tags": [
    {{"tag_type": "解题方法", "tag_value": "因式分解法"}},
    {{"tag_type": "核心素养", "tag_value": "逻辑推理"}}
  ]
}}"""

        messages = [{"role": "user", "content": prompt}]
        response = await structured_chat(messages=messages, session=self.session)

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            logger.error("auto_tag_parse_error", question_id=question_id)
            return {"knowledge_points": [], "difficulty": question.difficulty, "tags": []}

        # 更新难度
        new_difficulty = result.get("difficulty", question.difficulty)
        if 1.0 <= new_difficulty <= 5.0:
            question.difficulty = new_difficulty

        # 关联知识点
        kp_names = result.get("knowledge_points", [])
        for kp_name in kp_names:
            kp_node = await self.session.execute(
                select(KnowledgeNode).where(KnowledgeNode.name == kp_name)
            )
            kp = kp_node.scalar_one_or_none()
            if kp:
                existing = await self.session.execute(
                    select(QuestionKnowledge).where(
                        QuestionKnowledge.question_id == question_id,
                        QuestionKnowledge.knowledge_id == kp.id,
                    )
                )
                if not existing.scalar_one_or_none():
                    assoc = QuestionKnowledge(
                        question_id=question_id,
                        knowledge_id=kp.id,
                        relevance_score=0.8,
                        is_primary=False,
                    )
                    self.session.add(assoc)

        # 添加标签
        tags_data = result.get("tags", [])
        for tag in tags_data:
            qt = QuestionTag(
                question_id=question_id,
                tag_type=tag.get("tag_type", "其他"),
                tag_value=tag.get("tag_value", ""),
            )
            self.session.add(qt)

        await self.session.flush()

        return {
            "knowledge_points": kp_names,
            "difficulty": question.difficulty,
            "tags": tags_data,
        }

    async def get_statistics(self) -> dict:
        """多维统计."""
        # 总数
        total = await self.session.execute(
            select(func.count(Question.id)).where(Question.is_deleted == False)
        )
        total_count = total.scalar() or 0

        # 按题型统计
        type_stats = await self.session.execute(
            select(
                Question.question_type,
                func.count(Question.id).label("count"),
                func.avg(Question.difficulty).label("avg_difficulty"),
            )
            .where(Question.is_deleted == False)
            .group_by(Question.question_type)
        )
        by_type = {
            row.question_type: {
                "count": row.count,
                "avg_difficulty": round(row.avg_difficulty or 0, 2),
            }
            for row in type_stats
        }

        # 按审核状态统计
        status_stats = await self.session.execute(
            select(
                Question.review_status,
                func.count(Question.id).label("count"),
            )
            .where(Question.is_deleted == False)
            .group_by(Question.review_status)
        )
        by_status = {row.review_status: row.count for row in status_stats}

        # 按来源统计
        source_stats = await self.session.execute(
            select(
                Question.source,
                func.count(Question.id).label("count"),
            )
            .where(Question.is_deleted == False, Question.source.isnot(None))
            .group_by(Question.source)
            .order_by(func.count(Question.id).desc())
            .limit(20)
        )
        by_source = {row.source: row.count for row in source_stats}

        # 难度分布
        difficulty_stats = await self.session.execute(
            select(
                func.count(Question.id).label("count"),
                func.avg(Question.difficulty).label("avg"),
                func.min(Question.difficulty).label("min"),
                func.max(Question.difficulty).label("max"),
            ).where(Question.is_deleted == False)
        )
        diff_row = difficulty_stats.one()

        # AI 生成题目数
        ai_count = await self.session.execute(
            select(func.count(Question.id)).where(
                Question.is_deleted == False, Question.is_ai_generated == True
            )
        )
        ai_generated = ai_count.scalar() or 0

        return {
            "total": total_count,
            "by_type": by_type,
            "by_status": by_status,
            "by_source": by_source,
            "difficulty": {
                "average": round(diff_row.avg or 0, 2),
                "min": diff_row.min,
                "max": diff_row.max,
            },
            "ai_generated": ai_generated,
        }
