"""
Knowledge Extractor Agent - 知识提取 Agent
深度分析论文内容，提取核心知识和洞察
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
import re

sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse
from prompts.loader import load as load_prompt


class KnowledgeExtractorAgent(BaseAgent):
    """知识提取 Agent - 深度分析论文内容"""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.log("Knowledge Extractor Agent initialized")

    async def process(self, input_data: Dict) -> Dict:
        """
        处理知识提取请求

        Args:
            input_data: {
                'paper_data': 论文解析数据,
                'extraction_tasks': ['contributions', 'methodology', 'limitations', ...]
            }

        Returns:
            提取的知识
        """
        paper_data = input_data.get('paper_data')
        if not paper_data:
            return AgentResponse(
                success=False,
                error="No paper data provided"
            ).to_dict()

        extraction_tasks = input_data.get('extraction_tasks', [
            'contributions',
            'methodology',
            'research_questions',
            'findings',
            'limitations',
            'future_work',
            'keywords',
            'concepts'
        ])

        try:
            extracted_knowledge = {}

            # 执行各项提取任务
            if 'contributions' in extraction_tasks:
                extracted_knowledge['contributions'] = await self._extract_contributions(paper_data)

            if 'methodology' in extraction_tasks:
                extracted_knowledge['methodology'] = await self._extract_methodology(paper_data)

            if 'research_questions' in extraction_tasks:
                extracted_knowledge['research_questions'] = await self._extract_research_questions(paper_data)

            if 'findings' in extraction_tasks:
                extracted_knowledge['findings'] = await self._extract_findings(paper_data)

            if 'limitations' in extraction_tasks:
                extracted_knowledge['limitations'] = await self._extract_limitations(paper_data)

            if 'future_work' in extraction_tasks:
                extracted_knowledge['future_work'] = await self._extract_future_work(paper_data)

            if 'keywords' in extraction_tasks:
                extracted_knowledge['keywords'] = await self._extract_keywords(paper_data)

            if 'concepts' in extraction_tasks:
                extracted_knowledge['concepts'] = await self._extract_key_concepts(paper_data)

            # 综合分析
            extracted_knowledge['summary'] = await self._generate_comprehensive_summary(
                paper_data,
                extracted_knowledge
            )

            self.log("✓ Knowledge extraction completed")
            return AgentResponse(success=True, data=extracted_knowledge).to_dict()

        except Exception as e:
            self.log(f"Error in knowledge extraction: {e}", "error")
            return AgentResponse(success=False, error=str(e)).to_dict()

    async def _extract_contributions(self, paper_data: Dict) -> List[Dict]:
        """提取核心贡献"""
        self.log("Extracting core contributions...")

        prompt = load_prompt(
            "extractor/contributions",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            sections_brief=self._format_sections_brief(paper_data.get('sections', [])),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'contributions': []}).get('contributions', [])

    async def _extract_methodology(self, paper_data: Dict) -> Dict:
        """提取方法论"""
        self.log("Extracting methodology...")

        prompt = load_prompt(
            "extractor/methodology",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            method_sections=self._extract_method_sections(paper_data.get('sections', [])),
            equations_count=str(paper_data.get('equations_count', 0)),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={})

    async def _extract_research_questions(self, paper_data: Dict) -> List[str]:
        """提取研究问题"""
        self.log("Extracting research questions...")

        prompt = load_prompt(
            "extractor/research_questions",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            intro_sections=self._extract_intro_sections(paper_data.get('sections', [])),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'research_questions': []}).get('research_questions', [])

    async def _extract_findings(self, paper_data: Dict) -> List[Dict]:
        """提取主要发现和结果"""
        self.log("Extracting key findings...")

        prompt = load_prompt(
            "extractor/findings",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            results_sections=self._extract_results_sections(paper_data.get('sections', [])),
            figures_count=str(len(paper_data.get('figures', [])) + len(paper_data.get('tables', []))),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'findings': []}).get('findings', [])

    async def _extract_limitations(self, paper_data: Dict) -> List[str]:
        """提取局限性"""
        self.log("Extracting limitations...")

        prompt = load_prompt(
            "extractor/limitations",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
            discussion_sections=self._extract_discussion_sections(paper_data.get('sections', [])),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'limitations': []}).get('limitations', [])

    async def _extract_future_work(self, paper_data: Dict) -> str:
        """提取未来工作方向"""
        self.log("Extracting future work...")

        prompt = load_prompt(
            "extractor/future_work",
            title=paper_data.get('title', 'N/A'),
            conclusion_sections=self._extract_conclusion_sections(paper_data.get('sections', [])),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        result = self._parse_json_response(response, default={})
        return result.get('future_work', '') + '\n' + ', '.join(result.get('open_questions', []))

    async def _extract_keywords(self, paper_data: Dict) -> List[str]:
        """提取关键词"""
        self.log("Extracting keywords...")

        prompt = load_prompt(
            "extractor/keywords",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'keywords': []}).get('keywords', [])

    async def _extract_key_concepts(self, paper_data: Dict) -> List[Dict]:
        """提取核心概念及其关系"""
        self.log("Extracting key concepts...")

        prompt = load_prompt(
            "extractor/concepts",
            title=paper_data.get('title', 'N/A'),
            abstract=paper_data.get('abstract', 'N/A'),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'concepts': []}).get('concepts', [])

    async def _generate_comprehensive_summary(self, paper_data: Dict, extracted: Dict) -> str:
        """生成综合摘要"""
        self.log("Generating comprehensive summary...")

        prompt = load_prompt(
            "extractor/summary",
            title=paper_data.get('title', 'N/A'),
            contributions_count=str(len(extracted.get('contributions', []))),
            methodology_approach=extracted.get('methodology', {}).get('approach', 'N/A')[:100],
            questions_count=str(len(extracted.get('research_questions', []))),
            findings_count=str(len(extracted.get('findings', []))),
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    # 辅助方法

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return load_prompt("system/extractor")

    def _format_sections_brief(self, sections: List[Dict]) -> str:
        """简要格式化章节"""
        if not sections:
            return "N/A"

        formatted = []
        for sec in sections[:15]:  # 限制数量
            indent = "  " * (sec.get('level', 1) - 1)
            formatted.append(f"{indent}- {sec.get('title', 'Untitled')}")

        return "\n".join(formatted)

    def _extract_method_sections(self, sections: List[Dict]) -> str:
        """提取方法相关章节"""
        method_keywords = ['method', 'approach', 'model', 'algorithm', 'architecture']
        method_sections = []

        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in method_keywords):
                method_sections.append(f"## {sec.get('title')}\n{sec.get('content', '')[:300]}")

        return "\n\n".join(method_sections) if method_sections else "N/A"

    def _extract_intro_sections(self, sections: List[Dict]) -> str:
        """提取引言相关章节"""
        intro_keywords = ['introduction', 'background', 'motivation']
        intro_sections = []

        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in intro_keywords):
                intro_sections.append(f"## {sec.get('title')}\n{sec.get('content', '')[:300]}")

        return "\n\n".join(intro_sections) if intro_sections else "N/A"

    def _extract_results_sections(self, sections: List[Dict]) -> str:
        """提取结果相关章节"""
        results_keywords = ['result', 'experiment', 'evaluation', 'performance']
        results_sections = []

        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in results_keywords):
                results_sections.append(f"## {sec.get('title')}\n{sec.get('content', '')[:300]}")

        return "\n\n".join(results_sections) if results_sections else "N/A"

    def _extract_discussion_sections(self, sections: List[Dict]) -> str:
        """提取讨论相关章节"""
        discussion_keywords = ['discussion', 'limitation', 'analysis']
        discussion_sections = []

        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in discussion_keywords):
                discussion_sections.append(f"## {sec.get('title')}\n{sec.get('content', '')[:300]}")

        return "\n\n".join(discussion_sections) if discussion_sections else "N/A"

    def _extract_conclusion_sections(self, sections: List[Dict]) -> str:
        """提取结论相关章节"""
        conclusion_keywords = ['conclusion', 'future', 'summary']
        conclusion_sections = []

        for sec in sections:
            title_lower = sec.get('title', '').lower()
            if any(kw in title_lower for kw in conclusion_keywords):
                conclusion_sections.append(f"## {sec.get('title')}\n{sec.get('content', '')[:300]}")

        return "\n\n".join(conclusion_sections) if conclusion_sections else "N/A"

    def _parse_json_response(self, response: str, default: Dict = None) -> Dict:
        """解析 JSON 响应"""
        try:
            # 尝试提取 JSON（可能在 markdown 代码块中）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试直接解析
            # 找到第一个 { 和最后一个 }
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                return json.loads(json_str)

        except json.JSONDecodeError as e:
            self.log(f"JSON parse error: {e}", "warning")
        except Exception as e:
            self.log(f"Error parsing response: {e}", "warning")

        return default or {}


# 使用示例
if __name__ == "__main__":
    import asyncio

    async def main():
        config = AgentConfig(
            name="KnowledgeExtractor",
            model="claude-sonnet-4-5-20250929"
        )

        agent = KnowledgeExtractorAgent(config)

        # 模拟论文数据
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
