"""想法管理 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.ideas_manager import IdeasManager

router = APIRouter(prefix="/api/ideas", tags=["ideas"])
manager = IdeasManager(storage_dir=Path("knowledge/ideas"))


class CreateIdeaRequest(BaseModel):
    title: str
    content: str
    related_papers: Optional[List[str]] = None
    tags: Optional[List[str]] = None


@router.post("/")
async def create_idea(req: CreateIdeaRequest):
    idea = manager.create_idea(
        title=req.title,
        content=req.content,
        related_papers=req.related_papers or [],
        tags=req.tags or []
    )
    from dataclasses import asdict
    return {"success": True, "idea": asdict(idea)}


@router.get("/")
async def list_ideas(status: Optional[str] = None, tag: Optional[str] = None):
    if tag:
        ideas = manager.get_ideas_by_tag(tag)
    else:
        ideas = manager.get_all_ideas(status=status)
    from dataclasses import asdict
    return {"ideas": [asdict(i) for i in ideas]}


@router.get("/stats")
async def get_stats():
    return manager.get_statistics()


@router.get("/{idea_id}")
async def get_idea(idea_id: str):
    idea = manager.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"想法 {idea_id} 不存在")
    from dataclasses import asdict
    return asdict(idea)
