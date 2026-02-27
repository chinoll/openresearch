"""
Team Router - Agent Team 工具

将 Team 功能暴露为 LLM 可调用的工具：run_team, run_ad_hoc_team, list_teams。
通过 ROUTER_REGISTRATION 自动被 registry 发现，工具自动注入 chat 工具列表。
"""

import logging
from typing import Dict

from core.registry import (
    ModuleRegistration, ModuleType, Capability, InputSchema,
    get_registry,
)

logger = logging.getLogger(__name__)

# ==================== Lazy init ====================

_app_config = None
_registry = None


def _ensure_init():
    """Lazy init: 加载配置、获取 registry"""
    global _app_config, _registry
    if _registry is not None:
        return
    from core.config import get_app_config
    _app_config = get_app_config()
    _registry = get_registry()


# ==================== Tool Handlers ====================

async def _h_run_team(tool_input: Dict) -> Dict:
    """运行预定义 Team"""
    _ensure_init()
    from core.team import create_team_from_definition

    team_name = tool_input.get("team_name", "")
    task = tool_input.get("task", "")
    initial_data = tool_input.get("initial_data") or {}
    max_turns = tool_input.get("max_turns")

    if not team_name:
        return {"error": "缺少 team_name 参数"}
    if not task:
        return {"error": "缺少 task 参数"}

    team_def = _registry.get_team_definition(team_name)
    if not team_def:
        available = list(_registry.get_all_team_definitions().keys())
        return {"error": f"未找到 Team: {team_name}，可用: {available}"}

    try:
        team = create_team_from_definition(team_def, _app_config, max_turns=max_turns)
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
    _ensure_init()
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
            app_config=_app_config,
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
    _ensure_init()

    # 预定义 Teams
    team_defs = _registry.get_all_team_definitions()
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
    team_ready = _registry.get_team_ready_agents()
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


# ==================== 注册 ====================

TOOL_HANDLERS = {
    "run_team": _h_run_team,
    "run_ad_hoc_team": _h_run_ad_hoc_team,
    "list_teams": _h_list_teams,
}

ROUTER_REGISTRATION = ModuleRegistration(
    name="team_router",
    module_type=ModuleType.ROUTER,
    display_name="Agent Team 工具",
    description="多 Agent 协同执行：预定义 Team 或动态组队，LLM 协调 + 共享黑板",
    capabilities=[
        Capability(
            name="run_team",
            description="运行预定义 Agent Team。Team 内多个 agent 协同完成任务，由 LLM 协调决策。",
            input_schema=[
                InputSchema(name="team_name", type="str",
                            description="Team 名称（通过 list_teams 获取）", required=True),
                InputSchema(name="task", type="str",
                            description="任务描述", required=True),
                InputSchema(name="initial_data", type="object",
                            description="初始数据（写入共享黑板）", required=False),
                InputSchema(name="max_turns", type="int",
                            description="最大执行轮数（覆盖默认值）", required=False),
            ],
            tags=["team", "collaboration"],
        ),
        Capability(
            name="run_ad_hoc_team",
            description="动态组建 Agent Team 并运行。选择多个 agent 临时组队协作完成任务。",
            input_schema=[
                InputSchema(name="agent_names", type="array",
                            description="Agent 注册名列表（至少 2 个）", required=True),
                InputSchema(name="task", type="str",
                            description="任务描述", required=True),
                InputSchema(name="initial_data", type="object",
                            description="初始数据（写入共享黑板）", required=False),
                InputSchema(name="max_turns", type="int",
                            description="最大执行轮数", default=10),
            ],
            tags=["team", "collaboration", "ad_hoc"],
        ),
        Capability(
            name="list_teams",
            description="列出所有可用的预定义 Team 和可组队的 Agent",
            input_schema=[],
            tags=["team", "discovery"],
        ),
    ],
)
