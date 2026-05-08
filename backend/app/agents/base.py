"""Agent 基类."""

import json
from abc import ABC, abstractmethod

import structlog

from app.core.llm_gateway import LLMResponse, chat, structured_chat

logger = structlog.get_logger()


class BaseAgent(ABC):
    """所有 Agent 的基类，封装通用的 LLM 调用逻辑.

    支持：
    - 普通对话调用
    - JSON 结构化输出
    - tool_use 循环（AI 调用工具获取信息）
    """

    # 子类可覆盖，定义该 Agent 可用的工具
    tools: list[dict] = []

    @abstractmethod
    async def run(self, context: dict) -> dict:
        """子类必须实现的主逻辑."""
        raise NotImplementedError

    async def call_llm(
        self,
        system_prompt: str,
        user_message: str,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """调用 LLM."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        if response_format:
            return await structured_chat(messages=messages)
        return await chat(messages=messages)

    async def call_llm_json(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict:
        """调用 LLM 并解析 JSON 响应."""
        response = await self.call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error("llm_json_parse_error", error=str(e), content=response.content[:200])
            return {"error": "LLM 返回格式错误"}

    async def call_llm_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        max_rounds: int = 5,
    ) -> str:
        """调用 LLM 并处理 tool_use 循环.

        流程：
        1. 发送消息 + 工具定义给 LLM
        2. 如果 LLM 返回 tool_use，执行对应工具
        3. 将工具结果作为 tool_result 反馈给 LLM
        4. 重复直到 LLM 返回最终文本响应或达到最大轮数

        Returns:
            LLM 的最终文本响应
        """
        available_tools = tools or self.tools
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for round_num in range(max_rounds):
            response = await chat(
                messages=messages,
                tools=available_tools if available_tools else None,
                temperature=0.3,
            )

            # 检查是否有 tool_use
            content = response.content
            if not content:
                break

            # LiteLLM 返回的 content 在有 tool_use 时可能是特殊格式
            # 需要解析 assistant message 的完整结构
            # 这里简化处理：如果 content 是纯文本且不含 tool_use 标记，直接返回
            if not self._has_tool_calls(response):
                return content

            # 处理 tool calls
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                return content

            # 将 assistant 的响应加入消息历史
            messages.append({
                "role": "assistant",
                "content": content,
            })

            # 执行每个 tool call 并添加结果
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {})
                tool_call_id = tool_call.get("id", "")

                logger.info(
                    "agent_tool_call",
                    agent=self.__class__.__name__,
                    tool=tool_name,
                    args=tool_args,
                    round=round_num,
                )

                result = await self.execute_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        logger.warning("agent_tool_loop_max_rounds", agent=self.__class__.__name__, rounds=max_rounds)
        return content if content else ""

    async def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """执行工具调用. 子类应覆盖此方法以实现具体工具逻辑."""
        logger.warning("unhandled_tool_call", tool=tool_name, agent=self.__class__.__name__)
        return {"error": f"未实现的工具: {tool_name}"}

    def _has_tool_calls(self, response: LLMResponse) -> bool:
        """检查响应是否包含 tool_use 调用.

        检查多种 tool_use 格式：
        1. LiteLLM 标准格式：response.tool_calls 属性
        2. JSON content 中的 tool_calls 字段
        3. JSON content 中的 name + arguments 结构
        """
        # 检查 LiteLLM 标准 tool_calls 属性
        if hasattr(response, "tool_calls") and response.tool_calls:
            return True

        content = response.content or ""
        if not content.strip():
            return False
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                if "tool_calls" in data:
                    return True
                if "name" in data and ("arguments" in data or "input" in data):
                    return True
            if isinstance(data, list) and any(
                isinstance(item, dict) and "name" in item for item in data
            ):
                return True
        except json.JSONDecodeError:
            pass
        return False

    def _extract_tool_calls(self, response: LLMResponse) -> list[dict]:
        """从响应中提取 tool calls.

        支持多种格式：
        1. LiteLLM 标准 tool_calls 属性
        2. JSON content 中的 tool_calls 字段
        3. JSON content 中的 name + arguments 结构（单个或数组）
        """
        # 检查 LiteLLM 标准 tool_calls 属性
        if hasattr(response, "tool_calls") and response.tool_calls:
            return [
                {
                    "id": tc.id or "",
                    "name": tc.function.name if hasattr(tc, "function") else tc.get("name", ""),
                    "arguments": (
                        json.loads(tc.function.arguments)
                        if hasattr(tc, "function") and isinstance(tc.function.arguments, str)
                        else tc.get("arguments", {})
                    ),
                }
                for tc in response.tool_calls
            ]

        content = response.content or ""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                if "tool_calls" in data:
                    return data["tool_calls"]
                if "name" in data and ("arguments" in data or "input" in data):
                    return [{"id": "", "name": data["name"], "arguments": data.get("arguments", data.get("input", {}))}]
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict) and "name" in item]
        except json.JSONDecodeError:
            pass
        return []
