"""
Agent Team - 多 Agent 协同执行引擎

支持两种形式：
1. Form 1（同插件内 Team）: 同一 agent 不同 prompt/角色组队（如 extractor + critic）
2. Form 2（跨插件 Team）: 不同插件的 agent 协作（如 knowledge_extractor + insight_agent）

核心机制: LLM 协调 + 共享黑板 + 任务级生命周期
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.base_agent import AgentConfig, BaseAgent
from core.team_schemas import COORDINATOR_DECISION_SCHEMA
from prompts.loader import load as load_prompt

logger = logging.getLogger(__name__)


# ==================== 共享黑板 ====================

@dataclass
class BlackboardEntry:
    """黑板条目"""
    key: str
    value: Any
    writer: str       # 写入者角色名
    turn: int         # 写入轮次
    summary: str      # 值摘要（供 coordinator 快速浏览，省 token）


class TeamContext:
    """
    团队共享黑板 — 成员间信息传递的中心。

    Coordinator 只看 get_summary()（key + writer + 摘要）以节省 token，
    成员通过 read_many() 获取完整数据。
    """

    def __init__(self, task_description: str):
        self.task_description = task_description
        self._entries: Dict[str, BlackboardEntry] = {}
        self.turn: int = 0
        self.history: List[Dict] = []

    def write(self, key: str, value: Any, writer: str, summary: str = ""):
        """写入黑板条目"""
        if not summary:
            summary = self._auto_summary(value)
        self._entries[key] = BlackboardEntry(
            key=key, value=value, writer=writer,
            turn=self.turn, summary=summary,
        )

    def read(self, key: str) -> Any:
        """读取单个 key 的值"""
        entry = self._entries.get(key)
        return entry.value if entry else None

    def read_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量读取多个 key 的值"""
        return {k: self.read(k) for k in keys if self.read(k) is not None}

    def get_summary(self) -> str:
        """返回黑板摘要（仅 key + writer + 摘要，不含完整 value）"""
        if not self._entries:
            return "（黑板为空，尚无数据）"

        lines = []
        for entry in self._entries.values():
            lines.append(f"- **{entry.key}** (由 {entry.writer} 在第 {entry.turn} 轮写入): {entry.summary}")
        return "\n".join(lines)

    def get_all_keys(self) -> List[str]:
        """返回所有 key 名"""
        return list(self._entries.keys())

    def get_full_result(self) -> Dict[str, Any]:
        """返回黑板所有数据（用于最终结果）"""
        return {k: e.value for k, e in self._entries.items()}

    def add_history(self, turn: int, role: str, action: str, detail: str = ""):
        """记录执行历史"""
        self.history.append({
            "turn": turn,
            "role": role,
            "action": action,
            "detail": detail,
        })

    def get_history_summary(self) -> str:
        """返回历史摘要"""
        if not self.history:
            return "（无历史记录）"

        lines = []
        for h in self.history:
            lines.append(f"Turn {h['turn']}: [{h['role']}] {h['action']}"
                         + (f" — {h['detail']}" if h['detail'] else ""))
        return "\n".join(lines)

    @staticmethod
    def _auto_summary(value: Any) -> str:
        """自动生成值摘要"""
        if isinstance(value, str):
            return value[:120] + ("..." if len(value) > 120 else "")
        if isinstance(value, dict):
            keys = list(value.keys())[:5]
            return f"dict with keys: {keys}"
        if isinstance(value, list):
            return f"list with {len(value)} items"
        return str(value)[:120]


# ==================== Team 成员定义 ====================

@dataclass
class TeamMemberSpec:
    """Team 成员规格（用于 TEAM_DEFINITIONS 声明式定义）"""
    role: str                              # 团队内唯一角色名
    agent_name: str                        # Registry 注册名
    system_prompt_override: str = ""       # Form 1 核心：同 agent 不同角色
    description: str = ""                  # 在 team 中的能力描述


@dataclass
class TeamDefinition:
    """预定义 Team（插件导出）"""
    name: str                              # 全局唯一 team 名
    display_name: str = ""
    description: str = ""
    members: List[TeamMemberSpec] = field(default_factory=list)
    default_max_turns: int = 10
    tags: List[str] = field(default_factory=list)


@dataclass
class TeamMember:
    """运行时 Team 成员（持有实际 agent 实例）"""
    role: str
    agent: BaseAgent
    description: str = ""


# ==================== Team Agent Wrapper（Form 1 关键） ====================

