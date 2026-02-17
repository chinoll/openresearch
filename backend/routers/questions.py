"""疑问管理 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.questions_system import QuestionsManager

router = APIRouter(prefix="/api/questions", tags=["questions"])
manager = QuestionsManager(knowledge_dir=str(Path("knowledge")))


class CreateQuestionRequest(BaseModel):
    content: str
    paper_id: str
    question_type: str = "understanding"
    importance: int = 3
    difficulty: int = 3
    section: Optional[str] = None
    context: Optional[str] = None
    tags: Optional[List[str]] = None


class AddAnswerRequest(BaseModel):
    content: str
    source: str
    section: Optional[str] = None
    page: Optional[int] = None
    quote: Optional[str] = None
    confidence: float = 0.8


class StartSessionRequest(BaseModel):
    paper_id: str


@router.post("/")
async def create_question(req: CreateQuestionRequest):
    question = manager.create_question(
        content=req.content,
        paper_id=req.paper_id,
        question_type=req.question_type,
        importance=req.importance,
        difficulty=req.difficulty,
        section=req.section,
        context=req.context,
        tags=req.tags or []
    )
    from dataclasses import asdict
    return {"success": True, "question": asdict(question)}


@router.get("/")
async def list_questions(
    paper_id: Optional[str] = None,
    status: Optional[str] = None,
    question_type: Optional[str] = None,
    min_importance: Optional[int] = None
):
    questions = manager.search_questions(
        paper_id=paper_id,
        status=status,
        question_type=question_type,
        min_importance=min_importance
    )
    from dataclasses import asdict
    return {"questions": [asdict(q) for q in questions]}


@router.get("/stats")
async def get_stats():
    return manager.get_statistics()


@router.get("/{question_id}")
async def get_question(question_id: str):
    q = manager.get_question(question_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"疑问 {question_id} 不存在")
    from dataclasses import asdict
    return asdict(q)


@router.post("/{question_id}/answers")
async def add_answer(question_id: str, req: AddAnswerRequest):
    success = manager.add_answer(
        question_id=question_id,
        content=req.content,
        source=req.source,
        section=req.section,
        page=req.page,
        quote=req.quote,
        confidence=req.confidence
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"疑问 {question_id} 不存在")
    q = manager.get_question(question_id)
    return {"success": True, "new_status": q.status}


@router.put("/{question_id}/status")
async def update_status(question_id: str, status: str):
    success = manager.update_question_status(question_id, status)
    if not success:
        raise HTTPException(status_code=404, detail=f"疑问 {question_id} 不存在")
    return {"success": True}


@router.post("/session/start")
async def start_session(req: StartSessionRequest):
    session_id = manager.start_session(req.paper_id)
    return {"success": True, "session_id": session_id}


@router.post("/session/end")
async def end_session():
    session = manager.end_session()
    if not session:
        return {"success": False, "message": "没有活动会话"}
    from dataclasses import asdict
    return {"success": True, "session": asdict(session)}
