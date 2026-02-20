"""
Agents module - 多 Agent 协作系统

导入所有 Agent 类时会触发 REGISTRATION 类属性的创建，
配合 Registry.auto_discover() 实现自动注册。
"""

from .base_agent import BaseAgent, AgentConfig, AgentResponse
from .ingestion import PaperIngestionAgent
from .extractor import KnowledgeExtractorAgent
from .analyzer import RelationAnalyzerAgent
from .orchestrator import OrchestratorAgent
from .insight import InsightAgent

__all__ = [
    'BaseAgent',
    'AgentConfig',
    'AgentResponse',
    'PaperIngestionAgent',
    'KnowledgeExtractorAgent',
    'RelationAnalyzerAgent',
    'OrchestratorAgent',
    'InsightAgent',
]
