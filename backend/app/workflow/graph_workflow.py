"""试卷生成状态图工作流引擎 - 基于 LangGraph 风格的 DAG 编排.

支持:
- 多 Agent 状态流转
- Validator 检测到错误时精准回退到 Generator
- Self-Refine 闭环自省机制
- 最大重试次数限制防止无限循环
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Protocol

import structlog

logger = structlog.get_logger()


class WorkflowState(Enum):
    """工作流状态定义."""

    PENDING = auto()
    PLANNING = auto()
    RETRIEVING = auto()
    GENERATING = auto()
    VALIDATING = auto()
    ASSEMBLING = auto()
    COMPLETED = auto()
    FAILED = auto()
    # 回退状态用于 Self-Refine
    REGENERATING = auto()
    REVALIDATING = auto()


@dataclass
class WorkflowContext:
    """工作流上下文，携带所有阶段共享的状态."""

    template: dict = field(default_factory=dict)
    custom_params: dict = field(default_factory=dict)
    plan: dict = field(default_factory=dict)
    retrieval_result: dict = field(default_factory=dict)
    generation_result: dict = field(default_factory=dict)
    validation_result: dict = field(default_factory=dict)
    assembler_result: dict = field(default_factory=dict)
    
    # 错误追踪
    current_stage: str = ""
    error_message: str = ""
    retry_counts: dict = field(default_factory=dict)
    max_retries: int = 3  # 每个阶段最大重试次数
    
    # 进度追踪
    progress_pct: float = 0.0
    status: str = "pending"
    
    # 数据库会话 (可选)
    session: Any = None


class AgentProtocol(Protocol):
    """Agent 协议定义."""

    async def run(self, context: dict) -> dict:
        """执行 Agent 逻辑."""
        ...


@dataclass
class StateNode:
    """状态图节点定义."""

    name: str
    agent: AgentProtocol | None
    handler: Callable[[WorkflowContext], asyncio.Coroutine] | None = None
    transitions: dict[str, str] = field(default_factory=dict)  # condition -> next_state
    
    async def execute(self, context: WorkflowContext) -> dict:
        """执行节点逻辑."""
        if self.agent:
            return await self.agent.run({
                "template": context.template,
                "custom_params": context.custom_params,
                "plan": context.plan,
                "retrieval_result": context.retrieval_result,
                "generation_result": context.generation_result,
                "validation_result": context.validation_result,
                "session": context.session,
            })
        elif self.handler:
            return await self.handler(context)
        else:
            raise ValueError(f"Node {self.name} has no agent or handler")


class WorkflowGraph:
    """有向无环图工作流引擎.
    
    支持条件转移和回退机制:
    - 正常流程: Planning → Retrieving → Generating → Validating → Assembling
    - 回退流程: Validating (发现错误) → Generating (局部重写) → Revalidating
    """

    def __init__(self):
        self.nodes: dict[str, StateNode] = {}
        self.start_node: str | None = None
        self.end_nodes: list[str] = []

    def add_node(self, node: StateNode) -> None:
        """添加状态节点."""
        self.nodes[node.name] = node

    def set_start(self, node_name: str) -> None:
        """设置起始节点."""
        self.start_node = node_name

    def add_end(self, node_name: str) -> None:
        """设置终止节点."""
        self.end_nodes.append(node_name)

    async def run(self, initial_context: WorkflowContext) -> WorkflowContext:
        """执行工作流.
        
        从起始节点开始，根据转移条件依次执行各节点，
        直到到达终止节点或发生错误。
        """
        if not self.start_node:
            raise ValueError("Start node not set")

        current_state = self.start_node
        context = initial_context

        while current_state not in self.end_nodes:
            if current_state not in self.nodes:
                raise ValueError(f"Unknown state: {current_state}")

            node = self.nodes[current_state]
            context.current_stage = node.name
            
            logger.info("workflow_executing_node", node=node.name, stage=context.current_stage)

            try:
                # 检查重试次数
                retry_count = context.retry_counts.get(node.name, 0)
                if retry_count >= context.max_retries:
                    context.status = "failed"
                    context.error_message = f"阶段 {node.name} 重试次数超过上限 ({context.max_retries})"
                    logger.error("workflow_max_retries_exceeded", node=node.name)
                    break

                # 执行节点
                result = await node.execute(context)
                
                # 根据结果决定下一个状态
                next_state = self._determine_next_state(node, result, context)
                
                logger.info(
                    "workflow_node_completed",
                    node=node.name,
                    next_state=next_state,
                    result_summary=str(result)[:200],
                )
                
                current_state = next_state

            except Exception as e:
                logger.error("workflow_node_error", node=node.name, error=str(e), exc_info=True)
                context.retry_counts[node.name] = context.retry_counts.get(node.name, 0) + 1
                
                if context.retry_counts[node.name] >= context.max_retries:
                    context.status = "failed"
                    context.error_message = str(e)
                    break
                
                # 重试时保持在当前状态
                current_state = node.name
                await asyncio.sleep(0.5 * (context.retry_counts[node.name]))  # 指数退避

        return context

    def _determine_next_state(
        self, 
        node: StateNode, 
        result: dict, 
        context: WorkflowContext
    ) -> str:
        """根据执行结果和转移条件确定下一个状态."""
        # 检查是否有条件转移
        for condition, target_state in node.transitions.items():
            if condition == "default":
                continue
            
            # 评估条件
            if self._evaluate_condition(condition, result, context):
                return target_state
        
        # 默认转移
        return node.transitions.get("default", "")

    def _evaluate_condition(self, condition: str, result: dict, context: WorkflowContext) -> bool:
        """评估转移条件."""
        if condition == "is_valid":
            return result.get("is_valid", False)
        elif condition == "has_errors":
            issues = result.get("issues", [])
            cross_issues = result.get("cross_issues", [])
            return len(issues) > 0 or len(cross_issues) > 0
        elif condition == "needs_regeneration":
            # 需要重生成的情况：有严重错误
            issues = result.get("issues", [])
            critical_types = {"answer_mismatch", "latex_error", "content_error"}
            return any(
                issue.get("type") in critical_types 
                for issue in issues
            )
        elif condition == "success":
            return context.status != "failed"
        return False


class GenerationWorkflowBuilder:
    """试卷生成工作流构建器.
    
    构建包含 Self-Refine 机制的完整工作流:
    
    Planning → Retrieving → Generating → Validating ─┐
       ↓            ↓            ↓           ↓         │
       │            │            │      [has_errors]   │
       │            │            │           ↓         │
       │            │            │    Regenerating ────┘
       │            │            │           ↓
       │            │            │    Revalidating
       │            │            │           ↓
       ↓            ↓            ↓           ↓
    Assembling ←────────────────────────────┘
       ↓
    Completed
    """

    def build(self, planner, retriever, generator, validator, assembler) -> WorkflowGraph:
        """构建完整的工作流图."""
        graph = WorkflowGraph()

        # Planning 节点
        planning_node = StateNode(
            name="planning",
            agent=planner,
            transitions={"default": "retrieving"},
        )
        graph.add_node(planning_node)

        # Retrieving 节点
        retrieving_node = StateNode(
            name="retrieving",
            agent=retriever,
            transitions={"default": "generating"},
        )
        graph.add_node(retrieving_node)

        # Generating 节点
        generating_node = StateNode(
            name="generating",
            agent=generator,
            transitions={"default": "validating"},
        )
        graph.add_node(generating_node)

        # Validating 节点 - 关键：支持回退
        validating_node = StateNode(
            name="validating",
            agent=validator,
            transitions={
                "is_valid": "assembling",
                "needs_regeneration": "regenerating",
                "has_errors": "regenerating",
                "default": "assembling",  # 警告级别问题直接通过
            },
        )
        graph.add_node(validating_node)

        # Regenerating 节点 - Self-Refine 核心
        regenerating_node = StateNode(
            name="regenerating",
            agent=None,
            handler=self._create_regeneration_handler(generator),
            transitions={"default": "revalidating"},
        )
        graph.add_node(regenerating_node)

        # Revalidating 节点
        revalidating_node = StateNode(
            name="revalidating",
            agent=validator,
            transitions={
                "is_valid": "assembling",
                "needs_regeneration": "regenerating",
                "has_errors": "regenerating",
                "default": "assembling",
            },
        )
        graph.add_node(revalidating_node)

        # Assembling 节点
        assembling_node = StateNode(
            name="assembling",
            agent=assembler,
            transitions={"default": "completed"},
        )
        graph.add_node(assembling_node)

        # 设置起始和终止节点
        graph.set_start("planning")
        graph.add_end("completed")
        graph.add_end("failed")

        return graph

    def _create_regeneration_handler(self, generator):
        """创建重生成处理器，实现 Self-Refine 逻辑."""
        async def handler(context: WorkflowContext):
            """根据验证意见进行局部重写."""
            validation_result = context.validation_result
            issues = validation_result.get("issues", [])
            
            logger.info(
                "self_refine_regeneration",
                issues_count=len(issues),
                issues=[{"type": i.get("type"), "question_id": i.get("question_id")} for i in issues],
            )

            # 提取需要重写的题目 ID
            questions_to_regenerate = []
            for issue in issues:
                qid = issue.get("question_id")
                if qid and qid not in questions_to_regenerate:
                    questions_to_regenerate.append(qid)

            # 构造重写上下文
            regen_context = {
                "template": context.template,
                "custom_params": context.custom_params,
                "retrieval_result": context.retrieval_result,
                "generation_result": context.generation_result,
                "validation_feedback": {
                    "issues": issues,
                    "questions_to_regenerate": questions_to_regenerate,
                },
                "session": context.session,
                "is_regeneration": True,  # 标记为重生成模式
            }

            # 调用 Generator 进行重写
            regenerated = await generator.run(regen_context)
            
            # 合并结果
            existing_questions = context.generation_result.get("generated_questions", [])
            existing_ids = {q.get("id") for q in existing_questions if q.get("id")}
            
            # 保留未需要重写的题目，添加新生成的题目
            merged_questions = [
                q for q in existing_questions 
                if q.get("id") not in questions_to_regenerate
            ]
            merged_questions.extend(regenerated.get("generated_questions", []))
            
            context.generation_result = {
                "generated_questions": merged_questions,
                "regeneration_info": {
                    "regenerated_count": len(questions_to_regenerate),
                    "new_questions_count": len(regenerated.get("generated_questions", [])),
                },
            }
            
            return regenerated

        return handler


@dataclass
class WorkflowResult:
    """工作流执行结果."""

    success: bool
    context: WorkflowContext
    paper_id: int | None = None
    stats: dict = field(default_factory=dict)
    error_message: str | None = None
