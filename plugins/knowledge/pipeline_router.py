"""
Orchestrator Router - 流水线原子工具

将 Agent 能力拆为原子工具暴露给 Chat LLM，由 LLM 自主编排调用顺序。
通过 ROUTER_REGISTRATION 自动被 registry 发现，工具自动注入 chat 工具列表。
"""
import json
import logging
from pathlib import Path
from typing import Dict, List

from core.registry import (
    ModuleRegistration, ModuleType, Capability, InputSchema,
    get_registry,
)

logger = logging.getLogger(__name__)

# ==================== Lazy init ====================

_app_config = None
_registry = None
_agents: Dict[str, object] = {}


def _ensure_init():
    """Lazy init: 加载配置、获取 registry"""
    global _app_config, _registry
    if _registry is not None:
        return
    from core.config import get_app_config
    _app_config = get_app_config()
    _registry = get_registry()


def _get_agent(name: str):
    """按需创建 agent 实例（单例缓存）"""
    if name not in _agents:
        _ensure_init()
        from core.registration import agent_factory
        reg = _registry.get_registration(name)
        if not reg or not reg.cls:
            raise RuntimeError(f"Agent not registered: {name}")
        _agents[name] = agent_factory(reg.cls, _app_config)
    return _agents[name]


def _get_service(name: str):
    """获取共享服务实例（vector_store, knowledge_graph）"""
    _ensure_init()
    return _registry.get_instance(name, _app_config)


# ==================== 数据加载/保存 ====================

def _paper_metadata_dir() -> Path:
    _ensure_init()
    storage = _app_config.get('storage', {})
    d = Path(storage.get('papers', './data/papers')) / "metadata"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_paper_data(paper_id: str) -> dict:
    """加载已摄入的论文数据"""
    path = _paper_metadata_dir() / f"{paper_id.replace('.', '_')}.json"
    if not path.exists():
        raise FileNotFoundError(f"论文 {paper_id} 尚未摄入，请先调用 ingest_paper")
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _load_knowledge_data(paper_id: str) -> dict:
    """加载已提取的知识数据"""
    path = _paper_metadata_dir() / f"{paper_id.replace('.', '_')}_knowledge.json"
    if not path.exists():
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _save_knowledge_data(paper_id: str, data: dict):
    """保存知识提取结果"""
    path = _paper_metadata_dir() / f"{paper_id.replace('.', '_')}_knowledge.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ==================== Tool Handlers ====================

async def _h_ingest_paper(tool_input):
    """下载+解析+AI分析论文，返回论文元信息"""
    agent = _get_agent("paper_ingestion")
    result = await agent.process({
        'source': tool_input.get('source', 'arxiv'),
        'identifier': tool_input['identifier'],
    })
    if not result.get('success'):
        return result
    data = result['data']
    paper_id = data.get('metadata', {}).get('arxiv_id', tool_input['identifier']).replace('.', '_')
    return {
        "display_type": "paper_card",
        "success": True,
        "paper_id": paper_id,
        "title": data.get('title', 'Unknown'),
        "authors": data.get('authors', []),
        "abstract": data.get('abstract', ''),
        "source_type": data.get('source_type'),
        "sections": [s.get('title', '') for s in data.get('sections', [])],
        "ai_analysis": data.get('ai_analysis', {}),
    }


async def _h_extract_knowledge(tool_input):
    """从已摄入论文提取结构化知识，返回完整提取结果"""
    paper_id = tool_input['paper_id']
    paper_data = _load_paper_data(paper_id)
    agent = _get_agent("knowledge_extractor")
    result = await agent.process({
        'paper_data': paper_data,
        'extraction_tasks': tool_input.get('tasks', [
            'contributions', 'methodology', 'research_questions',
            'findings', 'limitations', 'keywords', 'concepts',
        ]),
    })
    if result.get('success'):
        _save_knowledge_data(paper_id, result['data'])
        k = result['data']
        return {
            "display_type": "knowledge",
            "success": True,
            "paper_id": paper_id,
            "contributions": k.get('contributions', []),
            "methodology": k.get('methodology', {}),
            "research_questions": k.get('research_questions', []),
            "findings": k.get('findings', []),
            "limitations": k.get('limitations', []),
            "keywords": k.get('keywords', []),
            "concepts": k.get('concepts', []),
            "summary": k.get('summary', ''),
        }
    return result


async def _h_add_to_knowledge_base(tool_input):
    """将论文和知识写入向量库+知识图谱"""
    paper_id = tool_input['paper_id']
    paper_data = _load_paper_data(paper_id)

    # keywords: 优先用 LLM 传入的，fallback 从磁盘加载
    keywords = tool_input.get('keywords') or _load_knowledge_data(paper_id).get('keywords', [])

    vs = _get_service("vector_store")
    kg = _get_service("knowledge_graph")

    title = paper_data.get('title', 'Unknown')
    abstract = paper_data.get('abstract', '')
    full_text_parts = [title, abstract]
    for sec in paper_data.get('sections', []):
        if sec.get('content'):
            full_text_parts.append(sec['content'])

    vs.add_paper(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        full_text='\n\n'.join(full_text_parts)[:10000],
        metadata={
            'title': title,
            'authors': ', '.join(paper_data.get('authors', [])),
            'year': paper_data.get('metadata', {}).get('year'),
            'source_type': paper_data.get('source_type', 'unknown'),
        },
    )

    kg.add_paper(
        paper_id=paper_id,
        title=title,
        authors=paper_data.get('authors', []),
        abstract=abstract,
        year=paper_data.get('metadata', {}).get('year'),
        keywords=keywords,
    )
    kg.save()

    return {
        "display_type": "confirmation",
        "success": True,
        "paper_id": paper_id,
        "title": title,
        "vector_store_count": vs.count(),
        "graph_stats": kg.get_statistics(),
    }