class TeamAgentWrapper(BaseAgent):
    """
    包装已有 agent，覆盖 system prompt，支持递归研究能力。

    Form 1 的关键：同一个 agent 类，不同的 system prompt 扮演不同角色。
    无需修改原 agent 代码。

    当 recursion_depth < max_recursion_depth 时，agent 在处理 team_instruction
    时可通过 `research` 工具发起递归 chat（带完整工具权限），自主查找外部信息。
    """

    def __init__(
        self,
        agent: BaseAgent,
        system_prompt_override: str = "",
        recursion_depth: int = 0,
        max_recursion_depth: int = 2,
    ):
        # 不调用 super().__init__，直接复用被包装 agent 的属性
        self.config = agent.config
        self.name = agent.name
        self.llm_client = agent.llm_client
        self.memory: List[Dict] = []
        self._wrapped_agent = agent
        self._system_prompt_override = system_prompt_override
        self._recursion_depth = recursion_depth
        self._max_recursion_depth = max_recursion_depth
        self._research_logs: List[str] = []  # 元摘要记录

    def _get_system_prompt(self) -> str:
        """获取系统提示词：优先使用覆盖值，否则尝试取原 agent 的"""
        if self._system_prompt_override:
            return self._system_prompt_override
        getter = getattr(self._wrapped_agent, '_get_system_prompt', None)
        if getter:
            return getter()
        return ""

    async def process(self, input_data: Dict) -> Dict:
        """
        委派给被包装 agent 的 process 方法。

        如果 input_data 包含 team_instruction：
        - depth < max_depth: 使用 ToolUseRunner + research 工具执行（可递归查资料）
        - depth >= max_depth: 退化为 call_llm（纯推理）

        否则直接委派给原 agent。
        """
        team_instruction = input_data.get("team_instruction", "")
        team_context_data = input_data.get("team_context", {})

        if team_instruction:
            context_text = ""
            if team_context_data:
                context_text = "\n\n## 可用数据\n" + json.dumps(
                    team_context_data, ensure_ascii=False, indent=2
                )[:3000]

            prompt = f"{team_instruction}{context_text}"
            system_prompt = self._get_system_prompt()

            # 递归能力：depth < max_depth 时使用 ToolUseRunner + research 工具
            if self._recursion_depth < self._max_recursion_depth:
                result = await self._process_with_research(prompt, system_prompt)
            else:
                # 退化为纯 call_llm
                result = self._process_plain(prompt, system_prompt)

            return result

        # 无 team_instruction，直接委派给原 agent
        return await self._wrapped_agent.process(input_data)

    async def _process_with_research(self, prompt: str, system_prompt: str) -> Dict:
        """使用 ToolUseRunner + research 工具处理指令"""
        from core.recursive_chat import RESEARCH_TOOL_DEF, run_recursive_chat
        from core.tool_use_runner import ToolUseRunner

        research_logs = []

        async def _execute_tool(tool_name: str, tool_input: Dict) -> Any:
            """research 工具处理器"""
            if tool_name == "research":
                sub_result = await run_recursive_chat(
                    query=tool_input.get("query", ""),
                    context=tool_input.get("context", ""),
                    depth=self._recursion_depth,
                    max_depth=self._max_recursion_depth,
                )
                research_logs.append(sub_result.get("meta_summary", ""))
                # 返回完整结果给 agent
                return sub_result["result"]
            return {"error": f"未知工具: {tool_name}"}

        messages = [{"role": "user", "content": prompt}]

        runner = ToolUseRunner(
            client=self.llm_client,
            model=self.config.model,
            system_prompt=system_prompt,
            tools=[RESEARCH_TOOL_DEF],
            execute_tool=_execute_tool,
            max_iterations=5,
        )

        response = await runner.run(messages)

        # 记录元摘要
        self._research_logs.extend(research_logs)

        # 尝试解析为结构化数据
        parsed = self._parse_json_response(response, default=None)
        result = {"success": True, "data": parsed if parsed is not None else response}

        if research_logs:
            result["research_meta"] = research_logs

        return result

    def _process_plain(self, prompt: str, system_prompt: str) -> Dict:
        """纯 call_llm 处理（无递归能力）"""
        response = self.call_llm(prompt, system_prompt)

        parsed = self._parse_json_response(response, default=None)
        if parsed is not None:
            return {"success": True, "data": parsed}
        return {"success": True, "data": response}


# ==================== Coordinator（LLM 协调者） ====================

@dataclass
class CoordinatorDecision:
    """协调者决策"""
    action: str             # "delegate" | "terminate"
    member_role: str = ""   # 委派给谁
    input_keys: List[str] = field(default_factory=list)
    instruction: str = ""   # 给成员的指令
    output_key: str = ""    # 结果写入哪个 key
    reasoning: str = ""     # 决策理由


