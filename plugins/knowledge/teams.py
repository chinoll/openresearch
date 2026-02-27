"""
Knowledge Domain Team Definitions

Form 1 示例：同一 agent (knowledge_extractor) 扮演不同角色组队。
extractor 提取知识，critic（同 agent 不同 prompt）审查结果。
"""

from core.team import TeamDefinition, TeamMemberSpec


TEAM_DEFINITIONS = [
    TeamDefinition(
        name="knowledge_review",
        display_name="知识提取审查团队",
        description="提取知识后由 critic 审查准确性和完整性。extractor 负责提取，critic 负责审查并指出错误和遗漏。",
        members=[
            TeamMemberSpec(
                role="extractor",
                agent_name="knowledge_extractor",
                description="从论文提取结构化知识（贡献、方法论、发现等）",
            ),
            TeamMemberSpec(
                role="critic",
                agent_name="knowledge_extractor",
                system_prompt_override=(
                    "你是严格的学术审稿人。你的职责是审查知识提取结果的准确性和完整性。\n\n"
                    "## 审查准则\n\n"
                    "1. **准确性**：提取的信息是否在原文中有明确依据？是否有编造或过度推断？\n"
                    "2. **完整性**：是否遗漏了重要的贡献、方法、发现？\n"
                    "3. **一致性**：不同提取项之间是否存在矛盾？\n"
                    "4. **术语精确**：技术术语是否准确使用？\n"
                    "5. **区分原创与引用**：贡献是否真的属于本文，而非引用的前人工作？\n\n"
                    "对每个问题提供具体的修正建议，引用原文作为依据。\n"
                    "输出格式为 JSON，包含 issues（问题列表）和 suggestions（修正建议）。"
                ),
                description="审查提取结果的准确性，指出错误和遗漏",
            ),
        ],
        default_max_turns=6,
        tags=["knowledge", "review", "quality"],
    ),
]
