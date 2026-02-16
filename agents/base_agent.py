"""
Base Agent - 所有 Agent 的基类
提供 LLM 调用、状态管理等通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
import json

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


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.llm_client = self._init_llm_client()
        self.memory: List[Dict] = []  # 对话历史

    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        # 这里可以根据配置初始化不同的 LLM
        # 暂时返回 None，在子类中实现
        try:
            if "claude" in self.config.model.lower():
                from anthropic import Anthropic
                return Anthropic(api_key=self.config.api_key)
            elif "gpt" in self.config.model.lower():
                from openai import OpenAI
                return OpenAI(api_key=self.config.api_key)
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

    def call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        调用 LLM

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            LLM 响应
        """
        if not self.llm_client:
            logger.warning("LLM client not initialized, returning empty response")
            return ""

        try:
            if isinstance(self.llm_client, object) and hasattr(self.llm_client, 'messages'):
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
            logger.error(f"Error calling LLM: {e}")
            return ""

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