class TeamCoordinator:
    """
    使用 LLM 的结构化输出决策下一步行动。

    每轮调用 call_llm_structured() + COORDINATOR_DECISION_SCHEMA。
    """

    def __init__(self, config: AgentConfig):
        self._agent = _CoordinatorAgent(config)

    def decide_next(
        self,
        context: TeamContext,
        members: List[TeamMember],
        max_turns: int,
    ) -> CoordinatorDecision:
        """根据当前状态决定下一步"""
        members_desc = "\n".join(
            f"- **{m.role}**: {m.description or '(无描述)'}"
            for m in members
        )

        prompt = load_prompt(
            "team/coordinator",
            task_description=context.task_description,
            members_description=members_desc,
            blackboard_summary=context.get_summary(),
            history_summary=context.get_history_summary(),
            current_turn=str(context.turn),
            max_turns=str(max_turns),
        )

        system_prompt = load_prompt("system/team_coordinator")

        result = self._agent.call_llm_structured(
            prompt, COORDINATOR_DECISION_SCHEMA,
            tool_name="coordinator_decision",
            system_prompt=system_prompt,
        )

        return CoordinatorDecision(
            action=result.get("action", "terminate"),
            member_role=result.get("member_role", ""),
            input_keys=result.get("input_keys", []),
            instruction=result.get("instruction", ""),
            output_key=result.get("output_key", ""),
            reasoning=result.get("reasoning", ""),
        )


class _CoordinatorAgent(BaseAgent):
    """Coordinator 内部使用的 BaseAgent 子类（提供 LLM 调用能力）"""

    async def process(self, input_data: Dict) -> Dict:
        # Coordinator 不需要 process，仅用 call_llm_structured
        return {}


# ==================== Team 执行引擎 ====================

class Team:
    """
    Team 执行引擎

    循环调用 coordinator 决策，委派成员执行，通过黑板传递数据。
    """

    def __init__(
        self,
        name: str,
        members: List[TeamMember],
        coordinator: TeamCoordinator,
        max_turns: int = 10,
    ):
        self.name = name
        self.members = {m.role: m for m in members}
        self.coordinator = coordinator
        self.max_turns = max_turns

    async def run(self, task: str, initial_data: Dict = None) -> Dict:
        """
        运行 Team

        Args:
            task: 任务描述
            initial_data: 初始数据（写入黑板）

        Returns:
            {success, turns_used, blackboard, history}
        """
        context = TeamContext(task_description=task)

        # 注入初始数据
        if initial_data:
            for key, value in initial_data.items():
                context.write(key, value, writer="initial", summary=f"初始数据: {key}")

        logger.info(f"[Team:{self.name}] 开始执行，任务: {task[:80]}...")

        for turn in range(self.max_turns):
            context.turn = turn

            # Coordinator 决策
            try:
                decision = self.coordinator.decide_next(context, list(self.members.values()), self.max_turns)
            except Exception as e:
                logger.error(f"[Team:{self.name}] Coordinator 决策失败: {e}")
                context.add_history(turn, "coordinator", "error", str(e))
                break

            context.add_history(
                turn, "coordinator",
                f"{decision.action} → {decision.member_role}" if decision.action == "delegate" else "terminate",
                decision.reasoning,
            )

            logger.info(
                f"[Team:{self.name}] Turn {turn}: "
                f"{decision.action} {decision.member_role or ''} — {decision.reasoning[:60]}"
            )

            # 终止
            if decision.action == "terminate":
                break

            # 委派
            if decision.action == "delegate":
                member = self.members.get(decision.member_role)
                if not member:
                    error_msg = f"未知成员角色: {decision.member_role}"
                    logger.warning(f"[Team:{self.name}] {error_msg}")
                    context.write(
                        decision.output_key or f"error_turn{turn}",
                        {"error": error_msg},
                        writer="coordinator",
                        summary=error_msg,
                    )
                    continue

                # 从黑板选择性读取数据
                selected_data = context.read_many(decision.input_keys) if decision.input_keys else {}

                # 构建 agent input
                agent_input = {
                    **selected_data,
                    "team_instruction": decision.instruction,
                    "team_context": selected_data,
                }

                # 执行
                try:
                    result = await member.agent.process(agent_input)
                except Exception as e:
                    result = {"success": False, "error": str(e)}
                    logger.error(f"[Team:{self.name}] 成员 {decision.member_role} 执行失败: {e}")

                # 写入黑板
                output_key = decision.output_key or f"result_{decision.member_role}_turn{turn}"
                result_summary = ""
                if isinstance(result, dict):
                    if result.get("success") is False:
                        result_summary = f"错误: {result.get('error', 'unknown')}"
                    elif "data" in result:
                        result_summary = TeamContext._auto_summary(result["data"])
                    else:
                        result_summary = TeamContext._auto_summary(result)
                else:
                    result_summary = TeamContext._auto_summary(result)

                context.write(output_key, result, writer=decision.member_role, summary=result_summary)
                context.add_history(turn, decision.member_role, f"完成 → {output_key}", result_summary[:80])

        turns_used = context.turn + 1
        logger.info(f"[Team:{self.name}] 执行完毕，共 {turns_used} 轮")

        return {
            "success": True,
            "team_name": self.name,
            "turns_used": turns_used,
            "blackboard": context.get_full_result(),
            "history": context.history,
        }


