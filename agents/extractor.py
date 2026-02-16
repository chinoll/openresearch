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

        prompt = f"""分析以下论文，提取其核心贡献和创新点。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

**章节信息**:
{self._format_sections_brief(paper_data.get('sections', []))}

请识别并列举论文的核心贡献（通常是2-5个主要贡献）。对每个贡献，说明：
1. 贡献内容
2. 创新性（与前人工作的区别）
3. 重要性

以 JSON 格式输出：
```json
{{
  "contributions": [
    {{
      "title": "贡献简短标题",
      "description": "详细描述",
      "novelty": "创新点说明",
      "significance": "重要性评估"
    }}
  ]
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'contributions': []}).get('contributions', [])

    async def _extract_methodology(self, paper_data: Dict) -> Dict:
        """提取方法论"""
        self.log("Extracting methodology...")

        prompt = f"""分析论文使用的研究方法和技术。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

**方法相关章节**:
{self._extract_method_sections(paper_data.get('sections', []))}

**公式数量**: {paper_data.get('equations_count', 0)}

请详细说明：
1. 主要方法和技术
2. 算法/模型架构
3. 实验设计
4. 评估指标

以 JSON 格式输出：
```json
{{
  "approach": "总体方法概述",
  "techniques": ["技术1", "技术2", ...],
  "model_architecture": "模型架构描述",
  "datasets": ["数据集1", "数据集2", ...],
  "evaluation_metrics": ["指标1", "指标2", ...],
  "implementation_details": "实现细节"
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={})

    async def _extract_research_questions(self, paper_data: Dict) -> List[str]:
        """提取研究问题"""
        self.log("Extracting research questions...")

        prompt = f"""识别论文试图回答的核心研究问题。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

**引言部分**:
{self._extract_intro_sections(paper_data.get('sections', []))}

请列出论文的核心研究问题（通常1-3个）。

以 JSON 格式输出：
```json
{{
  "research_questions": [
    "研究问题1",
    "研究问题2",
    ...
  ]
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'research_questions': []}).get('research_questions', [])

    async def _extract_findings(self, paper_data: Dict) -> List[Dict]:
        """提取主要发现和结果"""
        self.log("Extracting key findings...")

        prompt = f"""总结论文的主要发现和实验结果。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

**结果相关章节**:
{self._extract_results_sections(paper_data.get('sections', []))}

**图表数量**: {len(paper_data.get('figures', [])) + len(paper_data.get('tables', []))}

请总结：
1. 主要实验结果
2. 关键发现
3. 性能提升
4. 意外发现（如有）

以 JSON 格式输出：
```json
{{
  "findings": [
    {{
      "finding": "发现描述",
      "evidence": "支持证据",
      "importance": "重要性"
    }}
  ],
  "performance_improvements": "性能提升总结"
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'findings': []}).get('findings', [])

    async def _extract_limitations(self, paper_data: Dict) -> List[str]:
        """提取局限性"""
        self.log("Extracting limitations...")

        prompt = f"""识别论文的局限性和不足。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

**讨论/结论章节**:
{self._extract_discussion_sections(paper_data.get('sections', []))}

请列出论文的主要局限性，包括：
- 方法的局限
- 实验的局限
- 假设的限制
- 适用范围的限制

以 JSON 格式输出：
```json
{{
  "limitations": [
    "局限性1",
    "局限性2",
    ...
  ]
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'limitations': []}).get('limitations', [])

    async def _extract_future_work(self, paper_data: Dict) -> str:
        """提取未来工作方向"""
        self.log("Extracting future work...")

        prompt = f"""总结论文提出的未来研究方向。

**标题**: {paper_data.get('title', 'N/A')}

**结论章节**:
{self._extract_conclusion_sections(paper_data.get('sections', []))}

请总结作者提出的未来研究方向和开放问题。

以 JSON 格式输出：
```json
{{
  "future_work": "未来工作方向的总结",
  "open_questions": ["开放问题1", "开放问题2", ...]
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        result = self._parse_json_response(response, default={})
        return result.get('future_work', '') + '\n' + ', '.join(result.get('open_questions', []))

    async def _extract_keywords(self, paper_data: Dict) -> List[str]:
        """提取关键词"""
        self.log("Extracting keywords...")

        prompt = f"""从论文中提取关键技术术语和概念。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

请提取10-15个最重要的技术关键词。

以 JSON 格式输出：
```json
{{
  "keywords": ["keyword1", "keyword2", ...]
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'keywords': []}).get('keywords', [])

    async def _extract_key_concepts(self, paper_data: Dict) -> List[Dict]:
        """提取核心概念及其关系"""
        self.log("Extracting key concepts...")

        prompt = f"""识别论文中的核心概念及其定义。

**标题**: {paper_data.get('title', 'N/A')}

**摘要**:
{paper_data.get('abstract', 'N/A')}

请识别论文中引入或使用的核心概念（5-10个），包括其定义和在论文中的作用。

以 JSON 格式输出：
```json
{{
  "concepts": [
    {{
      "name": "概念名称",
      "definition": "概念定义",
      "role": "在论文中的作用"
    }}
  ]
}}
```"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return self._parse_json_response(response, default={'concepts': []}).get('concepts', [])

    async def _generate_comprehensive_summary(self, paper_data: Dict, extracted: Dict) -> str:
        """生成综合摘要"""
        self.log("Generating comprehensive summary...")

        prompt = f"""基于提取的信息，生成一个全面的论文摘要（300字以内）。

**论文**: {paper_data.get('title', 'N/A')}

**已提取信息**:
- 核心贡献: {len(extracted.get('contributions', []))} 项
- 方法: {extracted.get('methodology', {}).get('approach', 'N/A')[:100]}
- 研究问题: {len(extracted.get('research_questions', []))} 个
- 主要发现: {len(extracted.get('findings', []))} 项

请生成一个结构化的摘要，包含：
1. 研究背景和动机
2. 主要贡献
3. 使用的方法
4. 关键结果
5. 影响和意义

直接输出摘要文本即可。"""

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    # 辅助方法

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的学术论文分析助手，擅长从论文中提取核心知识和洞察。
你的任务是深入分析论文内容，准确识别和提取关键信息。
请始终以结构化的 JSON 格式输出结果，确保格式正确。"""

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
