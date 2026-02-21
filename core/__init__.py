"""
Core module - 共享基础设施

Registry 注册中心、BaseAgent 基类、注册辅助函数、
Orchestrator（流水线编排）、Chat Router（AI 对话）。
领域逻辑位于 plugins/ 目录。

所有具体类通过 auto_discover 注册，此处仅导出轻量基础设施。
"""

from .registry import Registry, ModuleRegistration, ModuleType, get_registry

__all__ = [
    'Registry',
    'ModuleRegistration',
    'ModuleType',
    'get_registry',
]
