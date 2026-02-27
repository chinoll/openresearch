"""
AI 对话 + Tool Use API

接收自然语言输入，调用 Anthropic API，AI 自动决定调用哪些工具。
Team（子 Agent 协作）工具内置于此，不通过插件注册。
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
_system_prompt_cache_time = 0
_SYSTEM_PROMPT_TTL = 300  # 5 minutes


def _get_system_prompt() -> str:
    """动态生成系统提示词：静态模板 + registry 扫描的工具能力（带 TTL 缓存）"""
    global _system_prompt_cache, _system_prompt_cache_time
    import time
    now = time.time()
    if _system_prompt_cache is not None and (now - _system_prompt_cache_time) < _SYSTEM_PROMPT_TTL:
        return _system_prompt_cache

    base = load_prompt("system/chat_assistant")
    registry = get_registry()
    capabilities = registry.describe_capabilities()
    _system_prompt_cache = f"{base}\n\n## 可用工具\n{capabilities}"
    _system_prompt_cache_time = now
    return _system_prompt_cache


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


# ==================== 内置 SubAgent 工具（Team） ====================

_subagent_app_config = None
_subagent_registry = None


def _ensure_subagent_init():
    """Lazy init: 加载配置、获取 registry（供 subagent handlers 使用）"""
    global _subagent_app_config, _subagent_registry
    if _subagent_registry is not None:
        return
    from core.config import get_app_config
    _subagent_app_config = get_app_config()
    _subagent_registry = get_registry()


async def _h_run_team(tool_input: Dict) -> Dict:
    """运行预定义 Team"""
    _ensure_subagent_init()
    from core.team import create_team_from_definition

    team_name = tool_input.get("team_name", "")
    task = tool_input.get("task", "")
    initial_data = tool_input.get("initial_data") or {}
    max_turns = tool_input.get("max_turns")

    if not team_name:
        return {"error": "缺少 team_name 参数"}
    if not task:
        return {"error": "缺少 task 参数"}

    team_def = _subagent_registry.get_team_definition(team_name)
    if not team_def:
        available = list(_subagent_registry.get_all_team_definitions().keys())
        return {"error": f"未找到 Team: {team_name}，可用: {available}"}

    try:
        team = create_team_from_definition(team_def, _subagent_app_config, max_turns=max_turns)
        result = await team.run(task, initial_data=initial_data)
        return {
            "display_type": "team_result",
            **result,
        }
    except Exception as e:
        logger.error(f"Team {team_name} 执行失败: {e}")
        return {"error": f"Team 执行失败: {e}"}


async def _h_run_ad_hoc_team(tool_input: Dict) -> Dict:
    """动态组队运行"""
    _ensure_subagent_init()
    from core.team import create_ad_hoc_team

    agent_names = tool_input.get("agent_names", [])
    task = tool_input.get("task", "")
    initial_data = tool_input.get("initial_data") or {}
    max_turns = tool_input.get("max_turns", 10)

    if not agent_names or len(agent_names) < 2:
        return {"error": "至少需要 2 个 agent 组队"}
    if not task:
        return {"error": "缺少 task 参数"}

    try:
        team = create_ad_hoc_team(
            name=f"ad_hoc_{'_'.join(agent_names[:3])}",
            agent_names=agent_names,
            app_config=_subagent_app_config,
            max_turns=max_turns,
        )
        result = await team.run(task, initial_data=initial_data)
        return {
            "display_type": "team_result",
            **result,
        }
    except Exception as e:
        logger.error(f"Ad-hoc team 执行失败: {e}")
        return {"error": f"Team 执行失败: {e}"}


async def _h_list_teams(tool_input: Dict) -> Dict:
    """列出可用 Team 和可组队 Agent"""
    _ensure_subagent_init()

    # 预定义 Teams
    team_defs = _subagent_registry.get_all_team_definitions()
    teams_list = []
    for name, td in team_defs.items():
        teams_list.append({
            "name": name,
            "display_name": getattr(td, 'display_name', ''),
            "description": getattr(td, 'description', ''),
            "members": [
                {"role": m.role, "agent": m.agent_name, "description": m.description}
                for m in getattr(td, 'members', [])
            ],
            "default_max_turns": getattr(td, 'default_max_turns', 10),
            "tags": getattr(td, 'tags', []),
        })

    # 可组队 Agents（声明了 team_export 的）
    team_ready = _subagent_registry.get_team_ready_agents()
    agents_list = []
    for reg in team_ready:
        agents_list.append({
            "name": reg.name,
            "display_name": reg.display_name,
            "role": reg.team_export.default_role,
            "description": reg.team_export.description,
        })

    return {
        "display_type": "team_list",
        "predefined_teams": teams_list,
        "team_ready_agents": agents_list,
    }


# SubAgent 工具的 handler 映射（内置，不通过 TOOL_HANDLERS 暴露）
_SUBAGENT_HANDLERS = {
    "run_team": _h_run_team,
    "run_ad_hoc_team": _h_run_ad_hoc_team,
    "list_teams": _h_list_teams,
}


def generate_subagent_tools() -> List[Dict[str, Any]]:
    """生成内置 subagent 工具的 Anthropic tool_use 定义"""
    return [
        {
            "name": "run_team",
            "description": "运行预定义 Agent Team。Team 内多个 agent 协同完成任务，由 LLM 协调决策。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "Team 名称（通过 list_teams 获取）",
                    },
                    "task": {
                        "type": "string",
                        "description": "任务描述",
                    },
                    "initial_data": {
                        "type": "object",
                        "description": "初始数据（写入共享黑板）",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "最大执行轮数（覆盖默认值）",
                    },
                },
                "required": ["team_name", "task"],
            },
        },
        {
            "name": "run_ad_hoc_team",
            "description": "动态组建 Agent Team 并运行。选择多个 agent 临时组队协作完成任务。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Agent 注册名列表（至少 2 个）",
                    },
                    "task": {
                        "type": "string",
                        "description": "任务描述",
                    },
                    "initial_data": {
                        "type": "object",
                        "description": "初始数据（写入共享黑板）",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "最大执行轮数",
                        "default": 10,
                    },
                },
                "required": ["agent_names", "task"],
            },
        },
        {
            "name": "list_teams",
            "description": "列出所有可用的预定义 Team 和可组队的 Agent",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


def get_all_tools() -> List[Dict[str, Any]]:
    """获取完整工具列表：registry 工具 + 内置 subagent 工具"""
    return generate_tools_from_registry() + generate_subagent_tools()


# ==================== 工具分发 ====================

# 工具名 → 执行函数 的静态映射（用于快速分发）
_TOOL_DISPATCH = {}


def _build_tool_dispatch():
    """构建工具分发表 — 自动收集所有插件的 TOOL_HANDLERS + 内置 subagent handlers"""
    if _TOOL_DISPATCH:
        return

    registry = get_registry()

    # 自动收集所有插件的 TOOL_HANDLERS
    _TOOL_DISPATCH.update(registry.get_all_tool_handlers())

    # 内置 subagent 工具
    _TOOL_DISPATCH.update(_SUBAGENT_HANDLERS)

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
        from core.tool_use_runner import ToolUseRunner

        client, model = _get_llm_client()

        _LONG_RUNNING_TOOLS = get_registry().get_long_running_tools()
        _LONG_RUNNING_TOOLS.update({"run_team", "run_ad_hoc_team"})  # 内置 subagent 工具

        # Use ToolUseRunner pattern with SSE-compatible callbacks
        # For SSE we need fine-grained control per iteration, so we keep a customized loop
        current_messages = messages.copy()

        for _iteration in range(15):
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=_get_system_prompt(),
                tools=get_all_tools(),
                messages=current_messages
            )

            tool_calls = []
            text_content = ""

            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(block)

            if text_content:
                yield f"data: {json.dumps({'type': 'text', 'content': text_content})}\n\n"

            if not tool_calls or response.stop_reason == "end_turn":
                break

            tool_results = []
            for tool_call in tool_calls:
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_call.name, 'input': tool_call.input})}\n\n"

                if tool_call.name in _LONG_RUNNING_TOOLS:
                    yield f"data: {json.dumps({'type': 'progress', 'content': f'正在执行 {tool_call.name}，可能需要一些时间...'})}\n\n"

                result = await execute_tool(tool_call.name, dict(tool_call.input))

                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_call.name, 'result': result})}\n\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})
        else:
            yield f"data: {json.dumps({'type': 'text', 'content': '[已达到最大工具调用轮数，自动停止]'})}\n\n"

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
