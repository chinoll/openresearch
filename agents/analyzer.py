"""
Relation Analyzer Agent - 关系分析 Agent
分析论文之间的关系，构建知识网络
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse
from prompts.loader import load as load_prompt
from core.vector_store import VectorStore
from core.knowledge_graph import KnowledgeGraph


class RelationAnalyzerAgent(BaseAgent):
    """关系分析 Agent - 构建论文关系网络"""

    from core.registry import ModuleRegistration, ModuleType, Capability, DependencySpec, InputSchema, OutputSchema
    REGISTRATION = ModuleRegistration(
        name="relation_analyzer",
        module_type=ModuleType.AGENT,
        display_name="关系分析 Agent",
        description="分析论文之间的引用、相似度、主题关系，构建知识网络",
        pipeline_stage="analysis",
        pipeline_order=30,
        dependencies=[
            DependencySpec(name="vector_store"),
            DependencySpec(name="knowledge_graph"),
        ],
        capabilities=[
            Capability(
                name="analyze_relations",
                description="分析论文关系（引用、相似度、主题、演进、影响力）",
                input_schema=[
                    InputSchema(name="paper_id", type="str", description="论文 ID"),
                    InputSchema(name="paper_data", type="Dict", description="论文数据"),
                    InputSchema(name="analysis_tasks", type="List[str]", description="分析任务列表", required=False),
                ],
                output_schema=[
                    OutputSchema(name="analysis_results", type="Dict", description="分析结果"),
                ],
                tags=["analysis", "citation", "similarity", "paper"],
            ),
            Capability(
                name="compare_papers",
                description="对比分析多篇论文",
                input_schema=[
                    InputSchema(name="paper_ids", type="List[str]", description="论文 ID 列表"),
                ],
                tags=["analysis", "comparison", "paper"],
            ),
        ],
    )
    del ModuleRegistration, ModuleType, Capability, DependencySpec, InputSchema, OutputSchema

    def __init__(self,
                 config: AgentConfig,
                 vector_store: VectorStore,
                 knowledge_graph: KnowledgeGraph):
        super().__init__(config)

        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph

        self.log("Relation Analyzer Agent initialized")

    async def process(self, input_data: Dict) -> Dict:
        """
        处理关系分析请求

        Args:
            input_data: {
                'paper_id': 论文 ID,
                'paper_data': 论文数据,
                'analysis_tasks': ['citations', 'similarities', 'topics', ...]
            }

        Returns:
            分析结果
        """
        paper_id = input_data.get('paper_id')
        paper_data = input_data.get('paper_data')

        if not paper_id or not paper_data:
            return AgentResponse(
                success=False,
                error="Missing paper_id or paper_data"
            ).to_dict()

        analysis_tasks = input_data.get('analysis_tasks', [
            'citations',
            'similarities',
            'topics',
            'evolution'
        ])

        try:
            analysis_results = {}

            # 1. 引用关系分析
            if 'citations' in analysis_tasks:
                analysis_results['citation_analysis'] = await self._analyze_citations(
                    paper_id, paper_data
                )

            # 2. 相似度分析
            if 'similarities' in analysis_tasks:
                analysis_results['similarity_analysis'] = await self._analyze_similarities(
                    paper_id, paper_data
                )

            # 3. 主题分析
            if 'topics' in analysis_tasks:
                analysis_results['topic_analysis'] = await self._analyze_topics(
                    paper_id, paper_data
                )

            # 4. 研究演进分析
            if 'evolution' in analysis_tasks:
                analysis_results['evolution_analysis'] = await self._analyze_evolution(
                    paper_id, paper_data
                )

            # 5. 影响力分析
            analysis_results['impact_analysis'] = await self._analyze_impact(
                paper_id, paper_data
            )

            # 6. 生成关系摘要
            analysis_results['relation_summary'] = await self._generate_relation_summary(
                paper_id, analysis_results
            )

            self.log(f"✓ Relation analysis completed for {paper_id}")
            return AgentResponse(success=True, data=analysis_results).to_dict()

        except Exception as e:
            self.log(f"Error in relation analysis: {e}", "error")
            return AgentResponse(success=False, error=str(e)).to_dict()

    async def _analyze_citations(self, paper_id: str, paper_data: Dict) -> Dict:
        """分析引用关系"""
        self.log(f"Analyzing citations for {paper_id}...")

        citations = paper_data.get('citations', [])

        # 添加到知识图谱
        for cited_key in citations:
            # 这里简化处理，实际应该查找真实的论文 ID
            self.knowledge_graph.add_citation(
                citing_paper=paper_id,
                cited_paper=cited_key,
                context=""
            )

        # 获取引用网络
        outgoing_citations = self.knowledge_graph.get_citations(paper_id, direction='out')
        incoming_citations = self.knowledge_graph.get_citations(paper_id, direction='in')

        # 获取引用网络子图
        citation_network = self.knowledge_graph.get_citation_network(paper_id, depth=2)

        return {
            'num_references': len(citations),
            'num_citing_this': len(incoming_citations),
            'references': citations[:20],  # 限制数量
            'cited_by': incoming_citations[:20],
            'citation_network_size': len(citation_network['nodes']),
            'network_stats': {
                'nodes': len(citation_network['nodes']),
                'edges': len(citation_network['edges'])
            }
        }

    async def _analyze_similarities(self, paper_id: str, paper_data: Dict) -> Dict:
        """分析语义相似度"""
        self.log(f"Analyzing similarities for {paper_id}...")

        # 使用向量存储查找相似论文
        similar_papers = self.vector_store.search_similar(
            paper_id=paper_id,
            top_k=10,
            min_similarity=0.5
        )

        # 添加相似性边到知识图谱
        for similar in similar_papers:
            if similar['paper_id'] != paper_id:
                self.knowledge_graph.add_similarity_edge(
                    paper1=paper_id,
                    paper2=similar['paper_id'],
                    similarity=similar['similarity'],
                    similarity_type='semantic'
                )

        # 使用 LLM 进行深度相似性分析
        if similar_papers:
            deep_analysis = await self._deep_similarity_analysis(
                paper_data, similar_papers[:3]
            )
        else:
            deep_analysis = "No similar papers found for comparison."

        return {
            'num_similar_papers': len(similar_papers),
            'top_similar': [
                {
                    'paper_id': p['paper_id'],
                    'title': p['metadata'].get('title', 'Unknown'),
                    'similarity': p['similarity']
                }
                for p in similar_papers[:5]
            ],
            'similarity_analysis': deep_analysis
        }

    async def _deep_similarity_analysis(self, paper_data: Dict,
                                       similar_papers: List[Dict]) -> str:
        """深度相似性分析"""
        if not self.llm_client:
            return "LLM not available"

        similar_titles = [p['metadata'].get('title', 'Unknown') for p in similar_papers]

        prompt = load_prompt(
            "analyzer/similarity",
            title=paper_data.get('title', 'N/A'),
            similar_papers_list="\n".join(f"{i+1}. {title}" for i, title in enumerate(similar_titles)),
            abstract=paper_data.get('abstract', '')[:500],
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    async def _analyze_topics(self, paper_id: str, paper_data: Dict) -> Dict:
        """分析主题和研究领域"""
        self.log(f"Analyzing topics for {paper_id}...")

        prompt = load_prompt(
            "analyzer/topics",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', ''),
            keywords=', '.join(paper_data.get('keywords', [])),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={})

    async def _analyze_evolution(self, paper_id: str, paper_data: Dict) -> Dict:
        """分析研究演进"""
        self.log(f"Analyzing research evolution for {paper_id}...")

        # 获取引用的论文（历史脉络）
        cited_papers = self.knowledge_graph.get_citations(paper_id, direction='out')

        # 获取引用此论文的（未来影响）
        citing_papers = self.knowledge_graph.get_citations(paper_id, direction='in')

        # 构建时间线分析
        year = paper_data.get('metadata', {}).get('year') or paper_data.get('year')

        evolution_context = f"""
