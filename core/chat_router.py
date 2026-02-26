"""
AI 对话 + Tool Use API

接收自然语言输入，调用 Anthropic API，AI 自动决定调用哪些工具。
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any

from backend.tools import generate_tools_from_registry
from prompts.loader import load as load_prompt
from core.registry import ModuleRegistration, ModuleType, Capability, get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Lazy-initialized LLM client and model
_llm_client = None
_llm_model = None


def _get_llm_client():
    """获取 LLM 客户端（延迟初始化，读取统一配置）"""
    global _llm_client, _llm_model

    if _llm_client is not None:
        return _llm_client, _llm_model

    from core.config import get_app_config
    config = get_app_config()
    llm = config.get('llm', {})

    provider = llm.get('provider', '')
    model = llm.get('model', 'claude-sonnet-4-5-20250929')
    api_key = llm.get('api_key', '')
    base_url = llm.get('base_url', '')

    # Auto-detect provider if not set
    if not provider:
        if 'claude' in model.lower():
            provider = 'anthropic'
        else:
            provider = 'openai'

    if provider != 'anthropic':
        logger.warning(
            f"chat_router uses Anthropic tool-use protocol. "
            f"Provider '{provider}' may not work correctly for /api/chat."
        )

    import anthropic
    kwargs = {}
    if api_key:
        kwargs['api_key'] = api_key
    if base_url:
        kwargs['base_url'] = base_url
    _llm_client = anthropic.Anthropic(**kwargs)
    _llm_model = model
    return _llm_client, _llm_model

_system_prompt_cache = None


def _get_system_prompt() -> str:
    """动态生成系统提示词：静态模板 + registry 扫描的工具能力"""
    global _system_prompt_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache

    base = load_prompt("system/chat_assistant")
    registry = get_registry()
    capabilities = registry.describe_capabilities()
    _system_prompt_cache = f"{base}\n\n## 可用工具\n{capabilities}"
    return _system_prompt_cache


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


# 工具名 → 执行函数 的静态映射（用于快速分发）
_TOOL_DISPATCH = {}


def _build_tool_dispatch():
    """构建工具分发表 — 自动收集所有插件的 TOOL_HANDLERS"""
    if _TOOL_DISPATCH:
        return

    registry = get_registry()

    # 自动收集所有插件的 TOOL_HANDLERS
    _TOOL_DISPATCH.update(registry.get_all_tool_handlers())

    # 聚合统计（跨所有插件）
    async def _get_statistics(tool_input):
        stats = {}
        for domain, handler in registry.get_stats_handlers().items():
            stats[domain] = await handler()
        return stats

    _TOOL_DISPATCH["get_statistics"] = _get_statistics


async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    """执行工具调用，返回结果（基于注册表动态分发）"""
    _build_tool_dispatch()

    handler = _TOOL_DISPATCH.get(tool_name)
    if handler:
        try:
            return await handler(tool_input)
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"未知工具: {tool_name}"}


@router.post("/")
async def chat(req: ChatRequest):
    """处理聊天请求，支持工具调用，流式返回"""

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    async def generate():
        client, model = _get_llm_client()

        # 多轮工具调用循环
        current_messages = messages.copy()

        for _ in range(5):  # 最多 5 轮工具调用
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=_get_system_prompt(),
                tools=generate_tools_from_registry(),
                messages=current_messages
            )

            tool_calls = []
            text_content = ""

            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(block)

            # 流式发送文本
            if text_content:
                yield f"data: {json.dumps({'type': 'text', 'content': text_content})}\n\n"

            # 如果没有工具调用，结束
            if not tool_calls or response.stop_reason == "end_turn":
                break

            # 执行工具调用
            _LONG_RUNNING_TOOLS = {"ingest_paper", "extract_knowledge", "analyze_relations"}
            tool_results = []
            for tool_call in tool_calls:
                # 通知前端正在调用工具
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_call.name, 'input': tool_call.input})}\n\n"

                if tool_call.name in _LONG_RUNNING_TOOLS:
                    yield f"data: {json.dumps({'type': 'progress', 'content': f'正在执行 {tool_call.name}，可能需要一些时间...'})}\n\n"

                result = await execute_tool(tool_call.name, dict(tool_call.input))

                # 通知前端工具调用结果
                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_call.name, 'result': result})}\n\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            # 将工具调用和结果加入消息历史
            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# Router 注册元数据
ROUTER_REGISTRATION = ModuleRegistration(
    name="chat_router",
    module_type=ModuleType.ROUTER,
    display_name="AI 对话 API",
    description="自然语言对话，AI 自动决定调用工具",
    api_prefix="/api/chat",
    api_tags=["chat"],
    capabilities=[
        Capability(name="chat", description="AI 对话（支持工具调用和流式返回）", tags=["chat", "ai"]),
    ],
)
