"""
TeX Source Parser - 解析 LaTeX 源文件提取结构化信息
优先于 PDF 解析，提供更丰富的语义信息
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

try:
    from TexSoup import TexSoup
except ImportError:
    TexSoup = None

try:
    from pylatexenc.latex2text import LatexNodes2Text
except ImportError:
    LatexNodes2Text = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TexDocument:
    """TeX 文档结构化数据"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    sections: List[Dict[str, str]] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    equations: List[str] = field(default_factory=list)
    figures: List[Dict[str, str]] = field(default_factory=list)
    tables: List[Dict[str, str]] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    raw_text: str = ""
    metadata: Dict = field(default_factory=dict)


class TeXParser:
    """TeX 源文件解析器"""

    def __init__(self, extract_comments: bool = True,
                 extract_equations: bool = True,
                 extract_citations: bool = True):
        self.extract_comments = extract_comments
        self.extract_equations = extract_equations
        self.extract_citations = extract_citations

        if LatexNodes2Text:
            self.latex_converter = LatexNodes2Text()
        else:
            logger.warning("pylatexenc not installed, using regex-based conversion")
            self.latex_converter = None

    def find_main_tex_file(self, source_dir: Path) -> Optional[Path]:
        """在解压的源文件目录中找到主 .tex 文件"""
        tex_files = list(source_dir.glob("*.tex"))

        if not tex_files:
            logger.warning(f"No .tex files found in {source_dir}")
            return None

        # 优先查找包含 \documentclass 的文件
        for tex_file in tex_files:
            try:
                with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000)  # 只读前1000字符
                    if r'\documentclass' in content:
                        return tex_file
            except Exception as e:
                logger.debug(f"Error reading {tex_file}: {e}")
                continue

        # 如果都没有，选择最大的文件
        return max(tex_files, key=lambda f: f.stat().st_size)

    def parse_file(self, tex_path: Path) -> TexDocument:
        """解析单个 TeX 文件"""
        logger.info(f"Parsing TeX file: {tex_path}")

        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        return self.parse_content(content)

    def parse_content(self, content: str) -> TexDocument:
        """解析 TeX 内容"""
        doc = TexDocument()
        doc.raw_text = content

        # 提取标题
        doc.title = self._extract_title(content)

        # 提取作者
        doc.authors = self._extract_authors(content)

        # 提取摘要
        doc.abstract = self._extract_abstract(content)

        # 提取章节
        doc.sections = self._extract_sections(content)

        # 提取引用
        if self.extract_citations:
            doc.citations = self._extract_citations(content)

        # 提取公式
        if self.extract_equations:
            doc.equations = self._extract_equations(content)

        # 提取图表
        doc.figures = self._extract_figures(content)
        doc.tables = self._extract_tables(content)

        # 提取注释
        if self.extract_comments:
            doc.comments = self._extract_comments(content)

        return doc

    def _extract_title(self, content: str) -> str:
        """提取标题"""
        # 尝试匹配 \title{...}
        pattern = r'\\title\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            title = match.group(1).strip()
            return self._latex_to_text(title)
        return ""

    def _extract_authors(self, content: str) -> List[str]:
        """提取作者列表"""
        authors = []

        # 匹配 \author{...}
        pattern = r'\\author\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            author_block = match.group(1)
            # 分割多个作者（通过 \and 或 逗号）
            author_parts = re.split(r'\\and|,', author_block)
            for author in author_parts:
                author_clean = self._latex_to_text(author).strip()
                if author_clean and len(author_clean) > 2:
                    authors.append(author_clean)

        return authors

    def _extract_abstract(self, content: str) -> str:
        """提取摘要"""
        # 匹配 \begin{abstract}...\end{abstract}
        pattern = r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            return self._latex_to_text(abstract)
        return ""

    def _extract_sections(self, content: str) -> List[Dict[str, str]]:
        """提取章节结构"""
        sections = []

        # 匹配各级标题
        section_patterns = [
            (r'\\section\s*\{([^}]+)\}', 'section', 1),
            (r'\\subsection\s*\{([^}]+)\}', 'subsection', 2),
            (r'\\subsubsection\s*\{([^}]+)\}', 'subsubsection', 3),
        ]

        for pattern, section_type, level in section_patterns:
            for match in re.finditer(pattern, content):
                title = self._latex_to_text(match.group(1))
                sections.append({
                    'type': section_type,
                    'level': level,
                    'title': title,
                    'position': match.start()
                })

        # 按位置排序
        sections.sort(key=lambda x: x['position'])

        # 提取每个章节的内容
        for i, section in enumerate(sections):
            start = section['position']
            end = sections[i + 1]['position'] if i + 1 < len(sections) else len(content)
            section_content = content[start:end]
            section['content'] = self._latex_to_text(section_content)[:500]  # 限制长度

        return sections

    def _extract_citations(self, content: str) -> List[str]:
        """提取引用"""
        citations = set()

        # 匹配 \cite{...}, \citep{...}, \citet{...} 等
        cite_pattern = r'\\cite[tp]?\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}'
        for match in re.finditer(cite_pattern, content):
            cite_keys = match.group(1).split(',')
            for key in cite_keys:
                citations.add(key.strip())

        return sorted(list(citations))

    def _extract_equations(self, content: str) -> List[str]:
        """提取数学公式"""
        equations = []

        # 匹配各种公式环境
        equation_patterns = [
            r'\\begin\{equation\}(.*?)\\end\{equation\}',
            r'\\begin\{align\}(.*?)\\end\{align\}',
            r'\\begin\{gather\}(.*?)\\end\{gather\}',
            r'\$\$([^\$]+)\$\$',  # 显示公式
            r'\\\[(.*?)\\\]',      # 显示公式
        ]

        for pattern in equation_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                eq = match.group(1).strip()
                if eq and len(eq) > 3:  # 过滤太短的
                    equations.append(eq)

        return equations

    def _extract_figures(self, content: str) -> List[Dict[str, str]]:
        """提取图片信息"""
        figures = []

        # 匹配 \begin{figure}...\end{figure}
        figure_pattern = r'\\begin\{figure\}(.*?)\\end\{figure\}'
        for match in re.finditer(figure_pattern, content, re.DOTALL):
            figure_content = match.group(1)

            # 提取 caption
            caption_match = re.search(r'\\caption\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
                                     figure_content, re.DOTALL)
            caption = ""
            if caption_match:
                caption = self._latex_to_text(caption_match.group(1))

            # 提取 label
            label_match = re.search(r'\\label\{([^}]+)\}', figure_content)
            label = label_match.group(1) if label_match else ""

            # 提取文件名
            graphics_match = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',
                                      figure_content)
            filename = graphics_match.group(1) if graphics_match else ""

            figures.append({
                'caption': caption,
                'label': label,
                'filename': filename
            })

        return figures

    def _extract_tables(self, content: str) -> List[Dict[str, str]]:
        """提取表格信息"""
        tables = []

        # 匹配 \begin{table}...\end{table}
        table_pattern = r'\\begin\{table\}(.*?)\\end\{table\}'
        for match in re.finditer(table_pattern, content, re.DOTALL):
            table_content = match.group(1)

            # 提取 caption
            caption_match = re.search(r'\\caption\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
                                     table_content, re.DOTALL)
            caption = ""
            if caption_match:
                caption = self._latex_to_text(caption_match.group(1))

            # 提取 label
            label_match = re.search(r'\\label\{([^}]+)\}', table_content)
            label = label_match.group(1) if label_match else ""

            tables.append({
                'caption': caption,
                'label': label
            })

        return tables

    def _extract_comments(self, content: str) -> List[str]:
        """提取 TeX 注释（可能包含作者的思考过程）"""
        comments = []

        # 匹配 % 开头的注释（不在字符串内）
        for line in content.split('\n'):
            # 简单匹配（可以改进以处理 % 转义的情况）
            if '%' in line and not line.strip().startswith('\\'):
                comment_start = line.find('%')
                comment = line[comment_start + 1:].strip()
                if len(comment) > 5:  # 过滤太短的注释
                    comments.append(comment)

        return comments

    def _latex_to_text(self, latex_str: str) -> str:
        """将 LaTeX 命令转换为纯文本"""
        if not latex_str:
            return ""

        # 使用 pylatexenc 转换
        if self.latex_converter:
            try:
                return self.latex_converter.latex_to_text(latex_str)
            except Exception as e:
                logger.debug(f"Error converting LaTeX: {e}")

        # 降级到基于正则的简单转换
        text = latex_str

        # 移除常见的 LaTeX 命令
        replacements = [
            (r'\\textbf\{([^}]+)\}', r'\1'),
            (r'\\textit\{([^}]+)\}', r'\1'),
            (r'\\emph\{([^}]+)\}', r'\1'),
            (r'\\text\{([^}]+)\}', r'\1'),
            (r'\\cite[tp]?\{[^}]+\}', '[citation]'),
            (r'\\ref\{[^}]+\}', '[ref]'),
            (r'\\label\{[^}]+\}', ''),
            (r'\\[a-zA-Z]+\{([^}]+)\}', r'\1'),  # 通用命令
            (r'\\[a-zA-Z]+', ''),  # 无参数命令
            (r'\$([^\$]+)\$', r'\1'),  # 行内公式
            (r'[{}]', ''),  # 移除花括号
        ]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        # 清理多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def to_dict(self, doc: TexDocument) -> Dict:
        """将 TexDocument 转换为字典"""
        return {
            'title': doc.title,
            'authors': doc.authors,
            'abstract': doc.abstract,
            'sections': doc.sections,
            'citations': doc.citations,
            'equations_count': len(doc.equations),
            'figures': doc.figures,
            'tables': doc.tables,
            'comments_count': len(doc.comments),
            'metadata': doc.metadata
        }


# 使用示例
if __name__ == "__main__":
    parser = TeXParser()

    # 示例 TeX 内容
    sample_tex = r"""
    \documentclass{article}
    \title{Deep Learning for Natural Language Processing}
    \author{John Doe \and Jane Smith}
    \begin{document}
    \begin{abstract}
    This paper presents a novel approach to NLP using deep learning.
    \end{abstract}

    \section{Introduction}
    Natural language processing has evolved significantly.
    % This is an important note about the approach

    \subsection{Background}
    Previous work \cite{smith2020} has shown...

    \begin{equation}
    E = mc^2
    \end{equation}

    \end{document}
    """

    doc = parser.parse_content(sample_tex)
    print(f"Title: {doc.title}")
    print(f"Authors: {doc.authors}")
    print(f"Abstract: {doc.abstract}")
    print(f"Sections: {len(doc.sections)}")
    print(f"Citations: {doc.citations}")
