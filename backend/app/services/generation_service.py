"""试卷生成服务 - 编排多 Agent 管线."""

import time
from collections.abc import Callable

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.assembler import AssemblerAgent
from app.agents.generator import GeneratorAgent
from app.agents.planner import PlannerAgent
from app.agents.retriever import RetrieverAgent
from app.agents.validator import ValidatorAgent
from app.models.generation_log import GenerationLog
from app.models.paper_template import PaperTemplate
from app.models.question import Question
from app.schemas.generation import GenerationRequest
from app.services.knowledge_service import KnowledgeService
from app.services.retrieval_service import RetrievalService
from app.services.validation_service import ValidationService

logger = structlog.get_logger()

# 管线阶段定义
PIPELINE_STAGES = [
    ("planning", "正在制定选题计划", 10.0, 25.0),
    ("retrieving", "正在检索候选题目", 30.0, 50.0),
    ("generating", "正在生成新题目", 55.0, 70.0),
    ("validating", "正在验证试卷质量", 75.0, 85.0),
    ("assembling", "正在组装试卷", 90.0, 100.0),
]


class GenerationService:
    """试卷生成服务，编排整个管线."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_task(self, task_id: int) -> GenerationLog | None:
        """获取任务状态."""
        return await self.session.get(GenerationLog, task_id)

    async def list_tasks(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[GenerationLog], int]:
        """获取任务列表."""
        count_stmt = select(func.count()).select_from(GenerationLog)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(GenerationLog)
            .order_by(GenerationLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        logs = list(result.scalars().all())
        return logs, total

    async def start_generation(self, request: GenerationRequest) -> GenerationLog:
        """开始生成任务."""
        log = GenerationLog(
            template_id=request.template_id,
            status="pending",
            current_step="等待开始",
            progress_pct=0.0,
        )
        self.session.add(log)
        await self.session.flush()

        logger.info("generation_started", log_id=log.id, template_id=request.template_id)
        return log

    async def update_progress(
        self,
        log_id: int,
        status: str,
        current_step: str,
        progress_pct: float,
    ) -> None:
        """更新生成进度."""
        log = await self.session.get(GenerationLog, log_id)
        if log:
            log.status = status
            log.current_step = current_step
            log.progress_pct = progress_pct
            await self.session.flush()

    async def complete_generation(
        self,
        log_id: int,
        paper_id: int,
        processing_time: float,
    ) -> None:
        """完成生成."""
        log = await self.session.get(GenerationLog, log_id)
        if log:
            log.status = "completed"
            log.paper_id = paper_id
            log.current_step = "生成完成"
            log.progress_pct = 100.0
            log.processing_time_seconds = processing_time
            await self.session.flush()

    async def fail_generation(self, log_id: int, error_message: str) -> None:
        """标记生成失败."""
        log = await self.session.get(GenerationLog, log_id)
        if log:
            log.status = "failed"
            log.error_message = error_message
            await self.session.flush()

    async def generate_paper(
        self,
        log_id: int,
        request: GenerationRequest,
        progress_callback: Callable | None = None,
    ) -> dict:
        """执行完整的试卷生成管线.

        按顺序调用 5 个 Agent：
        Planner → Retriever → Generator → Validator → Assembler

        Args:
            log_id: 生成日志 ID
            request: 生成请求
            progress_callback: 进度回调函数，签名 async (log_id, status, step, pct, detail=None)

        Returns:
            {"paper_id": int, "stats": dict} 或 {"error": str}
        """
        start_time = time.monotonic()

        try:
            # 加载模板
            template_obj = await self.session.get(PaperTemplate, request.template_id)
            if not template_obj:
                await self._fail_with_log(log_id, "模板不存在", progress_callback)
                return {"error": "模板不存在"}

            template = self._template_to_dict(template_obj)
            custom_params = request.custom_params.model_dump()

            # Phase 1: Planner
            plan = await self._run_planner(log_id, template, custom_params, progress_callback)

            # Phase 2: Retriever
            retrieval_result = await self._run_retriever(log_id, plan, template, custom_params, progress_callback)

            # Phase 3: Generator
            generation_result = await self._run_generator(log_id, retrieval_result, template, custom_params, progress_callback)

            # Phase 4: Validator
            validation_result = await self._run_validator(log_id, retrieval_result, generation_result, template, plan, progress_callback)

            # Phase 5: Assembler
            assembler_result = await self._run_assembler(log_id, retrieval_result, generation_result, template, custom_params, progress_callback)

            await self.session.commit()

            # 更新生成日志
            elapsed = time.monotonic() - start_time
            log = await self.session.get(GenerationLog, log_id)
            if log:
                log.status = "completed"
                log.current_step = "生成完成"
                log.progress_pct = 100.0
                log.paper_id = assembler_result.get("paper_id")
                log.processing_time_seconds = elapsed
                log.planner_output = plan
                log.retriever_output = retrieval_result
                log.generator_output = generation_result
                log.validator_output = validation_result
                await self.session.commit()

            if progress_callback:
                await progress_callback(log_id, "completed", "生成完成", 100.0, {
                    "paper_id": assembler_result.get("paper_id"),
                })

            logger.info(
                "generation_completed",
                log_id=log_id,
                paper_id=assembler_result.get("paper_id"),
                elapsed=elapsed,
            )

            return {
                "paper_id": assembler_result.get("paper_id"),
                "stats": assembler_result.get("stats", {}),
            }

        except Exception as e:
            logger.error("generation_failed", log_id=log_id, error=str(e), exc_info=True)
            await self._fail_with_log(log_id, str(e), progress_callback)
            return {"error": str(e)}

    async def _run_planner(
        self,
        log_id: int,
        template: dict,
        custom_params: dict,
        progress_callback: Callable | None,
    ) -> dict:
        """Phase 1: 制定选题计划."""
        await self._notify(log_id, "planning", "正在制定选题计划", 10.0, progress_callback)

        knowledge_svc = KnowledgeService(self.session)
        knowledge_tree = await knowledge_svc.get_tree()
        knowledge_dicts = _knowledge_to_dicts(knowledge_tree)

        # 获取题库统计
        stats_stmt = (
            select(Question.question_type, func.count())
            .where(Question.is_deleted == False, Question.review_status == "approved")
            .group_by(Question.question_type)
        )
        stats_result = await self.session.execute(stats_stmt)
        question_stats = {row[0]: row[1] for row in stats_result}

        planner = PlannerAgent(
            knowledge_tree=knowledge_dicts,
            question_stats=question_stats,
        )
        plan = await planner.run({
            "template": template,
            "custom_params": custom_params,
            "question_stats": question_stats,
            "knowledge_tree": knowledge_dicts,
        })

        await self._notify(log_id, "planning", "选题计划完成", 25.0, progress_callback, {
            "sections": len(plan.get("sections_plan", [])),
            "total_questions": plan.get("total_questions", 0),
        })

        return plan

    async def _run_retriever(
        self,
        log_id: int,
        plan: dict,
        template: dict,
        custom_params: dict,
        progress_callback: Callable | None,
    ) -> dict:
        """Phase 2: 检索候选题目."""
        await self._notify(log_id, "retrieving", "正在检索候选题目", 30.0, progress_callback)

        retrieval_svc = RetrievalService(self.session)
        retriever = RetrieverAgent()

        retrieval_result = await retriever.run({
            "plan": plan,
            "template": template,
            "custom_params": custom_params,
            "retrieval_service": retrieval_svc,
        })

        # 统计检索结果
        total_selected = sum(s.get("selected_count", 0) for s in retrieval_result.get("sections", []))
        total_gaps = sum(len(s.get("gaps", [])) for s in retrieval_result.get("sections", []))

        await self._notify(log_id, "retrieving", "题目检索完成", 50.0, progress_callback, {
            "total_selected": total_selected,
            "total_gaps": total_gaps,
        })

        return retrieval_result

    async def _run_generator(
        self,
        log_id: int,
        retrieval_result: dict,
        template: dict,
        custom_params: dict,
        progress_callback: Callable | None,
    ) -> dict:
        """Phase 3: 生成新题目."""
        await self._notify(log_id, "generating", "正在生成新题目", 55.0, progress_callback)

        retrieval_svc = RetrievalService(self.session)
        generator = GeneratorAgent()

        generation_result = await generator.run({
            "sections": retrieval_result.get("sections", []),
            "template": template,
            "custom_params": custom_params,
            "retrieval_service": retrieval_svc,
            "session": self.session,
        })

        gen_count = len(generation_result.get("generated_questions", []))
        await self._notify(log_id, "generating", "题目生成完成", 70.0, progress_callback, {
            "generated_count": gen_count,
        })

        return generation_result

    async def _run_validator(
        self,
        log_id: int,
        retrieval_result: dict,
        generation_result: dict,
        template: dict,
        plan: dict,
        progress_callback: Callable | None,
    ) -> dict:
        """Phase 4: 验证试卷质量."""
        await self._notify(log_id, "validating", "正在验证试卷质量", 75.0, progress_callback)

        validation_svc = ValidationService(self.session)
        validator = ValidatorAgent()

        # 收集所有题目
        all_questions = []
        for section in retrieval_result.get("sections", []):
            all_questions.extend(section.get("selected", []))
        all_questions.extend(generation_result.get("generated_questions", []))

        validation_result = await validator.run({
            "all_questions": all_questions,
            "template": template,
            "plan": plan,
            "validation_service": validation_svc,
        })

        issues_count = len(validation_result.get("issues", []))
        await self._notify(log_id, "validating", "质量验证完成", 85.0, progress_callback, {
            "total_questions": len(all_questions),
            "issues_count": issues_count,
            "is_valid": validation_result.get("is_valid", False),
        })

        return validation_result

    async def _run_assembler(
        self,
        log_id: int,
        retrieval_result: dict,
        generation_result: dict,
        template: dict,
        custom_params: dict,
        progress_callback: Callable | None,
    ) -> dict:
        """Phase 5: 组装试卷."""
        await self._notify(log_id, "assembling", "正在组装试卷", 90.0, progress_callback)

        assembler = AssemblerAgent()

        assembler_result = await assembler.run({
            "sections": retrieval_result.get("sections", []),
            "generated_questions": generation_result.get("generated_questions", []),
            "template": template,
            "custom_params": custom_params,
            "session": self.session,
            "generation_log_id": log_id,
        })

        return assembler_result

    async def _notify(
        self,
        log_id: int,
        status: str,
        step: str,
        pct: float,
        callback: Callable | None,
        detail: dict | None = None,
    ) -> None:
        """更新进度并通知回调."""
        log = await self.session.get(GenerationLog, log_id)
        if log:
            log.status = status
            log.current_step = step
            log.progress_pct = pct
            await self.session.flush()

        if callback:
            await callback(log_id, status, step, pct, detail)

    async def _fail_with_log(
        self,
        log_id: int,
        error: str,
        callback: Callable | None,
    ) -> None:
        """标记失败."""
        log = await self.session.get(GenerationLog, log_id)
        if log:
            log.status = "failed"
            log.error_message = error
            await self.session.commit()

        if callback:
            await callback(log_id, "failed", f"生成失败: {error}", 0.0)

    @staticmethod
    def _template_to_dict(template_obj: PaperTemplate) -> dict:
        """将模板 ORM 对象转为字典."""
        return {
            "id": template_obj.id,
            "name": template_obj.name,
            "stage": template_obj.stage,
            "grade": template_obj.grade,
            "subject": template_obj.subject,
            "total_score": template_obj.total_score,
            "duration_minutes": template_obj.duration_minutes,
            "structure": template_obj.structure,
        }


def _knowledge_to_dicts(nodes: list) -> list[dict]:
    """将知识点树转为字典列表（供 Planner Agent 使用）."""
    result = []
    for node in nodes:
        d = {
            "id": node.id,
            "name": node.name,
            "level": node.level,
            "stage": node.stage,
            "grade": node.grade,
            "description": node.description,
        }
        if node.children:
            d["children"] = _knowledge_to_dicts(node.children)
        result.append(d)
    return result
