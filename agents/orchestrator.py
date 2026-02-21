"""
Orchestrator Agent - 主控 Agent
协调所有子 Agent，管理整体工作流

通过 Registry 获取依赖，支持动态流水线组合。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse
from core.registry import get_registry, ModuleRegistration, ModuleType


class OrchestratorAgent(BaseAgent):
    """主控 Agent - 协调整个研究流程"""

    from core.registry import ModuleRegistration as _MR, ModuleType as _MT, Capability, DependencySpec
    REGISTRATION = _MR(
        name="orchestrator",
        module_type=_MT.AGENT,
        display_name="主控 Agent",
        description="协调所有子 Agent，管理论文研究全流程",
        dependencies=[
            DependencySpec(name="vector_store"),
            DependencySpec(name="knowledge_graph"),
        ],
        capabilities=[
            Capability(name="add_paper", description="添加论文并进行完整分析流水线", tags=["pipeline", "paper"]),
            Capability(name="analyze_paper", description="对已有论文重新进行关系分析", tags=["analysis", "paper"]),
            Capability(name="compare_papers", description="对比多篇论文", tags=["analysis", "comparison"]),
            Capability(name="get_statistics", description="获取系统统计信息", tags=["stats"]),
            Capability(name="search_papers", description="语义搜索论文", tags=["search", "paper"]),
        ],
    )
    del _MR, _MT, Capability, DependencySpec

    def __init__(self,
                 config: AgentConfig,
                 app_config: dict,
                 vector_store=None,
                 knowledge_graph=None):
        """
        初始化主控 Agent

        Args:
            config: Agent 配置
            app_config: 应用配置字典（用于 registry DI 解析）
            vector_store: 通过 registry DI 注入的向量存储实例
            knowledge_graph: 通过 registry DI 注入的知识图谱实例
        """
        super().__init__(config)

        self._app_config = app_config
        self._registry = get_registry()

        # 核心组件（通过 DI 注入或 registry 获取）
        self.vector_store = vector_store or self._registry.get_instance("vector_store", self._app_config)
        self.knowledge_graph = knowledge_graph or self._registry.get_instance("knowledge_graph", self._app_config)

        # data_dir 从 config 读取
        storage = self._app_config.get('storage', {})
        self.data_dir = Path(storage.get('papers', './data/papers'))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化子 Agent（通过 registry）
        self._init_sub_agents()

        self.log("Orchestrator Agent initialized")
        self.log(f"Vector store: {self.vector_store.count()} papers")
        self.log(f"Knowledge graph: {self.knowledge_graph.get_statistics()}")

    def _init_sub_agents(self):
        """通过 registry 初始化所有子 Agent"""
        from core.registration import agent_factory

        self.ingestion_agent = self._create_agent("paper_ingestion")
        self.extractor_agent = self._create_agent("knowledge_extractor")
        self.analyzer_agent = self._create_agent("relation_analyzer")

        self.log("All sub-agents initialized")

    def _create_agent(self, name: str):
        """通过 registry 创建 Agent 实例"""
        from core.registration import agent_factory

        reg = self._registry.get_registration(name)
        if not reg or not reg.cls:
            raise RuntimeError(f"Agent not registered: {name}")

        instance = agent_factory(reg.cls, self._app_config)
        self._registry.set_instance(name, instance)
        return instance

    # ==================== 流水线组合 ====================

    def compose_pipeline(self, stages: List[str], input_data: Dict) -> List[ModuleRegistration]:
        """
        按 stage 名列表动态组合流水线。

        Args:
            stages: pipeline_stage 名列表，如 ["ingestion", "extraction", "analysis"]
            input_data: 初始输入

        Returns:
            按 pipeline_order 排序的 Agent 注册列表
        """
        pipeline = []
        for stage in stages:
            stage_agents = self._registry.get_pipeline_modules(stage)
            pipeline.extend(stage_agents)
        return pipeline

    def _llm_route(self, input_data: Dict) -> Optional[str]:
        """
        用 LLM + describe_capabilities() 智能路由未知 command。

        Returns:
            匹配到的 capability 名，或 None
        """
        capabilities_text = self._registry.describe_capabilities()
        if not capabilities_text or not self.llm_client:
            return None

        command = input_data.get('command', '')
        prompt = f"""根据以下可用能力列表，判断用户命令 "{command}" 最匹配哪个能力。
只返回能力的 name（如 "ingest_arxiv"），如果没有匹配返回 "none"。

{capabilities_text}"""

        response = self.call_llm(prompt)
        result = response.strip().strip('"').strip("'")
        if result and result != "none":
            return result
        return None

    # ==================== 命令分发 ====================

    async def process(self, input_data: Dict) -> Dict:
        """处理请求"""
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
            # 尝试 LLM 智能路由
            capability = self._llm_route(input_data)
            if capability:
                reg = self._registry.find_by_capability(capability)
                if reg:
                    self.log(f"LLM routed command '{command}' to {reg.name}.{capability}")
                    instance = self._registry.get_instance(reg.name, self._app_config)
                    if hasattr(instance, 'process'):
                        return await instance.process(input_data)

            return AgentResponse(
                success=False,
                error=f"Unknown command: {command}"
            ).to_dict()

    async def add_paper(self, source: str, identifier: str,
                       full_analysis: bool = True) -> Dict:
        """添加论文并进行完整分析"""
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
            full_text=full_text[:10000],
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

        paper = self.vector_store.get_paper_by_id(paper_id)
        if not paper:
            return AgentResponse(
                success=False,
                error=f"Paper not found: {paper_id}"
            ).to_dict()

        paper_data = {
            'title': paper['metadata'].get('title', 'Unknown'),
            'abstract': paper['metadata'].get('abstract', ''),
            'authors': paper['metadata'].get('authors', '').split(', '),
            'metadata': paper['metadata']
        }

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
        app_config = {
            'llm': {
                'model': 'claude-sonnet-4-5-20250929',
                # 'api_key': 'your-api-key',
            },
            'storage': {
                'papers': './data/papers',
                'vector_db': './data/vector_db',
                'graph': './data/knowledge_graph.pkl',
            },
        }

        registry = get_registry()
        registry.auto_discover(['agents', 'core'])

        config = AgentConfig(
            name="Orchestrator",
            model=app_config['llm']['model'],
        )

        orchestrator = OrchestratorAgent(
            config=config,
            app_config=app_config,
        )

        result = await orchestrator.add_paper(
            source='arxiv',
            identifier='2301.00001'
        )

        print(json.dumps(result, indent=2, ensure_ascii=False))

        stats = orchestrator.get_statistics()
        print("\nStatistics:", json.dumps(stats, indent=2))

    asyncio.run(main())
