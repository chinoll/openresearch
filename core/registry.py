"""
Module Registry - 模块注册中心（插件系统核心）

所有 Agent、Core Service、Manager、Router 通过声明 REGISTRATION 类属性
即可被自动发现、实例化、注入依赖，并暴露为 API 工具。
"""

import importlib
import inspect
import logging
import pkgutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 枚举 ====================

class ModuleType(Enum):
    """模块类型"""
    AGENT = "agent"
    CORE_SERVICE = "core_service"
    MANAGER = "manager"
    ROUTER = "router"
    TOOL = "tool"            # 简单函数调用（CRUD、搜索、提取）
    SUBAGENT = "subagent"    # 复杂多 Agent 协作（Team）


# 所有可提供 LLM 工具的模块类型
TOOL_PROVIDING_TYPES = {ModuleType.ROUTER, ModuleType.TOOL, ModuleType.SUBAGENT}


# ==================== 注册数据结构 ====================

@dataclass
class DependencySpec:
    """依赖声明"""
    name: str                    # 要依赖的模块注册名
    optional: bool = False       # 是否可选依赖


@dataclass
class InputSchema:
    """输入字段定义"""
    name: str
    type: str = "str"
    description: str = ""
    required: bool = True
    default: Any = None
    enum_values: List[str] = field(default_factory=list)


@dataclass
class OutputSchema:
    """输出字段定义"""
    name: str
    type: str = "str"
    description: str = ""


@dataclass
class Capability:
    """能力声明"""
    name: str                    # 机器标识，如 "ingest_arxiv"
    description: str = ""        # 人类/LLM 可读描述
    input_schema: List[InputSchema] = field(default_factory=list)
    output_schema: List[OutputSchema] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class ConstructorParam:
    """构造参数（非依赖注入的参数）"""
    name: str                    # 参数名
    from_config: str = ""        # 从 config YAML 中的点分路径读取
    default: Any = None          # 默认值


@dataclass
class TeamExport:
    """跨插件 Team 导出声明 — 声明 agent 可参与 Team 协作"""
    default_role: str           # 在 team 中的默认角色名
    description: str = ""       # 在 team 中的能力描述


@dataclass
class ModuleRegistration:
    """模块注册元数据"""

    # ===== 身份标识 =====
    name: str                    # 全局唯一键
    module_type: ModuleType      # agent | core_service | manager | router
    version: str = "1.0.0"

    # ===== 供 LLM 路由理解的描述 =====
    display_name: str = ""
    description: str = ""

    # ===== 能力声明 =====
    capabilities: List[Capability] = field(default_factory=list)

    # ===== 依赖声明 =====
    dependencies: List[DependencySpec] = field(default_factory=list)

    # ===== 构造参数 =====
    constructor_params: List[ConstructorParam] = field(default_factory=list)

    # ===== Router 专用 =====
    api_prefix: Optional[str] = None
    api_tags: List[str] = field(default_factory=list)

    # ===== Team 协作 =====
    team_export: Optional[TeamExport] = None   # 声明可参与 Team 协作

    # ===== 实例化 =====
    cls: Optional[Type] = None             # 自动绑定
    factory: Optional[Callable] = None     # 替代 cls 的工厂函数
    singleton: bool = True                 # 单例模式


# ==================== Registry 单例 ====================

