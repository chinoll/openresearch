"""
Team Coordination JSON Schemas

Coordinator 决策的 JSON Schema，供 BaseAgent.call_llm_structured() 使用。
"""

COORDINATOR_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["delegate", "terminate"],
            "description": "动作类型：delegate 委派给成员，terminate 终止团队执行",
        },
        "member_role": {
            "type": "string",
            "description": "委派给哪个成员（角色名）",
        },
        "input_keys": {
            "type": "array",
            "items": {"type": "string"},
            "description": "从黑板传递哪些 key 给成员（选择性传递，节省 token）",
        },
        "instruction": {
            "type": "string",
            "description": "给成员的具体指令",
        },
        "output_key": {
            "type": "string",
            "description": "成员结果写入黑板的 key 名",
        },
        "reasoning": {
            "type": "string",
            "description": "决策理由",
        },
    },
    "required": ["action", "reasoning"],
}
