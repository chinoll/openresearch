"""
Knowledge Extractor Agent - 知识提取 Agent
深度分析论文内容，提取核心知识和洞察
"""

import asyncio
import json
from typing import Dict, List, Optional

from core.base_agent import BaseAgent, AgentConfig, AgentResponse
from prompts.loader import load as load_prompt
from plugins.knowledge.schemas import (
    CONTRIBUTIONS_SCHEMA, METHODOLOGY_SCHEMA, RESEARCH_QUESTIONS_SCHEMA,
    FINDINGS_SCHEMA, LIMITATIONS_SCHEMA, FUTURE_WORK_SCHEMA,
    KEYWORDS_SCHEMA, CONCEPTS_SCHEMA, VERIFICATION_SCHEMA,
)


class KnowledgeExtractorAgent(BaseAgent):
    """知识提取 Agent - 深度分析论文内容"""

    from core.registry import ModuleRegistration, ModuleType, Capability, InputSchema, OutputSchema, TeamExport
    REGISTRATION = ModuleRegistration(
        name="knowledge_extractor",
        module_type=ModuleType.AGENT,
        display_name="知识提取 Agent",
        description="深度分析论文内容，提取核心贡献、方法论、关键词等",
        capabilities=[
            Capability(
                name="extract_knowledge",
                description="从论文中提取结构化知识",
                input_schema=[
                    InputSchema(name="paper_data", type="Dict", description="论文解析数据"),
                    InputSchema(name="extraction_tasks", type="List[str]", description="提取任务列表", required=False),
                ],
                output_schema=[
                    OutputSchema(name="extracted_knowledge", type="Dict", description="提取的知识"),
                ],
                tags=["extraction", "knowledge", "paper"],
            ),
        ],
        team_export=TeamExport(default_role="extractor", description="从论文提取结构化知识"),
    )
    del ModuleRegistration, ModuleType, Capability, InputSchema, OutputSchema, TeamExport

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.log("Knowledge Extractor Agent initialized")

    async def process(self, input_data: Dict) -> Dict:
        """处理知识提取请求（分阶段并行 + 上下文累积）"""
        paper_data = input_data.get('paper_data')
        if not paper_data:
            return AgentResponse(success=False, error="No paper data provided").to_dict()

        extraction_tasks = input_data.get('extraction_tasks', [
            'contributions', 'methodology', 'research_questions',
            'findings', 'limitations', 'future_work', 'keywords', 'concepts'
        ])

        try:
            extracted = {}
            context_so_far = ""

            # Phase A（并行）: contributions, research_questions, keywords
            phase_a = {}
            tasks_a = []
            if 'contributions' in extraction_tasks:
                tasks_a.append(('contributions', self._extract_contributions(paper_data, context_so_far)))
            if 'research_questions' in extraction_tasks:
                tasks_a.append(('research_questions', self._extract_research_questions(paper_data, context_so_far)))
            if 'keywords' in extraction_tasks:
                tasks_a.append(('keywords', self._extract_keywords(paper_data, context_so_far)))

            if tasks_a:
                results_a = await asyncio.gather(*[t[1] for t in tasks_a])
                for (name, _), result in zip(tasks_a, results_a):
                    extracted[name] = result
                context_so_far = self._build_context(extracted)

            # Phase B（依赖 A，并行）: methodology, concepts
            tasks_b = []
            if 'methodology' in extraction_tasks:
                tasks_b.append(('methodology', self._extract_methodology(paper_data, context_so_far)))
            if 'concepts' in extraction_tasks:
                tasks_b.append(('concepts', self._extract_key_concepts(paper_data, context_so_far)))

            if tasks_b:
                results_b = await asyncio.gather(*[t[1] for t in tasks_b])
                for (name, _), result in zip(tasks_b, results_b):
                    extracted[name] = result
                context_so_far = self._build_context(extracted)

            # Phase C（依赖 A+B，并行）: findings, limitations, future_work
            tasks_c = []
            if 'findings' in extraction_tasks:
                tasks_c.append(('findings', self._extract_findings(paper_data, context_so_far)))
            if 'limitations' in extraction_tasks:
                tasks_c.append(('limitations', self._extract_limitations(paper_data, context_so_far)))
            if 'future_work' in extraction_tasks:
                tasks_c.append(('future_work', self._extract_future_work(paper_data, context_so_far)))

            if tasks_c:
                results_c = await asyncio.gather(*[t[1] for t in tasks_c])
                for (name, _), result in zip(tasks_c, results_c):
                    extracted[name] = result
                context_so_far = self._build_context(extracted)

            # Phase D（依赖全部）: summary
            extracted['summary'] = await self._generate_comprehensive_summary(
                paper_data, extracted, context_so_far
            )

            # 反思验证（仅对高影响任务）
            extracted = await self._verify_high_impact(paper_data, extracted)

            self.log("Knowledge extraction completed")
            return AgentResponse(success=True, data=extracted).to_dict()

        except Exception as e:
            self.log(f"Error in knowledge extraction: {e}", "error")
            return AgentResponse(success=False, error=str(e)).to_dict()

    def _build_context(self, extracted: Dict) -> str:
        """将已提取的结果构建为上下文字符串，注入后续 prompt"""
        parts = []
        if 'contributions' in extracted and extracted['contributions']:
            titles = [c.get('title', '') for c in extracted['contributions'] if isinstance(c, dict)]
            if titles:
                parts.append(f"已提取贡献: {'; '.join(titles)}")
        if 'research_questions' in extracted and extracted['research_questions']:
            parts.append(f"已提取研究问题: {'; '.join(extracted['research_questions'][:3])}")
        if 'keywords' in extracted and extracted['keywords']:
            parts.append(f"已提取关键词: {', '.join(extracted['keywords'][:10])}")
        if 'methodology' in extracted and isinstance(extracted['methodology'], dict):
            approach = extracted['methodology'].get('approach', '')
            if approach:
                parts.append(f"已提取方法: {approach[:200]}")
        if 'findings' in extracted and extracted['findings']:
            findings_brief = [f.get('finding', '')[:80] for f in extracted['findings'][:3] if isinstance(f, dict)]
            if findings_brief:
                parts.append(f"已提取发现: {'; '.join(findings_brief)}")

        if not parts:
            return ""
        return "**前序提取结果（供参考，避免重复）**:\n" + "\n".join(f"- {p}" for p in parts)

    # ==================== 提取方法 ====================

    async def _extract_contributions(self, paper_data: Dict, prior_context: str) -> List[Dict]:
        """提取核心贡献"""
        self.log("Extracting core contributions...")
        prompt = load_prompt(
            "extractor/contributions",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            sections_brief=self._format_sections_brief(paper_data.get('sections', [])),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, CONTRIBUTIONS_SCHEMA,
                                          tool_name="extract_contributions",
                                          system_prompt=self._get_system_prompt())
        return result.get('contributions', [])

    async def _extract_methodology(self, paper_data: Dict, prior_context: str) -> Dict:
        """提取方法论"""
        self.log("Extracting methodology...")
        prompt = load_prompt(
            "extractor/methodology",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            method_sections=self._extract_method_sections(paper_data.get('sections', [])),
            equations_count=str(paper_data.get('equations_count', 0)),
            prior_context=prior_context,
        )
        return self.call_llm_structured(prompt, METHODOLOGY_SCHEMA,
                                        tool_name="extract_methodology",
                                        system_prompt=self._get_system_prompt())

    async def _extract_research_questions(self, paper_data: Dict, prior_context: str) -> List[str]:
        """提取研究问题"""
        self.log("Extracting research questions...")
        prompt = load_prompt(
            "extractor/research_questions",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            intro_sections=self._extract_intro_sections(paper_data.get('sections', [])),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, RESEARCH_QUESTIONS_SCHEMA,
                                          tool_name="extract_research_questions",
                                          system_prompt=self._get_system_prompt())
        return result.get('research_questions', [])

    async def _extract_findings(self, paper_data: Dict, prior_context: str) -> List[Dict]:
        """提取主要发现和结果"""
        self.log("Extracting key findings...")
        prompt = load_prompt(
            "extractor/findings",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            results_sections=self._extract_results_sections(paper_data.get('sections', [])),
            figures_count=str(len(paper_data.get('figures', [])) + len(paper_data.get('tables', []))),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, FINDINGS_SCHEMA,
                                          tool_name="extract_findings",
                                          system_prompt=self._get_system_prompt())
        return result.get('findings', [])

    async def _extract_limitations(self, paper_data: Dict, prior_context: str) -> List[str]:
        """提取局限性"""
        self.log("Extracting limitations...")
        prompt = load_prompt(
            "extractor/limitations",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            discussion_sections=self._extract_discussion_sections(paper_data.get('sections', [])),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, LIMITATIONS_SCHEMA,
                                          tool_name="extract_limitations",
                                          system_prompt=self._get_system_prompt())
        return result.get('limitations', [])

    async def _extract_future_work(self, paper_data: Dict, prior_context: str) -> str:
        """提取未来工作方向"""
        self.log("Extracting future work...")
        prompt = load_prompt(
            "extractor/future_work",
            title=paper_data.get('title', 'N/A'),
            conclusion_sections=self._extract_conclusion_sections(paper_data.get('sections', [])),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, FUTURE_WORK_SCHEMA,
                                          tool_name="extract_future_work",
                                          system_prompt=self._get_system_prompt())
        future = result.get('future_work', '')
        open_qs = result.get('open_questions', [])
        if open_qs:
            return future + '\n' + ', '.join(open_qs)
        return future

    async def _extract_keywords(self, paper_data: Dict, prior_context: str) -> List[str]:
        """提取关键词"""
        self.log("Extracting keywords...")
        prompt = load_prompt(
            "extractor/keywords",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, KEYWORDS_SCHEMA,
                                          tool_name="extract_keywords",
                                          system_prompt=self._get_system_prompt())
        return result.get('keywords', [])

    async def _extract_key_concepts(self, paper_data: Dict, prior_context: str) -> List[Dict]:
        """提取核心概念及其关系"""
        self.log("Extracting key concepts...")
        prompt = load_prompt(
            "extractor/concepts",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            prior_context=prior_context,
        )
        result = self.call_llm_structured(prompt, CONCEPTS_SCHEMA,
                                          tool_name="extract_concepts",
                                          system_prompt=self._get_system_prompt())
        return result.get('concepts', [])

    async def _generate_comprehensive_summary(self, paper_data: Dict, extracted: Dict,
                                              prior_context: str) -> str:
        """生成综合摘要"""
        self.log("Generating comprehensive summary...")
        prompt = load_prompt(
            "extractor/summary",
            title=paper_data.get('title', 'N/A'),
            contributions_count=str(len(extracted.get('contributions', []))),
            methodology_approach=extracted.get('methodology', {}).get('approach', 'N/A')[:200],
            questions_count=str(len(extracted.get('research_questions', []))),
            findings_count=str(len(extracted.get('findings', []))),
            prior_context=prior_context,
        )
        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    # ==================== 反思验证 ====================

    async def _verify_high_impact(self, paper_data: Dict, extracted: Dict) -> Dict:
        """对高影响任务（contributions, methodology, findings）执行反思验证"""
        if not self.llm_client:
            return extracted

        for task_name in ('contributions', 'methodology', 'findings'):
            if task_name not in extracted or not extracted[task_name]:
                continue

            verified = await self._verify_extraction(
                paper_data, task_name, extracted[task_name]
            )
            if verified and verified.get('corrected_data'):
                confidence = verified.get('confidence', 0)
                if not verified.get('is_accurate', True) and confidence > 0.5:
                    self.log(f"Verification corrected {task_name} (confidence: {confidence:.2f})")
                    extracted[task_name] = verified['corrected_data']
                # 附加置信度
                if f'{task_name}_confidence' not in extracted:
                    extracted[f'{task_name}_confidence'] = confidence

        return extracted

    async def _verify_extraction(self, paper_data: Dict, task_name: str,
                                 extraction_result) -> Optional[Dict]:
        """让 LLM 对照原文验证提取结果的准确性"""
        self.log(f"Verifying {task_name}...")

        extraction_json = json.dumps(extraction_result, ensure_ascii=False, indent=2)
        prompt = f"""请对照论文原文验证以下提取结果的准确性。

**论文标题**: {paper_data.get('title', 'N/A')}
**论文摘要**: {paper_data.get('abstract', 'N/A')[:1000]}

**提取任务**: {task_name}
**提取结果**:
{extraction_json[:2000]}

请检查：
1. 提取的信息是否在原文中有依据？
2. 是否存在编造或过度推断？
3. 是否遗漏了重要信息？

如果发现问题，在 corrected_data 中提供修正后的完整数据（保持原始结构）。
如果准确无误，corrected_data 留空。"""

        return self.call_llm_structured(prompt, VERIFICATION_SCHEMA,
                                        tool_name="verify_extraction",
                                        system_prompt=self._get_system_prompt())

    # ==================== 辅助方法 ====================

    def _get_system_prompt(self) -> str:
        return load_prompt("system/extractor")

    def _format_sections_brief(self, sections: List[Dict]) -> str:
        """简要格式化章节（扩展到 30 个）"""
        if not sections:
            return "N/A"
        formatted = []
        for sec in sections[:30]:
            indent = "  " * (sec.get('level', 1) - 1)
            formatted.append(f"{indent}- {sec.get('title', 'Untitled')}")
        return "\n".join(formatted)

    def _extract_method_sections(self, sections: List[Dict]) -> str:
        """提取方法相关章节（内容截断 3000 字符）"""
        method_keywords = ['method', 'approach', 'model', 'algorithm', 'architecture']
        result = []
        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in method_keywords):
                result.append(f"## {sec.get('title')}\n{sec.get('content', '')[:3000]}")
        return "\n\n".join(result) if result else "N/A"

    def _extract_intro_sections(self, sections: List[Dict]) -> str:
        """提取引言相关章节（内容截断 3000 字符）"""
        intro_keywords = ['introduction', 'background', 'motivation']
        result = []
        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in intro_keywords):
                result.append(f"## {sec.get('title')}\n{sec.get('content', '')[:3000]}")
        return "\n\n".join(result) if result else "N/A"

    def _extract_results_sections(self, sections: List[Dict]) -> str:
        """提取结果相关章节（内容截断 3000 字符）"""
        keywords = ['result', 'experiment', 'evaluation', 'performance']
        result = []
        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in keywords):
                result.append(f"## {sec.get('title')}\n{sec.get('content', '')[:3000]}")
        return "\n\n".join(result) if result else "N/A"

    def _extract_discussion_sections(self, sections: List[Dict]) -> str:
        """提取讨论相关章节（内容截断 3000 字符）"""
        keywords = ['discussion', 'limitation', 'analysis']
        result = []
        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in keywords):
                result.append(f"## {sec.get('title')}\n{sec.get('content', '')[:3000]}")
        return "\n\n".join(result) if result else "N/A"

    def _extract_conclusion_sections(self, sections: List[Dict]) -> str:
        """提取结论相关章节（内容截断 3000 字符）"""
        keywords = ['conclusion', 'future', 'summary']
        result = []
        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in keywords):
                result.append(f"## {sec.get('title')}\n{sec.get('content', '')[:3000]}")
        return "\n\n".join(result) if result else "N/A"


# 使用示例
if __name__ == "__main__":
    import asyncio

    async def main():
        config = AgentConfig(
            name="KnowledgeExtractor",
            model="claude-sonnet-4-5-20250929"
        )

        agent = KnowledgeExtractorAgent(config)

        paper_data = {
            'title': 'Attention Is All You Need',
            'abstract': 'We propose a new architecture called Transformer...',
            'sections': [
                {'title': 'Introduction', 'level': 1, 'content': 'Recent advances...'},
                {'title': 'Model Architecture', 'level': 1, 'content': 'The Transformer...'},
            ]
        }

        result = await agent.process({
            'paper_data': paper_data,
            'extraction_tasks': ['contributions', 'keywords']
        })

        print(json.dumps(result, indent=2))

    asyncio.run(main())
