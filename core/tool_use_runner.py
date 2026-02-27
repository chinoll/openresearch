"""
ToolUseRunner - Anthropic tool-use 循环的通用执行器

从 chat_router.py 和 main.py 中提取的通用 tool-use 循环逻辑。
回调驱动，适配不同 UI（CLI、SSE 流式、TUI）。
"""

import json
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolUseRunner:
    """
    通用 Anthropic tool-use 循环执行器

    Usage:
        runner = ToolUseRunner(
            client=anthropic_client,
            model="claude-sonnet-4-5-20250929",
            system_prompt="...",
            tools=[...],
            execute_tool=my_execute_fn,
        )
        result = await runner.run(messages)
    """

    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        tools: List[Dict],
        execute_tool: Callable[[str, Dict], Coroutine[Any, Any, Any]],
        max_iterations: int = 15,
        max_tokens: int = 2048,
        on_text: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, Dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
    ):
        """
        Args:
            client: Anthropic client instance
            model: 模型名称
            system_prompt: 系统提示词
            tools: Anthropic tool 定义列表
            execute_tool: 工具执行函数 async (name, input) -> result
            max_iterations: 最大循环次数（安全上限）
            max_tokens: 每次 LLM 调用的 max_tokens
            on_text: 文本输出回调
            on_tool_call: 工具调用通知回调
            on_tool_result: 工具结果回调
        """
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.execute_tool = execute_tool
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.on_text = on_text
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result

    async def run(self, messages: List[Dict]) -> str:
        """
        执行 tool-use 循环，返回最终文本输出

        Args:
            messages: 初始消息列表

        Returns:
            最终的文本响应
        """
        current_messages = [dict(m) for m in messages]
        final_text = ""

        for iteration in range(self.max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                tools=self.tools,
                messages=current_messages,
            )

            text = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text += block.text
                elif block.type == "tool_use":
                    tool_calls.append(block)

            if text:
                final_text += text
                if self.on_text:
                    self.on_text(text)

            if not tool_calls or response.stop_reason == "end_turn":
                break

            # 执行工具调用
            tool_results = []
            for tc in tool_calls:
                if self.on_tool_call:
                    self.on_tool_call(tc.name, dict(tc.input))

                result = await self.execute_tool(tc.name, dict(tc.input))

                if self.on_tool_result:
                    self.on_tool_result(tc.name, result)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})
        else:
            # max_iterations 耗尽
            exhaust_msg = f"\n[已达到最大工具调用轮数 {self.max_iterations}，自动停止]"
            final_text += exhaust_msg
            if self.on_text:
                self.on_text(exhaust_msg)

        return final_text
