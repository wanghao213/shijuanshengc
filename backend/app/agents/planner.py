"""Planner Agent - 制定选题计划."""

import json
import re
from typing import Any

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger()

# 计划中每个 section 必须包含的字段
_REQUIRED_SECTION_FIELDS = {"section_name", "section_index", "need_count"}
_REQUIRED_PLAN_FIELDS = {"sections_plan", "total_questions"}


class PlannerAgent(BaseAgent):
    """制定试卷生成计划.

    通过 tool_use 让 AI 调用工具获取知识点树和题库统计信息，
    然后制定详细的选题计划。

    工具：
    - query_knowledge_tree: 查询知识点结构
    - query_question_stats: 查询题库统计
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_knowledge_tree",
                "description": "查询指定学段和年级的知识点树结构，返回知识点层级和名称",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "string",
                            "description": "学段，如 '小学'、'初中'、'高中'",
                        },
                        "grade": {
                            "type": "string",
                            "description": "年级，如 '初一'、'初二'、'高一'",
                        },
                    },
                    "required": ["stage"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_question_stats",
                "description": "查询题库中各题型的题目数量和难度分布统计",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "string",
                            "description": "学段筛选",
                        },
                        "grade": {
                            "type": "string",
                            "description": "年级筛选",
                        },
                        "question_type": {
                            "type": "string",
                            "description": "题型筛选：choice/fill_blank/short_answer/proof/comprehensive",
                        },
                    },
                },
            },
        },
    ]

    SYSTEM_PROMPT = """你是一位资深数学教育专家和命题规划师。
你的任务是根据试卷模板和用户需求，制定详细的选题计划。

你可以使用以下工具获取信息：
1. query_knowledge_tree: 查询知识点树结构，了解可用的知识点
2. query_question_stats: 查询题库统计，了解各题型的题目数量

你需要考虑：
1. 各大题的题目数量和分值分配
2. 难度分布（由易到难，合理梯度）
3. 知识点覆盖要求
4. 题库现有题目情况 vs 需要AI生成的题目数量

请先使用工具获取必要的信息，然后返回严格 JSON 格式的选题计划。"""

    def __init__(
        self,
        knowledge_tree: list | None = None,
        question_stats: dict | None = None,
    ):
        """初始化，可预注入知识树和题库统计数据."""
        self._knowledge_tree = knowledge_tree or []
        self._question_stats = question_stats or {}

    async def run(self, context: dict) -> dict:
        """执行选题计划."""
        template = context.get("template", {})
        custom_params = context.get("custom_params", {})
        self._knowledge_tree = context.get("knowledge_tree", self._knowledge_tree)
        self._question_stats = context.get("question_stats", self._question_stats)

        user_message = self._build_user_message(template, custom_params)

        # 使用 tool_use 循环，让 AI 自主决定是否需要查询更多信息
        result_text = await self.call_llm_with_tools(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
        )

        # 解析 JSON 响应
        plan = self._parse_plan(result_text)
        if not plan:
            logger.error("planner_fallback_used", content=result_text[:300])
            plan = self._build_fallback_plan(template)

        return plan

    def _parse_plan(self, text: str) -> dict | None:
        """解析 LLM 返回的计划文本为 dict，失败返回 None."""
        # 尝试直接解析
        try:
            plan = json.loads(text)
            if self._validate_plan_structure(plan):
                return plan
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取 JSON
        plan = self._extract_json_from_text(text)
        if plan and self._validate_plan_structure(plan):
            return plan

        return None

    async def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """执行 Planner Agent 的工具调用."""
        if tool_name == "query_knowledge_tree":
            return self._query_knowledge_tree(arguments)
        if tool_name == "query_question_stats":
            return self._query_question_stats(arguments)
        return {"error": f"未知工具: {tool_name}"}

    def _query_knowledge_tree(self, arguments: dict) -> dict:
        """查询知识点树."""
        stage = arguments.get("stage")
        grade = arguments.get("grade")

        filtered = self._knowledge_tree
        if stage:
            filtered = [n for n in filtered if n.get("stage") == stage]
        if grade:
            filtered = [n for n in filtered if n.get("grade") == grade]

        return {
            "knowledge_tree": filtered[:20],  # 限制返回量
            "total_count": len(filtered),
        }

    def _query_question_stats(self, arguments: dict) -> dict:
        """查询题库统计."""
        return {
            "stats": self._question_stats,
            "total": sum(self._question_stats.values()),
        }

    def _build_user_message(self, template: dict, custom_params: dict) -> str:
        """构建用户消息."""
        return f"""请根据以下信息制定选题计划：

