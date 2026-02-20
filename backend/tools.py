"""
AI 可调用工具定义
供 Anthropic tool_use API 使用

支持两种模式：
1. 静态 TOOLS 列表（向后兼容）
2. generate_tools_from_registry() 从 Registry 自动生成
"""

from typing import List, Dict, Any


def generate_tools_from_registry() -> List[Dict[str, Any]]:
    """
    从 Registry 中所有 ROUTER 类型注册的 capabilities 自动生成
    Anthropic tool_use 格式的工具定义。

    Returns:
        工具定义列表（Anthropic tool_use 格式）
    """
    from core.registry import get_registry, ModuleType

    registry = get_registry()
    router_regs = registry.get_all_registrations(ModuleType.ROUTER)

    tools = []
    for reg in router_regs:
        for cap in reg.capabilities:
            tool = {
                "name": cap.name,
                "description": cap.description,
                "input_schema": _capability_to_schema(cap),
            }
            tools.append(tool)

    return tools


def _capability_to_schema(cap) -> Dict[str, Any]:
    """将 Capability 的 input_schema 转换为 JSON Schema 格式"""
    if not cap.input_schema:
        return {"type": "object", "properties": {}}

    properties = {}
    required = []

    for field in cap.input_schema:
        prop = {"description": field.description}

        # 类型映射
        type_map = {
            "str": "string",
            "string": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "array": "array",
        }
        json_type = type_map.get(field.type, "string")
        prop["type"] = json_type

        if field.enum_values:
            prop["enum"] = field.enum_values

        if field.default is not None:
            prop["default"] = field.default

        if json_type == "array":
            prop["items"] = {"type": "string"}

        properties[field.name] = prop

        if field.required:
            required.append(field.name)

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required

    return schema


# ==================== 静态工具定义（向后兼容） ====================

TOOLS = [
    {
        "name": "download_paper",
        "description": "从 arXiv 下载论文（TeX 源文件优先）",
        "input_schema": {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "arXiv 论文 ID，如 1810.04805 或 1810_04805"
                }
            },
            "required": ["arxiv_id"]
        }
    },
    {
        "name": "list_papers",
        "description": "列出已下载的论文",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_paper_info",
        "description": "获取指定论文的详细信息（标题、作者、摘要、章节等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {
                    "type": "string",
                    "description": "论文 ID，如 1810_04805"
                }
            },
            "required": ["paper_id"]
        }
    },
    {
        "name": "create_insight",
        "description": "记录阅读论文时的洞察或观察",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "洞察内容"},
                "paper_id": {"type": "string", "description": "来源论文 ID"},
                "insight_type": {
                    "type": "string",
                    "enum": ["observation", "question", "connection", "surprise", "critique", "insight"],
                    "description": "洞察类型",
                    "default": "observation"
                },
                "importance": {"type": "integer", "minimum": 1, "maximum": 5, "description": "重要性 1-5", "default": 3},
                "section": {"type": "string", "description": "论文章节（可选）"}
            },
            "required": ["content", "paper_id"]
        }
    },
    {
        "name": "list_insights",
        "description": "列出洞察记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "按论文筛选（可选）"},
                "insight_type": {"type": "string", "description": "按类型筛选（可选）"},
                "unconverted_only": {"type": "boolean", "description": "只看未转化的洞察", "default": False}
            }
        }
    },
    {
        "name": "create_question",
        "description": "记录阅读论文时产生的疑问",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "疑问内容"},
                "paper_id": {"type": "string", "description": "来源论文 ID"},
                "question_type": {
                    "type": "string",
                    "enum": ["understanding", "method", "experiment", "application", "limitation", "extension", "comparison", "implementation"],
                    "description": "疑问类型",
                    "default": "understanding"
                },
                "importance": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                "section": {"type": "string", "description": "论文章节（可选）"},
                "context": {"type": "string", "description": "疑问上下文（可选）"}
            },
            "required": ["content", "paper_id"]
        }
    },
    {
        "name": "list_questions",
        "description": "列出疑问记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "按论文筛选（可选）"},
                "status": {
                    "type": "string",
                    "enum": ["unsolved", "partial", "solved"],
                    "description": "按状态筛选（可选）"
                },
                "question_type": {"type": "string", "description": "按类型筛选（可选）"},
                "min_importance": {"type": "integer", "description": "最低重要性（可选）"}
            }
        }
    },
    {
        "name": "add_answer",
        "description": "为疑问添加答案",
        "input_schema": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string", "description": "疑问 ID，如 q_0001"},
                "content": {"type": "string", "description": "答案内容"},
                "source": {"type": "string", "description": "答案来源（论文 ID 或 'own_thinking'）"},
                "section": {"type": "string", "description": "论文章节（可选）"},
                "quote": {"type": "string", "description": "相关引用（可选）"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.8}
            },
            "required": ["question_id", "content", "source"]
        }
    },
    {
        "name": "create_idea",
        "description": "记录研究想法",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "想法标题"},
                "content": {"type": "string", "description": "想法内容"},
                "paper_id": {"type": "string", "description": "相关论文 ID（可选）"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签（可选）"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "list_ideas",
        "description": "列出研究想法",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "按状态筛选（可选）"}
            }
        }
    },
    {
        "name": "start_reading_session",
        "description": "开始阅读一篇论文的会话，用于关联后续记录的洞察和疑问",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "要阅读的论文 ID"}
            },
            "required": ["paper_id"]
        }
    },
    {
        "name": "end_reading_session",
        "description": "结束当前阅读会话",
        "input_schema": {
            "type": "object",
            "properties": {
                "notes": {"type": "string", "description": "会话总结笔记（可选）"}
            }
        }
    },
    {
        "name": "get_statistics",
        "description": "获取系统统计数据（论文数、洞察数、疑问解决率等）",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]
