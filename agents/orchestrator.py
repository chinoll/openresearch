"""
Orchestrator Agent - 主控 Agent
协调所有子 Agent，管理整体工作流
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse
from agents.ingestion import PaperIngestionAgent
from agents.extractor import KnowledgeExtractorAgent
from agents.analyzer import RelationAnalyzerAgent

from core.vector_store import VectorStore
from core.knowledge_graph import KnowledgeGraph


class OrchestratorAgent(BaseAgent):
    """主控 Agent - 协调整个研究流程"""

    def __init__(self,
                 config: AgentConfig,
                 data_dir: Path,
                 vector_db_path: Path,
                 graph_path: Path):
        """
        初始化主控 Agent

        Args:
            config: Agent 配置
            data_dir: 数据目录
            vector_db_path: 向量数据库路径
            graph_path: 知识图谱路径
        """
        super().__init__(config)

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化核心组件
        self.vector_store = VectorStore(
            db_path=vector_db_path,
            collection_name="research_papers"
        )

        self.knowledge_graph = KnowledgeGraph(
            graph_path=graph_path
        )

        # 初始化子 Agent
        self._init_sub_agents(config)

        self.log("Orchestrator Agent initialized")
        self.log(f"Vector store: {self.vector_store.count()} papers")
        self.log(f"Knowledge graph: {self.knowledge_graph.get_statistics()}")

    def _init_sub_agents(self, config: AgentConfig):
        """初始化所有子 Agent"""

        # 论文摄入 Agent
        self.ingestion_agent = PaperIngestionAgent(
            config=AgentConfig(
                name="PaperIngestion",
                model=config.model,
                api_key=config.api_key,
                temperature=config.temperature
            ),
            download_dir=self.data_dir
        )

        # 知识提取 Agent
        self.extractor_agent = KnowledgeExtractorAgent(
            config=AgentConfig(
                name="KnowledgeExtractor",
                model=config.model,
                api_key=config.api_key,
                temperature=0.7  # 知识提取需要更稳定的输出
            )
        )

        # 关系分析 Agent
        self.analyzer_agent = RelationAnalyzerAgent(
            config=AgentConfig(
                name="RelationAnalyzer",
                model=config.model,
                api_key=config.api_key,
                temperature=0.7
            ),
            vector_store=self.vector_store,
            knowledge_graph=self.knowledge_graph
        )

        self.log("All sub-agents initialized")

    async def process(self, input_data: Dict) -> Dict:
        """
        处理请求（主要用于扩展）

        Args:
            input_data: 输入数据

        Returns:
            处理结果
        """
        command = input_data.get('command', 'add_paper')

        if command == 'add_paper':
            return await self.add_paper(
                source=input_data.get('source', 'arxiv'),
                identifier=input_data.get('identifier')
            )
        elif command == 'analyze_paper':
            return await self.analyze_existing_paper(
                paper_id=input_data.get('paper_id')
            )
        elif command == 'compare_papers':
            return await self.compare_papers(
                paper_ids=input_data.get('paper_ids', [])
            )
        else:
            return AgentResponse(
                success=False,
                error=f"Unknown command: {command}"
            ).to_dict()

    async def add_paper(self, source: str, identifier: str,
                       full_analysis: bool = True) -> Dict:
        """
        添加论文并进行完整分析

        Args:
            source: 'arxiv' 或 'local'
            identifier: arXiv ID 或文件路径
            full_analysis: 是否进行完整分析

        Returns:
            完整的处理结果
        """
        self.log(f"Starting full pipeline for {identifier}")
        self.log("=" * 60)

        workflow_results = {
            'identifier': identifier,
            'source': source,
            'steps': {}
        }

        try:
            # Step 1: 论文摄入
            self.log("Step 1/4: Paper Ingestion")
            ingestion_result = await self.ingestion_agent.process({
                'source': source,
                'identifier': identifier
            })

            if not ingestion_result.get('success'):
                return AgentResponse(
                    success=False,
                    error=f"Ingestion failed: {ingestion_result.get('error')}"
                ).to_dict()

            paper_data = ingestion_result['data']
            paper_id = paper_data.get('metadata', {}).get('arxiv_id') or identifier
            workflow_results['paper_id'] = paper_id
            workflow_results['steps']['ingestion'] = {
                'success': True,
                'title': paper_data.get('title'),
                'source_type': paper_data.get('source_type')
            }

            self.log(f"✓ Paper ingested: {paper_data.get('title')}")

            if not full_analysis:
                return AgentResponse(success=True, data=workflow_results).to_dict()

            # Step 2: 知识提取
            self.log("\nStep 2/4: Knowledge Extraction")
            extraction_result = await self.extractor_agent.process({
                'paper_data': paper_data,
                'extraction_tasks': [
                    'contributions',
                    'methodology',
                    'research_questions',
                    'findings',
                    'limitations',
                    'keywords',
                    'concepts'
                ]
            })

            if extraction_result.get('success'):
                extracted_knowledge = extraction_result['data']
                workflow_results['steps']['extraction'] = {
                    'success': True,
                    'num_contributions': len(extracted_knowledge.get('contributions', [])),
                    'num_keywords': len(extracted_knowledge.get('keywords', []))
                }
                self.log(f"✓ Knowledge extracted: {len(extracted_knowledge.get('contributions', []))} contributions")
            else:
                self.log("⚠ Knowledge extraction failed", "warning")
                extracted_knowledge = {}

            # Step 3: 添加到向量数据库和知识图谱
            self.log("\nStep 3/4: Building Knowledge Base")
            await self._add_to_knowledge_base(paper_id, paper_data, extracted_knowledge)
            workflow_results['steps']['knowledge_base'] = {'success': True}
            self.log("✓ Added to knowledge base")

            # Step 4: 关系分析
            self.log("\nStep 4/4: Relation Analysis")
            analysis_result = await self.analyzer_agent.process({
                'paper_id': paper_id,
                'paper_data': paper_data,
                'analysis_tasks': ['citations', 'similarities', 'topics', 'evolution']
            })

            if analysis_result.get('success'):
                relation_analysis = analysis_result['data']
                workflow_results['steps']['analysis'] = {
                    'success': True,
                    'num_similar': relation_analysis.get('similarity_analysis', {}).get('num_similar_papers', 0),
                    'impact_level': relation_analysis.get('impact_analysis', {}).get('impact_level', 'Unknown')
                }
                self.log(f"✓ Relation analysis completed")
            else:
                self.log("⚠ Relation analysis failed", "warning")
                relation_analysis = {}

            # 保存知识图谱
            self.knowledge_graph.save()

            # 整合所有结果
            workflow_results['complete_analysis'] = {
                'paper_info': {
                    'id': paper_id,
                    'title': paper_data.get('title'),
                    'authors': paper_data.get('authors', []),
                    'source_type': paper_data.get('source_type')
                },
                'knowledge': extracted_knowledge,
                'relations': relation_analysis
            }

            self.log("\n" + "=" * 60)
            self.log("✓ Full pipeline completed successfully")

            return AgentResponse(success=True, data=workflow_results).to_dict()

        except Exception as e:
            self.log(f"Error in pipeline: {e}", "error")
            return AgentResponse(
                success=False,
                error=str(e),
                data=workflow_results
            ).to_dict()

    async def _add_to_knowledge_base(self, paper_id: str, paper_data: Dict,
                                    extracted_knowledge: Dict):
        """添加到知识库"""

        # 1. 添加到向量数据库
        title = paper_data.get('title', 'Unknown')
        abstract = paper_data.get('abstract', '')

        # 构建全文（如果有的话）
        full_text_parts = [title, abstract]
        for section in paper_data.get('sections', []):
            if section.get('content'):
                full_text_parts.append(section['content'])

        full_text = '\n\n'.join(full_text_parts)

        metadata = {
            'title': title,
            'authors': ', '.join(paper_data.get('authors', [])),
            'year': paper_data.get('metadata', {}).get('year') or paper_data.get('year'),
            'venue': paper_data.get('metadata', {}).get('venue', ''),
            'source_type': paper_data.get('source_type', 'unknown')
        }

        self.vector_store.add_paper(
            paper_id=paper_id,
            title=title,
            abstract=abstract,
            full_text=full_text[:10000],  # 限制长度
            metadata=metadata
        )

        # 2. 添加到知识图谱
        keywords = extracted_knowledge.get('keywords', [])

        self.knowledge_graph.add_paper(
            paper_id=paper_id,
            title=title,
            authors=paper_data.get('authors', []),
            abstract=abstract,
            year=metadata.get('year'),
            venue=metadata.get('venue'),
            keywords=keywords
        )

    async def analyze_existing_paper(self, paper_id: str) -> Dict:
        """对已存在的论文进行重新分析"""
        self.log(f"Re-analyzing paper: {paper_id}")

        # 从向量存储获取论文
        paper = self.vector_store.get_paper_by_id(paper_id)
        if not paper:
            return AgentResponse(
                success=False,
                error=f"Paper not found: {paper_id}"
            ).to_dict()

        # 构建 paper_data
        paper_data = {
            'title': paper['metadata'].get('title', 'Unknown'),
            'abstract': paper['metadata'].get('abstract', ''),
            'authors': paper['metadata'].get('authors', '').split(', '),
            'metadata': paper['metadata']
        }

        # 执行关系分析
        analysis_result = await self.analyzer_agent.process({
            'paper_id': paper_id,
            'paper_data': paper_data,
            'analysis_tasks': ['citations', 'similarities', 'topics', 'evolution']
        })

        return analysis_result

    async def compare_papers(self, paper_ids: List[str]) -> Dict:
        """对比多篇论文"""
        self.log(f"Comparing {len(paper_ids)} papers")

        if len(paper_ids) < 2:
            return AgentResponse(
                success=False,
                error="Need at least 2 papers to compare"
            ).to_dict()

        # 使用关系分析 Agent 进行对比
        comparison = await self.analyzer_agent.compare_papers(paper_ids)

        return AgentResponse(success=True, data=comparison).to_dict()

    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        return {
            'vector_store': {
                'num_papers': self.vector_store.count()
            },
            'knowledge_graph': self.knowledge_graph.get_statistics(),
            'influential_papers': self.knowledge_graph.get_influential_papers(top_k=5)
        }

    def search_papers(self, query: str, top_k: int = 10) -> List[Dict]:
        """搜索论文"""
        return self.vector_store.search_similar(
            query=query,
            top_k=top_k
        )


# 使用示例
if __name__ == "__main__":
    import asyncio

    async def main():
        config = AgentConfig(
            name="Orchestrator",
            model="claude-sonnet-4-5-20250929",
            # api_key="your-api-key"
        )

        orchestrator = OrchestratorAgent(
            config=config,
            data_dir=Path("./data/papers"),
            vector_db_path=Path("./data/vector_db"),
            graph_path=Path("./data/knowledge_graph.pkl")
        )

        # 添加论文
        result = await orchestrator.add_paper(
            source='arxiv',
            identifier='2301.00001'
        )

        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 查看统计
        stats = orchestrator.get_statistics()
        print("\nStatistics:", json.dumps(stats, indent=2))

    asyncio.run(main())
