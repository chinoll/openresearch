"""
Registration Helpers - 便捷装饰器和工厂函数

提供 @register_module 装饰器和 agent_factory 工厂函数，
简化模块注册流程。
"""

import logging
from typing import Type

from core.registry import ModuleRegistration, get_registry

logger = logging.getLogger(__name__)


def register_module(reg: ModuleRegistration):
    """
    类装饰器：自动绑定 cls 并调用 registry.register()。

    用法:
        @register_module(ModuleRegistration(name="my_module", ...))
        class MyModule:
            ...
    """
    def decorator(cls: Type) -> Type:
        reg.cls = cls
        cls.REGISTRATION = reg
        get_registry().register(reg)
        return cls
    return decorator


def agent_factory(cls: Type, app_config: dict) -> object:
    """
    为 Agent 类生成实例，从 app_config 构建 AgentConfig 并与 DI 依赖合并。

    Args:
        cls: Agent 类（带 REGISTRATION 属性）
        app_config: 应用配置字典

    Returns:
        Agent 实例
    """
    from core.base_agent import AgentConfig

    llm_config = app_config.get('llm', {})

    agent_config = AgentConfig(
        name=cls.REGISTRATION.display_name or cls.__name__,
        model=llm_config.get('model', 'claude-sonnet-4-5-20250929'),
        temperature=llm_config.get('temperature', 0.7),
        max_tokens=llm_config.get('max_tokens', 4096),
        api_key=llm_config.get('api_key'),
        provider=llm_config.get('provider'),
        base_url=llm_config.get('base_url'),
    )

    # 收集依赖参数
    registry = get_registry()
    dep_kwargs = {}
    for dep_spec in cls.REGISTRATION.dependencies:
        try:
            dep_kwargs[dep_spec.name] = registry.get_instance(dep_spec.name, app_config)
        except (KeyError, ValueError):
            if not dep_spec.optional:
                raise

    # 收集构造参数
    from core.registry import _get_nested_config
    ctor_kwargs = {}
    for param in cls.REGISTRATION.constructor_params:
        value = param.default
        if param.from_config:
            value = _get_nested_config(app_config, param.from_config, param.default)
        ctor_kwargs[param.name] = value

    return cls(config=agent_config, **ctor_kwargs, **dep_kwargs)
