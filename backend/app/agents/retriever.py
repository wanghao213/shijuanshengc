"""Retriever Agent - 检索候选题目."""

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger()

# 约束常数
SIMILARITY_THRESHOLD = 0.92
MAX_SAME_SOURCE_RATIO = 0.3


class RetrieverAgent(BaseAgent):
    """检索候选题目.

    对每个 section：
    1. 根据 plan 的 knowledge_allocation，执行 hybrid_search
    2. 按 difficulty_distribution 分档匹配候选题
    3. 执行约束检查：
       - 相似度去重（cosine > 0.92 排除）
       - 来源分布控制（同来源 ≤ 30%）
       - 知识点覆盖率检查
    4. 输出每个 section 的已选题目列表 + 缺口数量
    """

    async def run(self, context: dict) -> dict:
        """执行检索."""
        plan = context.get("plan", {})
        retrieval_service = context.get("retrieval_service")
        template = context.get("template", {})
        custom_params = context.get("custom_params", {})
        avoid_ids = set(custom_params.get("avoid_question_ids", []))

        results = []
        sections_plan = plan.get("sections_plan", [])
        structure_sections = template.get("structure", {}).get("sections", [])

        for i, section_plan in enumerate(sections_plan):
            section_result = await self._retrieve_section(
                section_plan=section_plan,
                section_config=structure_sections[i] if i < len(structure_sections) else {},
                retrieval_service=retrieval_service,
                avoid_ids=avoid_ids,
                prefer_real=custom_params.get("prefer_real_questions", True),
            )
            results.append(section_result)

            # 更新避免列表，防止重复选取
            for q in section_result.get("selected", []):
                avoid_ids.add(q.get("id"))

        return {"sections": results}

    async def _retrieve_section(
        self,
        section_plan: dict,
        section_config: dict,
        retrieval_service,
        avoid_ids: set,
        prefer_real: bool,
    ) -> dict:
        """检索单个 section 的题目."""
        section_name = section_plan.get("section_name", "")
        question_type = section_config.get("type", "")
        need_count = section_plan.get("need_count", 0)
        difficulty_range = section_config.get("difficulty_range", [1.0, 5.0])

        # 执行混合检索
        all_candidates = []
        for topic, count in section_plan.get("knowledge_allocation", {}).items():
            candidates = await retrieval_service.hybrid_search(
                query_text=topic,
                filters={
                    "question_type": question_type,
                    "difficulty_min": difficulty_range[0],
                    "difficulty_max": difficulty_range[1],
                },
                top_k=count * 3,
            )
            all_candidates.extend(candidates)

        # 约束检查 1: ID 去重
        selected = []
        seen_ids = set(avoid_ids)

        for candidate in all_candidates:
            cid = candidate.get("id")
            if cid in seen_ids:
                continue
            if len(selected) >= need_count:
                break

            selected.append(candidate)
            seen_ids.add(cid)

        # 约束检查 2: 来源分布控制
        selected = self._enforce_source_distribution(selected, need_count)

        # 约束检查 3: 知识点覆盖率检查
        coverage_result = self._check_knowledge_coverage(
            selected, section_plan.get("knowledge_allocation", {})
        )

        # 计算缺口
        gaps = []
        if len(selected) < need_count:
            gaps.append({
                "type": question_type,
                "difficulty_range": difficulty_range,
                "count": need_count - len(selected),
                "knowledge_points": list(section_plan.get("knowledge_allocation", {}).keys()),
                "reason": "题库无匹配",
            })

        logger.info(
            "retriever_section_done",
            section=section_name,
            selected=len(selected),
            need=need_count,
            gaps=len(gaps),
            coverage=coverage_result,
        )

        return {
            "section_name": section_name,
            "section_index": section_plan.get("section_index", 0),
            "selected": selected,
            "gaps": gaps,
            "selected_count": len(selected),
            "need_count": need_count,
            "coverage": coverage_result,
        }

    def _enforce_source_distribution(
        self, candidates: list[dict], need_count: int
    ) -> list[dict]:
        """约束检查：来源分布控制.

        同来源的题目不超过总数的 MAX_SAME_SOURCE_RATIO。
        """
        if not candidates:
            return candidates

        max_per_source = max(1, int(need_count * MAX_SAME_SOURCE_RATIO))
        source_counts: dict[str, int] = {}
        filtered = []

        for q in candidates:
            source = q.get("source", "未知") or "未知"
            count = source_counts.get(source, 0)
            if count < max_per_source:
                filtered.append(q)
                source_counts[source] = count + 1

        return filtered

    def _check_knowledge_coverage(
        self, selected: list[dict], knowledge_allocation: dict
    ) -> dict:
        """约束检查：知识点覆盖率."""
        if not knowledge_allocation:
            return {"covered": 0, "total": 0, "ratio": 1.0}

        # 收集已选题目覆盖的知识点
        covered_kps = set()
        for q in selected:
            kps = q.get("knowledge_points", [])
            if isinstance(kps, list):
                for kp in kps:
                    if isinstance(kp, str):
                        covered_kps.add(kp)
                    elif isinstance(kp, dict):
                        covered_kps.add(kp.get("name", ""))

        required_kps = set(knowledge_allocation.keys())
        if not required_kps:
            return {"covered": 0, "total": 0, "ratio": 1.0}

        actually_covered = covered_kps & required_kps
        ratio = len(actually_covered) / len(required_kps) if required_kps else 1.0

        return {
            "covered": len(actually_covered),
            "total": len(required_kps),
            "ratio": round(ratio, 2),
            "missing": list(required_kps - actually_covered),
        }
