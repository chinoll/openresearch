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
from core.vector_store import VectorStore
from core.knowledge_graph import KnowledgeGraph


class RelationAnalyzerAgent(BaseAgent):
    """关系分析 Agent - 构建论文关系网络"""

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

        prompt = f"""分析以下论文与相似论文的关系：

**目标论文**: {paper_data.get('title')}

**相似论文**:
{chr(10).join(f"{i+1}. {title}" for i, title in enumerate(similar_titles))}

**目标论文摘要**:
{paper_data.get('abstract', '')[:500]}

请分析：
1. 这些论文的共同点是什么？
2. 主要的研究方向或主题是什么？
3. 它们之间的主要差异是什么？

请用2-3段话总结。"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    async def _analyze_topics(self, paper_id: str, paper_data: Dict) -> Dict:
        """分析主题和研究领域"""
        self.log(f"Analyzing topics for {paper_id}...")

        prompt = f"""分析论文的研究主题和领域。

**标题**: {paper_data.get('title')}

**摘要**:
{paper_data.get('abstract', '')}

**关键词**: {', '.join(paper_data.get('keywords', []))}

请识别：
1. 主要研究领域（如 NLP, CV, RL 等）
2. 具体研究方向（如 Transformers, Object Detection 等）
3. 技术栈和方法类别
4. 应用场景

以 JSON 格式输出：
```json
{{
  "primary_field": "主要领域",
  "sub_fields": ["子领域1", "子领域2"],
  "research_direction": "具体研究方向",
  "technical_stack": ["技术1", "技术2"],
  "application_domains": ["应用领域1", "应用领域2"]
}}
```"""

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

        prompt = f"""分析这篇论文在研究演进中的位置。

**论文**: {paper_data.get('title')}

**时间信息**:
{evolution_context}

**摘要**:
{paper_data.get('abstract', '')[:300]}

请分析：
1. 这篇论文继承了哪些前人的工作？
2. 它在研究脉络中的创新点是什么？
3. 它可能对后续研究产生什么影响？

以 JSON 格式输出：
```json
{{
  "builds_on": "基于哪些前人工作",
  "innovation": "主要创新点",
  "potential_impact": "潜在影响",
  "position_in_timeline": "在研究时间线中的位置描述"
}}
```"""

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

        prompt = f"""基于以下关系分析结果，生成一个简洁的关系摘要（200字以内）。

**引用信息**:
- 引用了 {citation_info.get('num_references', 0)} 篇论文
- 被引用 {citation_info.get('num_citing_this', 0)} 次

**相似论文**:
- 发现 {similarity_info.get('num_similar_papers', 0)} 篇相似论文

**研究领域**:
- {topic_info.get('primary_field', 'Unknown')}

**影响力**:
- 影响力等级: {impact_info.get('impact_level', 'Unknown')}

请生成一个关系摘要，说明：
1. 论文在研究网络中的位置
2. 与其他研究的关系
3. 潜在影响

直接输出摘要文本。"""

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
        prompt = f"""对比分析以下 {len(papers_info)} 篇论文：

{self._format_papers_for_comparison(papers_info)}

请从以下方面对比：
1. 研究问题的异同
2. 方法的差异
3. 各自的优势和不足
4. 互补性或竞争关系

以 JSON 格式输出：
```json
{{
  "commonalities": ["共同点1", "共同点2"],
  "differences": ["差异1", "差异2"],
  "comparative_advantages": {{
    "paper1_id": ["优势1", "优势2"],
    "paper2_id": ["优势1", "优势2"]
  }},
  "relationship": "竞争/互补/延续",
  "summary": "对比总结"
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        comparison = self._parse_json_response(response, default={})

        comparison['papers_compared'] = [p['id'] for p in papers_info]
        comparison['num_papers'] = len(papers_info)

        return comparison

    # 辅助方法

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的学术关系分析助手，擅长分析论文之间的关系和影响。
你的任务是识别论文在研究网络中的位置，分析其与其他研究的联系。
请始终以结构化的 JSON 格式输出结果（当需要时），确保格式正确。"""

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
