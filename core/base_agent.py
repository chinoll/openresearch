"""
Base Agent - 所有 Agent 的基类
提供 LLM 调用、状态管理等通用功能
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, List, Optional, Any, TYPE_CHECKING
import logging
import re
import time
from dataclasses import dataclass
import json

if TYPE_CHECKING:
    from core.registry import ModuleRegistration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str
    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: Optional[str] = None
    provider: Optional[str] = None   # "anthropic" | "openai" | None (auto-detect)
    base_url: Optional[str] = None   # Custom endpoint; None = SDK default


class BaseAgent(ABC):
    """Agent 基类"""

    REGISTRATION: ClassVar[Optional["ModuleRegistration"]] = None

    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.llm_client = self._init_llm_client()
        self.memory: List[Dict] = []  # 对话历史

    def _resolve_provider(self) -> str:
        """确定 LLM 提供商：优先使用显式 provider，否则从 model 名推断"""
        if self.config.provider:
            return self.config.provider
        model_lower = self.config.model.lower()
        if "claude" in model_lower:
            return "anthropic"
        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            return "openai"
        # Default to openai for unknown models (OpenAI-compatible API is the most common)
        return "openai"

    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        provider = self._resolve_provider()
        try:
            if provider == "anthropic":
                from anthropic import Anthropic
                kwargs = {}
                if self.config.api_key:
                    kwargs["api_key"] = self.config.api_key
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                return Anthropic(**kwargs)
            else:
                from openai import OpenAI
                kwargs = {}
                if self.config.api_key:
                    kwargs["api_key"] = self.config.api_key
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                return OpenAI(**kwargs)
        except ImportError as e:
            logger.warning(f"LLM client not available: {e}")
        return None

    @abstractmethod
    async def process(self, input_data: Dict) -> Dict:
        """
        处理输入数据（子类必须实现）

        Args:
            input_data: 输入数据

        Returns:
            处理结果
        """
        pass

    def call_llm(self, prompt: str, system_prompt: Optional[str] = None,
                 max_retries: int = 2) -> str:
        """
        调用 LLM（带指数退避重试）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_retries: 最大重试次数

        Returns:
            LLM 响应
        """
        if not self.llm_client:
            logger.warning("LLM client not initialized, returning empty response")
            return ""

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if hasattr(self.llm_client, 'messages'):
                    # Anthropic Claude
                    messages = [{"role": "user", "content": prompt}]
                    response = self.llm_client.messages.create(
                        model=self.config.model,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                        system=system_prompt or "",
                        messages=messages
                    )
                    return response.content[0].text
                else:
                    # OpenAI
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    response = self.llm_client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens
                    )
                    return response.choices[0].message.content

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2 ** attempt
                    self.log(f"LLM call failed (attempt {attempt+1}), retrying in {wait}s: {e}", "warning")
                    time.sleep(wait)

        logger.error(f"LLM call failed after {max_retries+1} attempts: {last_error}")
        return ""

    def call_llm_structured(self, prompt: str, schema: Dict[str, Any],
                            tool_name: str = "extract",
                            system_prompt: Optional[str] = None,
                            max_retries: int = 2) -> Dict:
        """
        调用 LLM 并强制返回结构化 JSON（通过 tool_use 机制）

        Anthropic: 使用 tool_choice 强制调用指定 tool，从 tool_use block 提取 input
        OpenAI: 使用 function calling，从 tool_calls[0].function.arguments 解析

        Args:
            prompt: 用户提示词
            schema: JSON Schema 定义输出结构
            tool_name: 虚拟工具名称
            system_prompt: 系统提示词
            max_retries: 最大重试次数

        Returns:
            结构化 JSON 结果
        """
        if not self.llm_client:
            logger.warning("LLM client not initialized, returning empty dict")
            return {}

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if hasattr(self.llm_client, 'messages'):
                    # Anthropic — tool_use 强制结构化输出
                    tool_def = {
                        "name": tool_name,
                        "description": f"Extract structured data according to the schema",
                        "input_schema": schema,
                    }
                    messages = [{"role": "user", "content": prompt}]
                    response = self.llm_client.messages.create(
                        model=self.config.model,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                        system=system_prompt or "",
                        messages=messages,
                        tools=[tool_def],
                        tool_choice={"type": "tool", "name": tool_name},
                    )
                    # 从 tool_use block 提取结构化数据
                    for block in response.content:
                        if block.type == "tool_use":
                            result = block.input
                            self._validate_schema(result, schema)
                            return result

                    # 回退：尝试从文本中解析
                    for block in response.content:
                        if block.type == "text":
                            return self._parse_json_response(block.text, default={})
                    return {}

                else:
                    # OpenAI — function calling
                    func_def = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": "Extract structured data",
                            "parameters": schema,
                        },
                    }
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})

                    response = self.llm_client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        tools=[func_def],
                        tool_choice={"type": "function", "function": {"name": tool_name}},
                    )
                    msg = response.choices[0].message
                    if msg.tool_calls:
                        raw = msg.tool_calls[0].function.arguments
                        result = json.loads(raw)
                        self._validate_schema(result, schema)
                        return result

                    # 回退：从文本解析
                    if msg.content:
                        return self._parse_json_response(msg.content, default={})
                    return {}

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2 ** attempt
                    self.log(f"Structured LLM call failed (attempt {attempt+1}), retrying in {wait}s: {e}", "warning")
                    time.sleep(wait)

        logger.error(f"Structured LLM call failed after {max_retries+1} attempts: {last_error}")
        return {}

    def _validate_schema(self, data: Any, schema: Dict[str, Any]):
        """可选 JSON Schema 校验（如果安装了 jsonschema）"""
        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=schema)
        except ImportError:
            pass  # jsonschema 未安装，跳过校验
        except Exception as e:
            self.log(f"Schema validation warning: {e}", "warning")

    def _parse_json_response(self, response: str, default: Any = None) -> Any:
        """
        从 LLM 文本响应中提取 JSON（支持 object {} 和 array []）

        使用括号深度计数而非正则，正确处理嵌套结构。
        """
        if not response:
            return default if default is not None else {}

        # 1. 先尝试 markdown 代码块
        code_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', response)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 2. 使用括号深度计数提取第一个完整的 JSON object 或 array
        for open_char, close_char in [('{', '}'), ('[', ']')]:
            start = response.find(open_char)
            if start == -1:
                continue

            depth = 0
            in_string = False
            escape_next = False

            for i in range(start, len(response)):
                ch = response[i]

                if escape_next:
                    escape_next = False
                    continue

                if ch == '\\' and in_string:
                    escape_next = True
                    continue

                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if ch == open_char:
                    depth += 1
                elif ch == close_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(response[start:i + 1])
                        except json.JSONDecodeError:
                            break

        # 3. 最后尝试直接解析整个响应
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        self.log("Failed to parse JSON from response", "warning")
        return default if default is not None else {}

    def add_to_memory(self, role: str, content: str):
        """添加到记忆"""
        self.memory.append({
            "role": role,
            "content": content
        })

    def get_memory(self, last_n: Optional[int] = None) -> List[Dict]:
        """获取记忆"""
        if last_n:
            return self.memory[-last_n:]
        return self.memory

    def clear_memory(self):
        """清空记忆"""
        self.memory = []

    def log(self, message: str, level: str = "info"):
        """日志记录"""
        log_msg = f"[{self.name}] {message}"
        if level == "info":
            logger.info(log_msg)
        elif level == "warning":
            logger.warning(log_msg)
        elif level == "error":
            logger.error(log_msg)
        elif level == "debug":
            logger.debug(log_msg)


class AgentResponse:
    """Agent 响应封装"""

    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }

    def __repr__(self):
        return f"AgentResponse(success={self.success}, error={self.error})"
