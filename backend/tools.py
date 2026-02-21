"""
AI 可调用工具定义
供 Anthropic tool_use API 使用

从 Registry 自动生成 Anthropic tool_use 格式的工具定义。
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
