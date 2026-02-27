"""
递归 Chat 引擎 — Team Agent 的研究工具

允许 Team agent 通过 `research` 工具递归调用完整的 tool-use chat，
自主查找外部信息（搜索论文、提取知识等）来支撑观点。

递归完成后完整对话历史丢弃（自然 GC），只保留：
- full_result → 返回给 agent 用于推理
- meta_summary → 留给系统上下文感知
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== research 工具定义 ====================

RESEARCH_TOOL_DEF = {
    "name": "research",
    "description": (
        "递归研究工具：发起一轮完整的 tool-use 对话来查找外部信息。"
        "拥有所有系统工具（搜索论文、提取知识、Team 协作等）的完整权限。"
        "当你需要查找资料来支撑观点时使用此工具。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "研究查询（你想查找什么信息）",
            },
            "context": {
                "type": "string",
                "description": "当前上下文（帮助研究更精准）",
            },
        },
        "required": ["query"],
    },
}


# ==================== 递归 chat 引擎 ====================

async def run_recursive_chat(
    query: str,
    context: str = "",
    depth: int = 0,
    max_depth: int = 2,
) -> Dict[str, Any]:
    """
    执行一轮递归研究 chat。

    拥有完整工具权限（TOOL + subagent），可自主使用 search_papers、
    extract_knowledge、run_team 等。递归 chat 的完整对话历史在函数
    返回后丢弃（自然 GC）。

    Args:
        query: 研究查询
        context: 当前上下文
        depth: 当前递归深度
        max_depth: 最大递归深度

    Returns:
        {"result": full_result, "meta_summary": meta_summary}
    """
    from core.chat_router import execute_tool, get_all_tools
    from core.tool_use_runner import ToolUseRunner

    client, model = _get_llm_client()

    # 复用 chat_assistant 系统提示词，前置递归模式声明
    from core.chat_router import _get_system_prompt
    base_prompt = _get_system_prompt()
    system_prompt = (
        f"[递归研究模式 depth={depth}/{max_depth}] "
        f"你正在为 Team Agent 查找资料，完成后直接给出结论性回答。\n\n"
        + base_prompt
    )

    # 组装工具列表：完整权限
    tools = get_all_tools()

    # 如果还没达到最大深度，允许再递归
    if depth + 1 < max_depth:
        tools = tools + [RESEARCH_TOOL_DEF]

    # 工具调用日志
    tool_log: List[Dict[str, str]] = []

    async def _execute_tool(tool_name: str, tool_input: Dict) -> Any:
        """包装工具执行：拦截 research 和 team 工具，其余委托 chat_router"""
        if tool_name == "research":
            # 递归调用
            sub_result = await run_recursive_chat(
                query=tool_input.get("query", ""),
                context=tool_input.get("context", ""),
                depth=depth + 1,
                max_depth=max_depth,
            )
            tool_log.append({
                "tool": "research",
                "query": tool_input.get("query", "")[:80],
                "meta": sub_result.get("meta_summary", ""),
            })
            return sub_result["result"]

        if tool_name in ("run_team", "run_ad_hoc_team"):
            # Team 工具：传递 recursion_depth 以便子 team 的 agent 也有递归能力
            tool_input_with_depth = {**tool_input, "_recursion_depth": depth + 1}
            result = await execute_tool(tool_name, tool_input_with_depth)
            tool_log.append({
                "tool": tool_name,
                "task": tool_input.get("task", "")[:80],
            })
            return result

        # 其他工具：委托 chat_router.execute_tool
        result = await execute_tool(tool_name, tool_input)
        tool_log.append({
            "tool": tool_name,
            "summary": str(result)[:80] if result else "",
        })
        return result

    # 构建初始消息
    user_message = query
    if context:
        user_message = f"研究查询: {query}\n\n当前上下文:\n{context}"

    messages = [{"role": "user", "content": user_message}]

    # 运行 ToolUseRunner
    runner = ToolUseRunner(
        client=client,
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        execute_tool=_execute_tool,
        max_iterations=10,
    )

    full_result = await runner.run(messages)
    # runner.run 返回后，runner 内部的 current_messages 自然 GC

    # 生成元摘要
    meta_summary = _build_meta_summary(query, depth, tool_log, full_result)

    return {
        "result": full_result,
        "meta_summary": meta_summary,
    }


# ==================== 辅助函数 ====================

def _get_llm_client():
    """获取 LLM 客户端（复用 chat_router 的延迟初始化逻辑）"""
    from core.chat_router import _get_llm_client as get_client
    return get_client()


def _build_meta_summary(
    query: str,
    depth: int,
    tool_log: List[Dict[str, str]],
    result: str,
) -> str:
    """
    构建元摘要（纯字符串拼接，不需要 LLM）。

    格式：[递归研究 depth=N] 查询: ... | 工具调用: ... | 子Team: N | 嵌套递归: N | 结果: N字符
    """
    tool_names = [t["tool"] for t in tool_log]
    team_count = sum(1 for t in tool_names if t in ("run_team", "run_ad_hoc_team"))
    research_count = sum(1 for t in tool_names if t == "research")

    tool_calls_str = ", ".join(tool_names) if tool_names else "无"

    return (
        f"[递归研究 depth={depth}] "
        f"查询: {query[:60]} | "
        f"工具调用: {tool_calls_str} | "
        f"子Team: {team_count} | "
        f"嵌套递归: {research_count} | "
        f"结果: {len(result)}字符"
    )
