"""
Agents module - 多 Agent 协作系统
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
