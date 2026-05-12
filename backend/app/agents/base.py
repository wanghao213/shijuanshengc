"""Agent 基类."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import structlog

from app.core.llm_gateway import LLMResponse, chat, structured_chat

logger = structlog.get_logger()

# 工具执行重试配置
_TOOL_MAX_RETRIES = 2
_TOOL_RETRY_BASE_DELAY = 0.5


class BaseAgent(ABC):
    """所有 Agent 的基类，封装通用的 LLM 调用逻辑.

    支持：
    - 普通对话调用
    - JSON 结构化输出
    - tool_use 循环（AI 调用工具获取信息）
    """

    # 子类可覆盖，定义该 Agent 可用的工具
    tools: ClassVar[list[dict[str, Any]]] = []

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

        last_content = ""
        for round_num in range(max_rounds):
            response = await chat(
                messages=messages,
                tools=available_tools if available_tools else None,
                temperature=0.3,
            )

            content = response.content or ""
            if content:
                last_content = content

            # 空响应但可能有 tool_calls（某些 LLM 在 tool_use 时 content 为空）
            if not self._has_tool_calls(response):
                if content:
                    return content
                # 空响应且无 tool_calls — 无法继续
                logger.warning(
                    "agent_empty_response",
                    agent=self.__class__.__name__,
                    round=round_num,
                )
                break

            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                return content

            # 将 assistant 的响应加入消息历史
            messages.append({
                "role": "assistant",
                "content": content,
            })

            # 执行每个 tool call 并添加结果（带重试）
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

                result = await self._execute_tool_with_retry(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        logger.warning(
            "agent_tool_loop_max_rounds",
            agent=self.__class__.__name__,
            rounds=max_rounds,
        )
        return last_content

    async def _execute_tool_with_retry(
        self, tool_name: str, arguments: dict
    ) -> dict:
        """执行工具调用，带指数退避重试（仅针对瞬时错误）."""
        last_error: Exception | None = None
        for attempt in range(_TOOL_MAX_RETRIES + 1):
            try:
                return await self.execute_tool(tool_name, arguments)
            except (ConnectionError, TimeoutError, OSError) as e:
                last_error = e
                if attempt < _TOOL_MAX_RETRIES:
                    delay = _TOOL_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "tool_transient_error",
                        tool=tool_name,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
            except Exception:
                # 非瞬时错误不做重试，直接抛出
                raise
        # 重试耗尽，返回错误而非抛出异常（与原有行为一致）
        logger.error(
            "tool_retry_exhausted",
            tool=tool_name,
            error=str(last_error),
        )
        return {"error": f"工具 {tool_name} 执行失败: {last_error}"}

    async def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """执行工具调用. 子类应覆盖此方法以实现具体工具逻辑."""
        logger.warning(
            "unhandled_tool_call",
            tool=tool_name,
            agent=self.__class__.__name__,
        )
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

        content = response.content
        if not isinstance(content, str) or not content.strip():
            return False
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return False

        if isinstance(data, dict):
            if "tool_calls" in data:
                return True
            if "name" in data and ("arguments" in data or "input" in data):
                return True
        if isinstance(data, list):
            return any(isinstance(item, dict) and "name" in item for item in data)
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
            calls: list[dict] = []
            for tc in response.tool_calls:
                try:
                    name = (
                        tc.function.name
                        if hasattr(tc, "function")
                        else tc.get("name", "")
                    )
                    raw_args = (
                        tc.function.arguments
                        if hasattr(tc, "function")
                        else tc.get("arguments", "{}")
                    )
                    args = (
                        json.loads(raw_args)
                        if isinstance(raw_args, str)
                        else raw_args
                        if isinstance(raw_args, dict)
                        else {}
                    )
                    calls.append({"id": tc.id or "", "name": name, "arguments": args})
                except (AttributeError, json.JSONDecodeError) as e:
                    logger.warning("tool_call_parse_error", error=str(e))
            return calls

        content = response.content or ""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return []

        if isinstance(data, dict):
            if "tool_calls" in data:
                return data["tool_calls"]
            if "name" in data and ("arguments" in data or "input" in data):
                return [{
                    "id": "",
                    "name": data["name"],
                    "arguments": data.get("arguments", data.get("input", {})),
                }]
        if isinstance(data, list):
            return [
                item for item in data
                if isinstance(item, dict) and "name" in item
            ]
        return []
