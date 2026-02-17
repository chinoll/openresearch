"""洞察管理 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.insights_system import InsightsManager

router = APIRouter(prefix="/api/insights", tags=["insights"])
manager = InsightsManager(storage_dir=Path("knowledge"))


class CreateInsightRequest(BaseModel):
    content: str
    paper_id: str
    insight_type: str = "observation"
    importance: int = 3
    section: Optional[str] = None
    quote: Optional[str] = None
    tags: Optional[List[str]] = None


class StartSessionRequest(BaseModel):
    paper_id: str
    notes: str = ""


@router.post("/")
async def create_insight(req: CreateInsightRequest):
    insight = manager.create_insight(
        content=req.content,
        paper_id=req.paper_id,
        insight_type=req.insight_type,
        importance=req.importance,
        section=req.section,
        quote=req.quote,
        tags=req.tags or []
    )
    from dataclasses import asdict
    return {"success": True, "insight": asdict(insight)}


@router.get("/")
async def list_insights(
    paper_id: Optional[str] = None,
    insight_type: Optional[str] = None,
    unconverted_only: bool = False
):
    if unconverted_only:
        insights = manager.get_unconverted_insights(paper_id)
    elif paper_id:
        insights = manager.get_insights_by_paper(paper_id)
    elif insight_type:
        insights = manager.get_insights_by_type(insight_type)
    else:
        insights = manager.get_all_insights()

    from dataclasses import asdict
    return {"insights": [asdict(i) for i in insights]}


@router.get("/stats")
async def get_stats():
    return manager.get_statistics()


@router.post("/session/start")
async def start_session(req: StartSessionRequest):
    session_id = manager.start_reading_session(req.paper_id, req.notes)
    return {"success": True, "session_id": session_id}


@router.post("/session/end")
async def end_session():
    result = manager.end_reading_session(
        manager.current_session.id if manager.current_session else None
    )
    return {"success": True, "summary": result}
