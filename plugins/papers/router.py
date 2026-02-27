"""论文管理 API"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plugins.papers.downloader import ArxivDownloader
from core.registry import ModuleRegistration, ModuleType, Capability, InputSchema

router = APIRouter(prefix="/api/papers", tags=["papers"])
downloader = ArxivDownloader(download_dir=Path("papers"))


class DownloadRequest(BaseModel):
    arxiv_id: str


@router.post("/download")
async def download_paper(req: DownloadRequest):
    try:
        arxiv_id = downloader.extract_arxiv_id(req.arxiv_id) or req.arxiv_id.replace(".", "_")
        source_type, file_path, metadata = downloader.download_paper(arxiv_id)
        return {
            "success": True,
            "paper_id": arxiv_id,
            "source_type": source_type,
            "metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_papers():
    papers_dir = Path("papers")
    papers = []
    if papers_dir.exists():
        for paper_dir in papers_dir.iterdir():
            if paper_dir.is_dir():
                meta_file = paper_dir / "metadata.json"
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)
                    papers.append({
                        "paper_id": paper_dir.name,
                        "title": meta.get("title", paper_dir.name),
                        "authors": meta.get("authors", []),
                        "published": meta.get("published", ""),
                        "has_tex": (paper_dir / "source.tex").exists(),
                    })
                else:
                    papers.append({"paper_id": paper_dir.name, "title": paper_dir.name})
    return {"papers": papers}


@router.get("/{paper_id}")
async def get_paper(paper_id: str):
    paper_dir = Path("papers") / paper_id
    if not paper_dir.exists():
        raise HTTPException(status_code=404, detail=f"论文 {paper_id} 不存在")

    meta_file = paper_dir / "metadata.json"
    meta = {}
    if meta_file.exists():
        with open(meta_file) as f:
            meta = json.load(f)

    parsed_file = paper_dir / "parsed_structure.json"
    parsed = {}
    if parsed_file.exists():
        with open(parsed_file) as f:
            parsed = json.load(f)

    return {
        "paper_id": paper_id,
        "metadata": meta,
        "structure": parsed,
        "has_tex": (paper_dir / "source.tex").exists(),
        "has_pdf": (paper_dir / "paper.pdf").exists(),
    }


# Router 注册元数据
ROUTER_REGISTRATION = ModuleRegistration(
    name="papers_router",
    module_type=ModuleType.TOOL,
    display_name="论文管理 API",
    description="论文下载、列表、详情",
    api_prefix="/api/papers",
    api_tags=["papers"],
    capabilities=[
        Capability(
            name="download_paper",
            description="从 arXiv 下载论文（TeX 源文件优先）",
            input_schema=[InputSchema(name="arxiv_id", type="str", description="arXiv 论文 ID，如 1810.04805")],
            tags=["paper", "download"],
        ),
        Capability(name="list_papers", description="列出已下载的论文", tags=["paper", "list"]),
        Capability(
            name="get_paper_info",
            description="获取指定论文的详细信息（标题、作者、摘要、章节等）",
            input_schema=[InputSchema(name="paper_id", type="str", description="论文 ID，如 1810_04805")],
            tags=["paper", "detail"],
        ),
    ],
)


# Tool handlers — 供 chat_router 自动收集
async def _h_download_paper(tool_input):
    req = DownloadRequest(arxiv_id=tool_input["arxiv_id"])
    result = await download_paper(req)
    result["display_type"] = "confirmation"
    return result

async def _h_list_papers(tool_input):
    result = await list_papers()
    result["display_type"] = "paper_list"
    return result

async def _h_get_paper_info(tool_input):
    result = await get_paper(tool_input["paper_id"])
    result["display_type"] = "paper_detail"
    return result

TOOL_HANDLERS = {
    "download_paper": _h_download_paper,
    "list_papers": _h_list_papers,
    "get_paper_info": _h_get_paper_info,
}
