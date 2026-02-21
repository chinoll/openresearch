"""
ArXiv Downloader - 优先下载 TeX 源文件
如果 TeX 源不可用，则降级到 PDF
"""

import os
import re
import tarfile
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
import requests
import arxiv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArxivDownloader:
    """arXiv 论文下载器，优先 TeX 源文件"""

    from core.registry import ModuleRegistration, ModuleType, Capability, ConstructorParam
    REGISTRATION = ModuleRegistration(
        name="arxiv_downloader",
        module_type=ModuleType.CORE_SERVICE,
        display_name="arXiv 下载器",
        description="从 arXiv 下载论文（优先 TeX 源文件，降级到 PDF）",
        constructor_params=[
            ConstructorParam(name="download_dir", from_config="storage.papers", default="./data/papers"),
            ConstructorParam(name="prefer_tex", default=True),
        ],
        capabilities=[
            Capability(name="download_paper", description="下载 arXiv 论文", tags=["download", "arxiv"]),
            Capability(name="get_paper_info", description="获取论文元数据", tags=["metadata", "arxiv"]),
        ],
    )
    del ModuleRegistration, ModuleType, Capability, ConstructorParam

    def __init__(self, download_dir: Path, prefer_tex: bool = True):
        """
        Args:
            download_dir: 下载目录
            prefer_tex: 是否优先下载 TeX 源文件
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.prefer_tex = prefer_tex

        # TeX 源文件存储目录
        self.tex_dir = self.download_dir / "tex_sources"
        self.tex_dir.mkdir(exist_ok=True)

        # PDF 存储目录
        self.pdf_dir = self.download_dir / "pdfs"
        self.pdf_dir.mkdir(exist_ok=True)

    def extract_arxiv_id(self, input_str: str) -> Optional[str]:
        """
        从各种输入格式提取 arXiv ID

        支持格式:
        - 2301.00001
        - arXiv:2301.00001
        - https://arxiv.org/abs/2301.00001
        - https://arxiv.org/pdf/2301.00001.pdf
        """
        # 移除空白
        input_str = input_str.strip()

        # 已经是标准 ID 格式
        pattern1 = r'^\d{4}\.\d{5}$'
        if re.match(pattern1, input_str):
            return input_str

        # arXiv:ID 格式
        pattern2 = r'arXiv:(\d{4}\.\d{5})'
        match = re.search(pattern2, input_str, re.IGNORECASE)
        if match:
            return match.group(1)

        # URL 格式
        pattern3 = r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{5})'
        match = re.search(pattern3, input_str)
        if match:
            return match.group(1)

        logger.warning(f"Could not extract arXiv ID from: {input_str}")
        return None

    def download_paper(self, arxiv_id: str) -> Tuple[str, Optional[Path], Dict]:
        """
        下载论文（优先 TeX 源文件）

        Returns:
            (source_type, file_path, metadata)
            source_type: 'tex' 或 'pdf'
            file_path: 下载文件的路径
            metadata: 论文元数据
        """
        # 提取规范的 arXiv ID
        arxiv_id = self.extract_arxiv_id(arxiv_id)
        if not arxiv_id:
            raise ValueError(f"Invalid arXiv ID: {arxiv_id}")

        logger.info(f"Processing arXiv paper: {arxiv_id}")

        # 获取论文元数据
        metadata = self._fetch_metadata(arxiv_id)

        if self.prefer_tex:
            # 尝试下载 TeX 源文件
            tex_path = self._download_tex_source(arxiv_id)
            if tex_path:
                logger.info(f"✓ TeX source downloaded: {tex_path}")
                return 'tex', tex_path, metadata

            logger.info("TeX source not available, falling back to PDF")

        # 降级到 PDF
        pdf_path = self._download_pdf(arxiv_id, metadata)
        logger.info(f"✓ PDF downloaded: {pdf_path}")
        return 'pdf', pdf_path, metadata

    def _fetch_metadata(self, arxiv_id: str) -> Dict:
        """获取论文元数据"""
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results())

            metadata = {
                'arxiv_id': arxiv_id,
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'abstract': paper.summary,
                'published': paper.published.isoformat() if paper.published else None,
                'updated': paper.updated.isoformat() if paper.updated else None,
                'categories': paper.categories,
                'primary_category': paper.primary_category,
                'doi': paper.doi,
                'journal_ref': paper.journal_ref,
                'pdf_url': paper.pdf_url,
            }

            return metadata

        except Exception as e:
            logger.error(f"Error fetching metadata for {arxiv_id}: {e}")
            return {
                'arxiv_id': arxiv_id,
                'title': '',
                'authors': [],
                'abstract': '',
            }

    def _download_tex_source(self, arxiv_id: str) -> Optional[Path]:
        """
        下载并解压 TeX 源文件

        arXiv 源文件 URL 格式: https://arxiv.org/e-print/XXXX.XXXXX
        通常是 .tar.gz 格式
        """
        source_url = f"https://arxiv.org/e-print/{arxiv_id}"

        # 创建论文专属目录
        paper_tex_dir = self.tex_dir / arxiv_id.replace('.', '_')
        paper_tex_dir.mkdir(exist_ok=True)

        # 下载源文件
        tar_path = paper_tex_dir / f"{arxiv_id}.tar.gz"

        try:
            logger.info(f"Downloading TeX source from {source_url}")
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()

            # 保存压缩文件
            with open(tar_path, 'wb') as f:
                f.write(response.content)

            # 检查文件类型并解压
            if self._is_tarfile(tar_path):
                logger.info(f"Extracting tar archive: {tar_path}")
                with tarfile.open(tar_path, 'r:*') as tar:
                    tar.extractall(path=paper_tex_dir)
                tar_path.unlink()  # 删除压缩文件
                return paper_tex_dir

            # 如果不是 tar 文件，可能直接是单个 .tex 文件
            elif tar_path.read_text(errors='ignore').startswith('%') or \
                 '\\documentclass' in tar_path.read_text(errors='ignore')[:1000]:
                tex_file = paper_tex_dir / f"{arxiv_id}.tex"
                tar_path.rename(tex_file)
                return paper_tex_dir

            else:
                logger.warning(f"Downloaded file is not a valid TeX source: {tar_path}")
                tar_path.unlink()
                return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.info(f"TeX source not available for {arxiv_id} (403 Forbidden)")
            else:
                logger.warning(f"HTTP error downloading TeX source: {e}")
            return None

        except Exception as e:
            logger.error(f"Error downloading TeX source: {e}")
            return None

    def _download_pdf(self, arxiv_id: str, metadata: Dict) -> Path:
        """下载 PDF 文件"""
        pdf_url = metadata.get('pdf_url') or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = self.pdf_dir / f"{arxiv_id.replace('.', '_')}.pdf"

        try:
            # 使用 arxiv 库下载（更可靠）
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results())
            paper.download_pdf(dirpath=str(self.pdf_dir),
                             filename=f"{arxiv_id.replace('.', '_')}.pdf")

            logger.info(f"PDF downloaded: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"Error downloading PDF with arxiv library: {e}")

            # 降级到直接 HTTP 下载
            try:
                logger.info(f"Trying direct download from {pdf_url}")
                response = requests.get(pdf_url, timeout=30)
                response.raise_for_status()

                with open(pdf_path, 'wb') as f:
                    f.write(response.content)

                return pdf_path

            except Exception as e2:
                logger.error(f"Error downloading PDF directly: {e2}")
                raise

    def _is_tarfile(self, path: Path) -> bool:
        """检查文件是否为 tar 压缩文件"""
        try:
            return tarfile.is_tarfile(path)
        except Exception:
            return False

    def get_paper_info(self, arxiv_id: str) -> Dict:
        """仅获取论文信息，不下载"""
        arxiv_id = self.extract_arxiv_id(arxiv_id)
        if not arxiv_id:
            raise ValueError(f"Invalid arXiv ID: {arxiv_id}")

        return self._fetch_metadata(arxiv_id)


# 使用示例
if __name__ == "__main__":
    downloader = ArxivDownloader(
        download_dir=Path("./data/papers"),
        prefer_tex=True
    )

    # 测试下载
    test_papers = [
        "2301.00001",  # 标准格式
        "https://arxiv.org/abs/2401.12345",  # URL 格式
        "arXiv:2312.54321",  # arXiv: 前缀
    ]

    for paper_id in test_papers[:1]:  # 只测试第一个
        try:
            source_type, file_path, metadata = downloader.download_paper(paper_id)
            print(f"\n{'='*60}")
            print(f"Paper: {metadata['title']}")
            print(f"Authors: {', '.join(metadata['authors'][:3])}")
            print(f"Source Type: {source_type}")
            print(f"File Path: {file_path}")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"Error processing {paper_id}: {e}")