# ==================== 工厂函数 ====================

def create_team_from_definition(
    team_def: TeamDefinition,
    app_config: dict,
    max_turns: int = None,
    max_recursion_depth: int = 2,
    recursion_depth: int = 0,
) -> Team:
    """
    从 TeamDefinition 创建 Team 实例

    Args:
        team_def: 预定义 Team
        app_config: 应用配置
        max_turns: 覆盖默认 max_turns
        max_recursion_depth: agent 递归研究的最大深度
        recursion_depth: 当前递归深度（由递归 chat 传入）
    """
    from core.registration import agent_factory
    from core.registry import get_registry

    registry = get_registry()
    members = []

    for spec in team_def.members:
        reg = registry.get_registration(spec.agent_name)
        if not reg or not reg.cls:
            raise RuntimeError(f"Agent not registered: {spec.agent_name}")

        agent = agent_factory(reg.cls, app_config)

        # 始终用 TeamAgentWrapper 包装（提供递归研究能力）
        agent = TeamAgentWrapper(
            agent,
            system_prompt_override=spec.system_prompt_override,
            recursion_depth=recursion_depth,
            max_recursion_depth=max_recursion_depth,
        )

        members.append(TeamMember(
            role=spec.role,
            agent=agent,
            description=spec.description,
        ))

    coordinator = _create_coordinator(app_config)

    return Team(
        name=team_def.name,
        members=members,
        coordinator=coordinator,
        max_turns=max_turns or team_def.default_max_turns,
    )


def create_ad_hoc_team(
    name: str,
    agent_names: List[str],
    app_config: dict,
    max_turns: int = 10,
    max_recursion_depth: int = 2,
    recursion_depth: int = 0,
) -> Team:
    """
    动态创建 ad-hoc Team（Form 2: 跨插件协作）

    使用 agent 的 team_export 信息确定角色名和描述。

    Args:
        name: Team 名称
        agent_names: Agent 注册名列表
        app_config: 应用配置
        max_turns: 最大轮次
        max_recursion_depth: agent 递归研究的最大深度
        recursion_depth: 当前递归深度（由递归 chat 传入）
    """
    from core.registration import agent_factory
    from core.registry import get_registry

    registry = get_registry()
    members = []

    for agent_name in agent_names:
        reg = registry.get_registration(agent_name)
        if not reg or not reg.cls:
            raise RuntimeError(f"Agent not registered: {agent_name}")

        agent = agent_factory(reg.cls, app_config)

        # 使用 team_export 确定角色信息
        team_export = getattr(reg, 'team_export', None)
        if team_export:
            role = team_export.default_role
            description = team_export.description
        else:
            role = agent_name
            description = reg.description or ""

        # 始终用 TeamAgentWrapper 包装（提供递归研究能力）
        agent = TeamAgentWrapper(
            agent,
            recursion_depth=recursion_depth,
            max_recursion_depth=max_recursion_depth,
        )

        members.append(TeamMember(
            role=role,
            agent=agent,
            description=description,
        ))

    coordinator = _create_coordinator(app_config)

    return Team(
        name=name,
        members=members,
        coordinator=coordinator,
        max_turns=max_turns,
    )


def _create_coordinator(app_config: dict) -> TeamCoordinator:
    """创建 Coordinator 实例"""
    llm_config = app_config.get('llm', {})
    config = AgentConfig(
        name="TeamCoordinator",
        model=llm_config.get('model', 'claude-sonnet-4-5-20250929'),
        temperature=0.3,  # coordinator 需要更确定性的决策
        max_tokens=llm_config.get('max_tokens', 4096),
        api_key=llm_config.get('api_key'),
        provider=llm_config.get('provider'),
        base_url=llm_config.get('base_url'),
    )
    return TeamCoordinator(config)