async def _h_analyze_relations(tool_input):
    """分析论文关系，返回完整分析结果"""
    paper_id = tool_input['paper_id']
    paper_data = _load_paper_data(paper_id)
    agent = _get_agent("relation_analyzer")
    result = await agent.process({
        'paper_id': paper_id,
        'paper_data': paper_data,
        'analysis_tasks': tool_input.get('tasks',
                                         ['citations', 'similarities', 'topics', 'evolution']),
    })
    if result.get('success'):
        d = result['data']
        return {
            "display_type": "relations",
            "success": True,
            "paper_id": paper_id,
            "citation_analysis": d.get('citation_analysis', {}),
            "similarity_analysis": d.get('similarity_analysis', {}),
            "topic_analysis": d.get('topic_analysis', {}),
            "impact_analysis": d.get('impact_analysis', {}),
            "relation_summary": d.get('relation_summary', ''),
        }
    return result


async def _h_search_papers(tool_input):
    """语义搜索已有论文"""
    vs = _get_service("vector_store")
    results = vs.search_similar(
        query=tool_input['query'],
        top_k=tool_input.get('top_k', 5),
    )
    return {
        "display_type": "paper_list",
        "count": len(results),
        "papers": [
            {
                "paper_id": r.get('paper_id'),
                "title": r.get('metadata', {}).get('title', 'Unknown'),
                "authors": r.get('metadata', {}).get('authors', ''),
                "similarity": round(r.get('similarity', 0), 3),
            }
            for r in results
        ],
    }


# ==================== 注册 ====================

TOOL_HANDLERS = {
    "ingest_paper": _h_ingest_paper,
    "extract_knowledge": _h_extract_knowledge,
    "add_to_knowledge_base": _h_add_to_knowledge_base,
    "analyze_relations": _h_analyze_relations,
    "search_papers": _h_search_papers,
}

ROUTER_REGISTRATION = ModuleRegistration(
    name="pipeline_router",
    module_type=ModuleType.TOOL,
    display_name="研究流水线工具",
    description="论文分析原子工具（摄入、知识提取、入库、关系分析、搜索），由 AI 自主编排",
    capabilities=[
        Capability(
            name="ingest_paper",
            description="下载并解析论文（TeX 优先），包含 AI 深度分析。返回 paper_id 和论文元信息。",
            input_schema=[
                InputSchema(name="identifier", type="str",
                            description="arXiv ID/URL 或本地文件路径", required=True),
                InputSchema(name="source", type="str",
                            description="来源类型",
                            enum_values=["arxiv", "local"], default="arxiv"),
            ],
            tags=["pipeline", "ingestion"],
        ),
        Capability(
            name="extract_knowledge",
            description="从已摄入论文中提取结构化知识：贡献、方法论、关键词、发现等。需先调用 ingest_paper。",
            input_schema=[
                InputSchema(name="paper_id", type="str",
                            description="论文 ID（由 ingest_paper 返回）", required=True),
                InputSchema(name="tasks", type="array",
                            description="提取任务列表",
                            default=None, required=False),
            ],
            tags=["pipeline", "extraction"],
        ),
        Capability(
            name="add_to_knowledge_base",
            description="将论文和提取的知识写入向量数据库和知识图谱。keywords 可从 extract_knowledge 结果传入。",
            input_schema=[
                InputSchema(name="paper_id", type="str",
                            description="论文 ID", required=True),
                InputSchema(name="keywords", type="array",
                            description="关键词列表（可选，来自 extract_knowledge 结果）",
                            default=None, required=False),
            ],
            tags=["pipeline", "knowledge_base"],
        ),
        Capability(
            name="analyze_relations",
            description="分析论文的引用关系、相似论文、研究领域和影响力。需先将论文加入知识库。",
            input_schema=[
                InputSchema(name="paper_id", type="str",
                            description="论文 ID", required=True),
                InputSchema(name="tasks", type="array",
                            description="分析任务列表",
                            default=None, required=False),
            ],
            tags=["pipeline", "analysis"],
        ),
        Capability(
            name="search_papers",
            description="在已有论文中进行语义搜索，返回相似论文列表",
            input_schema=[
                InputSchema(name="query", type="str",
                            description="搜索查询文本", required=True),
                InputSchema(name="top_k", type="int",
                            description="返回数量", default=5),
            ],
            tags=["search"],
        ),
    ],
)