class Registry:
    """模块注册中心（单例）"""

    _instance: Optional["Registry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._registrations: Dict[str, ModuleRegistration] = {}
        self._instances: Dict[str, Any] = {}
        self._capability_index: Dict[str, str] = {}   # capability_name -> module_name
        self._tag_index: Dict[str, List[str]] = {}     # tag -> [module_names]
        self._source_modules: Dict[str, Any] = {}      # reg_name -> Python module 对象
        self._team_definitions: Dict[str, Any] = {}    # team_name -> TeamDefinition

    def register(self, reg: ModuleRegistration):
        """注册模块（同 class 重复注册静默跳过）"""
        existing = self._registrations.get(reg.name)
        if existing is not None:
            if existing.cls is not None and existing.cls is reg.cls:
                return  # 同一个类，跳过
            logger.debug(f"Module re-registered: {reg.name}")

        self._registrations[reg.name] = reg

        # 建立 capability 索引
        for cap in reg.capabilities:
            self._capability_index[cap.name] = reg.name
            # 建立 tag 索引
            for tag in cap.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                if reg.name not in self._tag_index[tag]:
                    self._tag_index[tag].append(reg.name)

        logger.debug(f"Registered module: {reg.name} ({reg.module_type.value})")

    def unregister(self, name: str):
        """注销模块"""
        reg = self._registrations.pop(name, None)
        if reg:
            # 清理 capability 索引
            for cap in reg.capabilities:
                self._capability_index.pop(cap.name, None)
                for tag in cap.tags:
                    if tag in self._tag_index and name in self._tag_index[tag]:
                        self._tag_index[tag].remove(name)
            # 清理实例缓存
            self._instances.pop(name, None)
            logger.debug(f"Unregistered module: {name}")

    def get_registration(self, name: str) -> Optional[ModuleRegistration]:
        """按名称查询注册"""
        return self._registrations.get(name)

    def get_all_registrations(self, module_type: ModuleType = None) -> List[ModuleRegistration]:
        """列出所有注册，可按类型过滤"""
        regs = list(self._registrations.values())
        if module_type is not None:
            regs = [r for r in regs if r.module_type == module_type]
        return regs

    def find_by_capability(self, name: str) -> Optional[ModuleRegistration]:
        """按能力名查找归属模块"""
        module_name = self._capability_index.get(name)
        if module_name:
            return self._registrations.get(module_name)
        return None

    def find_by_tag(self, tag: str) -> List[ModuleRegistration]:
        """按标签查找模块列表"""
        module_names = self._tag_index.get(tag, [])
        return [self._registrations[n] for n in module_names if n in self._registrations]

    def describe_capabilities(self) -> str:
        """生成人类可读的能力描述文本（供 orchestrator LLM 路由），按 TOOL / SUBAGENT 分组"""
        tool_lines = []
        subagent_lines = []

        for reg in self._registrations.values():
            if not reg.capabilities:
                continue

            section = f"\n### {reg.display_name or reg.name}"
            if reg.description:
                section += f"\n  {reg.description}"
            for cap in reg.capabilities:
                section += f"\n  - {cap.name}: {cap.description}"
                if cap.tags:
                    section += f"\n    tags: {', '.join(cap.tags)}"

            if reg.module_type == ModuleType.SUBAGENT:
                subagent_lines.append(section)
            elif reg.module_type in (ModuleType.TOOL, ModuleType.ROUTER):
                tool_lines.append(section)

        lines = []
        if tool_lines:
            lines.append("\n## 原子工具（优先使用）")
            lines.extend(tool_lines)
        if subagent_lines:
            lines.append("\n## 子 Agent 协作（仅在原子工具无法完成时使用）")
            lines.extend(subagent_lines)
        return "\n".join(lines)

    def get_instance(self, name: str, config: dict = None) -> Any:
        """
        获取/创建实例，自动递归解析依赖，从 config 读取构造参数。

        Args:
            name: 模块注册名
            config: 应用配置字典（用于读取 constructor_params 的 from_config 路径）

        Returns:
            模块实例
        """
        # 检查缓存
        if name in self._instances:
            return self._instances[name]

        reg = self._registrations.get(name)
        if not reg:
            raise KeyError(f"Module not registered: {name}")

        if not reg.cls and not reg.factory:
            raise ValueError(f"Module {name} has no cls or factory defined")

        config = config or {}

        # 递归解析依赖
        dep_kwargs = {}
        for dep_spec in reg.dependencies:
            try:
                dep_instance = self.get_instance(dep_spec.name, config)
                dep_kwargs[dep_spec.name] = dep_instance
            except (KeyError, ValueError) as e:
                if dep_spec.optional:
                    logger.debug(f"Optional dependency {dep_spec.name} not available: {e}")
                else:
                    raise

        # 从 config 读取构造参数
        ctor_kwargs = {}
        for param in reg.constructor_params:
            value = param.default
            if param.from_config:
                value = _get_nested_config(config, param.from_config, param.default)
            ctor_kwargs[param.name] = value

        # 合并依赖和构造参数
        kwargs = {**ctor_kwargs, **dep_kwargs}

        # 使用工厂或直接实例化
        if reg.factory:
            instance = reg.factory(**kwargs)
        else:
            instance = reg.cls(**kwargs)

        # 缓存单例
        if reg.singleton:
            self._instances[name] = instance

        logger.debug(f"Created instance: {name}")
        return instance

    def set_instance(self, name: str, instance: Any):
        """手动注入实例（用于测试或外部构建的对象）"""
        self._instances[name] = instance

    def auto_discover(self, package_paths: List[str]):
        """
        扫描指定 Python 包，寻找带 REGISTRATION 属性的类并注册。

        Args:
            package_paths: 包路径列表，如 ['agents', 'core']
        """
        for package_path in package_paths:
            try:
                package = importlib.import_module(package_path)
            except ImportError as e:
                logger.warning(f"Cannot import package {package_path}: {e}")
                continue

            package_dir = getattr(package, '__path__', None)
            if not package_dir:
                # 非包，直接扫描模块
                self._scan_module(package)
                continue

            for importer, modname, ispkg in pkgutil.walk_packages(
                package_dir, prefix=package_path + "."
            ):
                try:
                    module = importlib.import_module(modname)
                    self._scan_module(module)
                except ImportError as e:
                    logger.debug(f"Cannot import module {modname}: {e}")

    def _scan_module(self, module):
        """扫描模块中的注册"""
        for attr_name in dir(module):
            obj = getattr(module, attr_name)

            # 类级别 REGISTRATION
            if inspect.isclass(obj) and hasattr(obj, 'REGISTRATION'):
                reg = obj.REGISTRATION
                if isinstance(reg, ModuleRegistration) and reg.name:
                    if reg.cls is None:
                        reg.cls = obj
                    self.register(reg)
                    self._source_modules[reg.name] = module

            # 模块级别 ROUTER_REGISTRATION
            if attr_name == 'ROUTER_REGISTRATION' and isinstance(obj, ModuleRegistration):
                # 对于 router，cls 保留为 None（路由是模块级对象）
                self.register(obj)
                self._source_modules[obj.name] = module

        # 模块级别 TEAM_DEFINITIONS（Team 预定义列表）
        team_defs = getattr(module, 'TEAM_DEFINITIONS', None)
        if team_defs and isinstance(team_defs, list):
            for td in team_defs:
                if hasattr(td, 'name') and td.name:
                    self._team_definitions[td.name] = td
                    logger.debug(f"Registered team definition: {td.name}")

    def get_router_objects(self) -> list:
        """返回 [(reg, router_obj), ...] — 所有可提供工具的模块中有 FastAPI router 的"""
        result = []
        for reg in self._registrations.values():
            if reg.module_type not in TOOL_PROVIDING_TYPES:
                continue
            module = self._source_modules.get(reg.name)
            if module and hasattr(module, 'router'):
                result.append((reg, module.router))
        return result

    def get_all_tool_handlers(self) -> Dict[str, Callable]:
        """合并所有可提供工具的模块的 TOOL_HANDLERS 字典"""
        handlers = {}
        for reg in self._registrations.values():
            if reg.module_type not in TOOL_PROVIDING_TYPES:
                continue
            module = self._source_modules.get(reg.name)
            if module and hasattr(module, 'TOOL_HANDLERS'):
                handlers.update(module.TOOL_HANDLERS)
        return handlers

    def get_stats_handlers(self) -> Dict[str, Callable]:
        """收集所有可提供工具的模块的 get_stats 函数，以领域名为 key"""
        handlers = {}
        for reg in self._registrations.values():
            if reg.module_type not in TOOL_PROVIDING_TYPES:
                continue
            module = self._source_modules.get(reg.name)
            if module and hasattr(module, 'get_stats'):
                # 用注册名去掉 _router 后缀作为 domain key
                domain = reg.name.replace('_router', '')
                handlers[domain] = module.get_stats
        return handlers

    # ==================== Team 查询 ====================

    def get_team_definition(self, name: str):
        """按名称获取 TeamDefinition"""
        return self._team_definitions.get(name)

    def get_all_team_definitions(self) -> Dict[str, Any]:
        """返回所有已注册的 TeamDefinition"""
        return dict(self._team_definitions)

    def get_team_ready_agents(self) -> List[ModuleRegistration]:
        """返回所有声明了 team_export 的 Agent 注册"""
        return [
            reg for reg in self._registrations.values()
            if reg.team_export is not None
        ]

    def reset(self):
        """重置注册中心（用于测试）"""
        self._registrations.clear()
        self._instances.clear()
        self._capability_index.clear()
        self._tag_index.clear()
        self._source_modules.clear()
        self._team_definitions.clear()


# ==================== 辅助函数 ====================

def _get_nested_config(config: dict, dotted_path: str, default: Any = None) -> Any:
    """从嵌套 config 字典中按点分路径读取值"""
    keys = dotted_path.split(".")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def get_registry() -> Registry:
    """获取全局 Registry 单例"""
    return Registry()