## 试卷模板
- 学段：{template.get('stage')}
- 年级：{template.get('grade')}
- 总分：{template.get('total_score')}
- 时长：{template.get('duration_minutes')} 分钟

## 模板结构
{self._format_structure(template.get('structure', {}))}

## 用户自定义参数
- 目标难度：{custom_params.get('difficulty_target', '未指定')}
- 重点知识点：{', '.join(custom_params.get('knowledge_focus', []))}
- 排除题目ID：{custom_params.get('avoid_question_ids', [])}
- 优先真题：{custom_params.get('prefer_real_questions', True)}
- 允许AI生成：{custom_params.get('allow_ai_generation', True)}

请使用 query_knowledge_tree 和 query_question_stats 工具获取必要信息后，
返回以下格式的 JSON 选题计划：
{{
  "sections_plan": [
    {{
      "section_name": "选择题",
      "section_index": 0,
      "need_count": 10,
      "difficulty_distribution": [3, 4, 2, 1],
      "knowledge_allocation": {{"代数": 4, "几何": 3, "概率统计": 2, "函数": 1}},
      "estimated_from_bank": 8,
      "estimated_ai_gen": 2
    }}
  ],
  "total_questions": 20,
  "estimated_difficulty": 3.2,
  "knowledge_coverage_target": 0.7
}}"""

    def _format_structure(self, structure: dict) -> str:
        """格式化模板结构."""
        sections = structure.get("sections", [])
        lines = []
        for i, s in enumerate(sections, 1):
            lines.append(
                f"{i}. {s.get('name', '')}：{s.get('count', 0)}题，"
                f"每题{s.get('per_question_score', 0)}分，"
                f"难度范围{s.get('difficulty_range', [1, 5])}"
            )
        return "\n".join(lines) if lines else "无"

    def _extract_json_from_text(self, text: str) -> dict | None:
        """从文本中提取 JSON，支持 markdown 代码块和嵌套结构."""
        # 优先尝试提取 markdown 代码块中的 JSON
        code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?\s*```"
        code_match = re.search(code_block_pattern, text)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 回退：用 rfind 找最后一个 }，配合第一个 { 提取最外层 JSON
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace : last_brace + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _validate_plan_structure(self, plan: dict) -> bool:
        """校验计划是否包含必要字段."""
        if not isinstance(plan, dict):
            return False
        if not _REQUIRED_PLAN_FIELDS.issubset(plan.keys()):
            return False
        sections = plan.get("sections_plan", [])
        if not isinstance(sections, list) or len(sections) == 0:
            return False
        for sec in sections:
            if not isinstance(sec, dict):
                return False
            if not _REQUIRED_SECTION_FIELDS.issubset(sec.keys()):
                return False
        return True

    def _build_fallback_plan(self, template: dict) -> dict:
        """构建回退选题计划，使用模板的 difficulty_range."""
        structure = template.get("structure", {})
        sections = structure.get("sections", [])

        sections_plan = []
        for i, s in enumerate(sections):
            diff_range = s.get("difficulty_range", [1, 5])
            sections_plan.append({
                "section_name": s.get("name", f"第{i+1}部分"),
                "section_index": i,
                "need_count": s.get("count", 0),
                "difficulty_distribution": [
                    round(sum(diff_range) / 2)
                ] * s.get("count", 0),
                "knowledge_allocation": {},
                "estimated_from_bank": max(0, s.get("count", 0) - 2),
                "estimated_ai_gen": min(2, s.get("count", 0)),
            })

        return {
            "sections_plan": sections_plan,
            "total_questions": sum(s.get("count", 0) for s in sections),
            "estimated_difficulty": round(
                sum(
                    sum(s.get("difficulty_range", [1, 5])) / 2
                    for s in sections
                )
                / max(len(sections), 1),
                1,
            ),
            "knowledge_coverage_target": 0.7,
        }
