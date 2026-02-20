"""
Core module - 核心功能组件

导入所有 Core 类时会触发 REGISTRATION 类属性的创建，
配合 Registry.auto_discover() 实现自动注册。
"""

from .tex_parser import TeXParser, TexDocument
from .arxiv_downloader import ArxivDownloader
from .vector_store import VectorStore
from .knowledge_graph import KnowledgeGraph
from .ideas_manager import IdeasManager, Idea, ReadingSession
from .insights_system import InsightsManager
from .questions_system import QuestionsManager
from .structured_ideas import StructuredIdeasManager
from .registry import Registry, ModuleRegistration, ModuleType, get_registry

__all__ = [
    'TeXParser',
    'TexDocument',
    'ArxivDownloader',
    'VectorStore',
    'KnowledgeGraph',
    'IdeasManager',
    'Idea',
    'ReadingSession',
    'InsightsManager',
    'QuestionsManager',
    'StructuredIdeasManager',
    'Registry',
    'ModuleRegistration',
    'ModuleType',
    'get_registry',
]