**论文年份**: {year}
**引用了**: {len(cited_papers)} 篇论文
**被引用**: {len(citing_papers)} 次
"""

        prompt = load_prompt(
            "analyzer/evolution",
            title=paper_data.get('title', 'N/A'),
            evolution_context=evolution_context,
            abstract=paper_data.get('abstract', '')[:300],
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        result = self._parse_json_response(response, default={})

        result['cited_count'] = len(cited_papers)
        result['citing_count'] = len(citing_papers)

        return result

    async def _analyze_impact(self, paper_id: str, paper_data: Dict) -> Dict:
        """分析影响力"""
        self.log(f"Analyzing impact for {paper_id}...")

        # 被引次数
        citing_papers = self.knowledge_graph.get_citations(paper_id, direction='in')
        citation_count = len(citing_papers)

        # 在图中的中心性（如果有足够节点）
        centrality = 0.0
        if self.knowledge_graph.graph.number_of_nodes() > 1:
            try:
                import networkx as nx
                centrality_dict = nx.betweenness_centrality(
                    self.knowledge_graph.graph.to_undirected()
                )
                centrality = centrality_dict.get(paper_id, 0.0)
            except:
                pass

        # 影响力评估
        impact_level = "Low"
        if citation_count > 100:
            impact_level = "High"
        elif citation_count > 20:
            impact_level = "Medium"

        return {
            'citation_count': citation_count,
            'centrality_score': centrality,
            'impact_level': impact_level,
            'is_influential': citation_count > 20
        }

    async def _generate_relation_summary(self, paper_id: str,
                                        analysis_results: Dict) -> str:
        """生成关系摘要"""
        self.log(f"Generating relation summary for {paper_id}...")

        citation_info = analysis_results.get('citation_analysis', {})
        similarity_info = analysis_results.get('similarity_analysis', {})
        topic_info = analysis_results.get('topic_analysis', {})
        evolution_info = analysis_results.get('evolution_analysis', {})
        impact_info = analysis_results.get('impact_analysis', {})

        prompt = load_prompt(
            "analyzer/relation_summary",
            num_references=str(citation_info.get('num_references', 0)),
            num_citing=str(citation_info.get('num_citing_this', 0)),
            num_similar=str(similarity_info.get('num_similar_papers', 0)),
            primary_field=topic_info.get('primary_field', 'Unknown'),
            impact_level=impact_info.get('impact_level', 'Unknown'),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    async def compare_papers(self, paper_ids: List[str]) -> Dict:
        """
        对比分析多篇论文

        Args:
            paper_ids: 论文 ID 列表

        Returns:
            对比分析结果
        """
        self.log(f"Comparing {len(paper_ids)} papers...")

        if len(paper_ids) < 2:
            return {"error": "Need at least 2 papers to compare"}

        # 获取论文信息
        papers_info = []
        for pid in paper_ids:
            paper = self.knowledge_graph.get_paper(pid)
            if paper:
                papers_info.append({
                    'id': pid,
                    'title': paper.get('title', 'Unknown'),
                    'year': paper.get('year'),
                    'abstract': paper.get('abstract', '')[:300]
                })

        if len(papers_info) < 2:
            return {"error": "Could not find enough papers in knowledge graph"}

        # 使用 LLM 进行对比分析
        prompt = load_prompt(
            "analyzer/compare_papers",
            papers_count=str(len(papers_info)),
            papers_formatted=self._format_papers_for_comparison(papers_info),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        comparison = self._parse_json_response(response, default={})

        comparison['papers_compared'] = [p['id'] for p in papers_info]
        comparison['num_papers'] = len(papers_info)

        return comparison

    # 辅助方法

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return load_prompt("system/analyzer")

    def _parse_json_response(self, response: str, default: Dict = None) -> Dict:
        """解析 JSON 响应"""
        import re
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                return json.loads(response[start:end+1])

        except Exception as e:
            self.log(f"Error parsing JSON: {e}", "warning")

        return default or {}

    def _format_papers_for_comparison(self, papers_info: List[Dict]) -> str:
        """格式化论文用于对比"""
        formatted = []
        for i, paper in enumerate(papers_info, 1):
            formatted.append(f"""
**论文 {i}** (ID: {paper['id']})
- 标题: {paper['title']}
- 年份: {paper.get('year', 'N/A')}
- 摘要: {paper.get('abstract', 'N/A')}
""")
        return "\n".join(formatted)


# 使用示例
if __name__ == "__main__":
    import asyncio

    async def main():
        # 初始化组件
        vector_store = VectorStore(
            db_path=Path("./data/vector_db")
        )

        knowledge_graph = KnowledgeGraph(
            graph_path=Path("./data/knowledge_graph.pkl")
        )

        # 创建 Agent
        config = AgentConfig(
            name="RelationAnalyzer",
            model="claude-sonnet-4-5-20250929"
        )

        agent = RelationAnalyzerAgent(
            config=config,
            vector_store=vector_store,
            knowledge_graph=knowledge_graph
        )

        # 测试分析
        result = await agent.process({
            'paper_id': 'test_paper',
            'paper_data': {
                'title': 'Test Paper',
                'abstract': 'This is a test...',
                'citations': ['ref1', 'ref2']
            },
            'analysis_tasks': ['citations', 'topics']
        })

        print(json.dumps(result, indent=2))

    asyncio.run(main())
