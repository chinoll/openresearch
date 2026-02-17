"""论文管理 API"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.arxiv_downloader import ArxivDownloader

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
