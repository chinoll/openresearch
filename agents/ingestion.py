"""
Paper Ingestion Agent - 论文摄入 Agent
负责下载、解析论文，优先处理 TeX 源文件
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse
from core.arxiv_downloader import ArxivDownloader
from core.tex_parser import TeXParser, TexDocument
from prompts.loader import load as load_prompt


class PaperIngestionAgent(BaseAgent):
    """论文摄入 Agent - 优先 TeX 源文件"""

    def __init__(self, config: AgentConfig, download_dir: Path):
        super().__init__(config)

        self.download_dir = Path(download_dir)
        self.downloader = ArxivDownloader(
            download_dir=self.download_dir,
            prefer_tex=True
        )
        self.tex_parser = TeXParser(
            extract_comments=True,
            extract_equations=True,
            extract_citations=True
        )

        self.log("Paper Ingestion Agent initialized")

    async def process(self, input_data: Dict) -> Dict:
        """
        处理论文摄入请求

        Args:
            input_data: {
                'source': 'arxiv' | 'local',
                'identifier': arXiv ID 或本地文件路径,
                'metadata': 可选的额外元数据
            }

        Returns:
            处理结果，包含解析后的论文数据
        """
        source = input_data.get('source', 'arxiv')
        identifier = input_data.get('identifier')

        if not identifier:
            return AgentResponse(
                success=False,
                error="No identifier provided"
            ).to_dict()

        try:
            if source == 'arxiv':
                result = await self._process_arxiv(identifier)
            elif source == 'local':
                result = await self._process_local(identifier)
            else:
                return AgentResponse(
                    success=False,
                    error=f"Unknown source: {source}"
                ).to_dict()

            return AgentResponse(success=True, data=result).to_dict()

        except Exception as e:
            self.log(f"Error processing paper: {e}", "error")
            return AgentResponse(success=False, error=str(e)).to_dict()

    async def _process_arxiv(self, arxiv_id: str) -> Dict:
        """处理 arXiv 论文"""
        self.log(f"Processing arXiv paper: {arxiv_id}")

        # 下载论文（优先 TeX）
        source_type, file_path, metadata = self.downloader.download_paper(arxiv_id)

        # 解析内容
        if source_type == 'tex':
            parsed_data = self._parse_tex_source(file_path)
        else:  # pdf
            parsed_data = self._parse_pdf(file_path)

        # 合并元数据
        parsed_data['metadata'].update(metadata)
        parsed_data['source_type'] = source_type
        parsed_data['file_path'] = str(file_path)

        # 使用 LLM 进行深度分析
        analysis = await self._analyze_with_llm(parsed_data)
        parsed_data['ai_analysis'] = analysis

        # 保存处理结果
        self._save_processed_data(arxiv_id, parsed_data)

        self.log(f"✓ Successfully processed arXiv paper: {arxiv_id}")
        return parsed_data

    async def _process_local(self, file_path: str) -> Dict:
        """处理本地论文文件"""
        self.log(f"Processing local file: {file_path}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 根据文件类型处理
        if path.suffix == '.tex':
            parsed_data = self._parse_tex_file(path)
            source_type = 'tex'
        elif path.suffix == '.pdf':
            parsed_data = self._parse_pdf(path)
            source_type = 'pdf'
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        parsed_data['source_type'] = source_type
        parsed_data['file_path'] = str(path)

        # AI 分析
        analysis = await self._analyze_with_llm(parsed_data)
        parsed_data['ai_analysis'] = analysis

        self.log(f"✓ Successfully processed local file: {file_path}")
        return parsed_data

    def _parse_tex_source(self, tex_dir: Path) -> Dict:
        """解析 TeX 源文件目录"""
        self.log(f"Parsing TeX source: {tex_dir}")

        # 查找主 .tex 文件
        main_tex = self.tex_parser.find_main_tex_file(tex_dir)
        if not main_tex:
            raise FileNotFoundError(f"No main .tex file found in {tex_dir}")

        # 解析 TeX 文件
        doc = self.tex_parser.parse_file(main_tex)

        return self.tex_parser.to_dict(doc)

    def _parse_tex_file(self, tex_file: Path) -> Dict:
        """解析单个 TeX 文件"""
        doc = self.tex_parser.parse_file(tex_file)
        return self.tex_parser.to_dict(doc)

    def _parse_pdf(self, pdf_path: Path) -> Dict:
        """解析 PDF 文件（降级方案）"""
        self.log(f"Parsing PDF: {pdf_path}", "warning")

        # TODO: 实现 PDF 解析
        # 这里可以使用 PyPDF2, pdfplumber 等库
        # 暂时返回基础结构

        return {
            'title': pdf_path.stem,
            'authors': [],
            'abstract': '',
            'sections': [],
            'citations': [],
            'equations_count': 0,
            'figures': [],
            'tables': [],
            'comments_count': 0,
            'metadata': {
                'source': 'pdf',
                'note': 'PDF parsing not yet fully implemented'
            }
        }

    async def _analyze_with_llm(self, parsed_data: Dict) -> Dict:
        """使用 LLM 对论文进行深度分析"""
        if not self.llm_client:
            self.log("LLM not available, skipping AI analysis", "warning")
            return {
                'summary': '',
                'key_contributions': [],
                'methodology': '',
                'limitations': [],
                'research_direction': ''
            }

        self.log("Performing AI analysis...")

        # 构建分析提示词
        prompt = self._build_analysis_prompt(parsed_data)

        system_prompt = load_prompt("system/ingestion")

        try:
            response = self.call_llm(prompt, system_prompt)

            # 解析 JSON 响应
            # 尝试提取 JSON（可能包含在 markdown 代码块中）
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                analysis = json.loads(response)

            return analysis

        except Exception as e:
            self.log(f"Error in AI analysis: {e}", "error")
            return {
                'summary': response[:500] if response else '',
                'error': str(e)
            }

    def _build_analysis_prompt(self, parsed_data: Dict) -> str:
        """构建 AI 分析的提示词"""
        return load_prompt(
            "ingestion/analyze_paper",
            title=parsed_data.get('title', 'N/A'),
            authors=', '.join(parsed_data.get('authors', [])),
            abstract=parsed_data.get('abstract', 'N/A'),
            sections=self._format_sections(parsed_data.get('sections', [])),
            citations_count=str(len(parsed_data.get('citations', []))),
            equations_count=str(parsed_data.get('equations_count', 0)),
            figures_count=str(len(parsed_data.get('figures', [])) + len(parsed_data.get('tables', []))),
        )

    def _format_sections(self, sections: list) -> str:
        """格式化章节列表"""
        if not sections:
            return "N/A"

        formatted = []
        for sec in sections[:10]:  # 限制数量
            indent = "  " * (sec.get('level', 1) - 1)
            formatted.append(f"{indent}- {sec.get('title', 'Untitled')}")

        return "\n".join(formatted)

    def _save_processed_data(self, paper_id: str, data: Dict):
        """保存处理后的数据"""
        metadata_dir = self.download_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        output_file = metadata_dir / f"{paper_id.replace('.', '_')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.log(f"Saved processed data to: {output_file}")


# 使用示例
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    async def main():
        # 创建 Agent
        config = AgentConfig(
            name="PaperIngestionAgent",
            model="claude-sonnet-4-5-20250929",
            # api_key="your-api-key-here"  # 实际使用时设置
        )

        agent = PaperIngestionAgent(
            config=config,
            download_dir=Path("./data/papers")
        )

        # 测试处理 arXiv 论文
        result = await agent.process({
            'source': 'arxiv',
            'identifier': '2301.00001'  # 替换为真实的 arXiv ID
        })

        print(json.dumps(result, indent=2))

    asyncio.run(main())
