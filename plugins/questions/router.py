"""疑问管理 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from plugins.questions.manager import QuestionsManager
from core.registry import ModuleRegistration, ModuleType, Capability, InputSchema

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


# Router 注册元数据
ROUTER_REGISTRATION = ModuleRegistration(
    name="questions_router",
    module_type=ModuleType.ROUTER,
    display_name="疑问管理 API",
    description="疑问记录、答案、状态追踪、会话",
    api_prefix="/api/questions",
    api_tags=["questions"],
    capabilities=[
        Capability(
            name="create_question",
            description="记录阅读论文时产生的疑问",
            input_schema=[
                InputSchema(name="content", type="str", description="疑问内容"),
                InputSchema(name="paper_id", type="str", description="来源论文 ID"),
                InputSchema(name="question_type", type="str", description="疑问类型", required=False,
                           enum_values=["understanding", "method", "experiment", "application",
                                       "limitation", "extension", "comparison", "implementation"]),
                InputSchema(name="importance", type="int", description="重要性 1-5", required=False),
                InputSchema(name="section", type="str", description="论文章节", required=False),
                InputSchema(name="context", type="str", description="疑问上下文", required=False),
            ],
            tags=["question", "create"],
        ),
        Capability(
            name="list_questions",
            description="列出疑问记录",
            input_schema=[
                InputSchema(name="paper_id", type="str", description="按论文筛选", required=False),
                InputSchema(name="status", type="str", description="按状态筛选", required=False,
                           enum_values=["unsolved", "partial", "solved"]),
                InputSchema(name="question_type", type="str", description="按类型筛选", required=False),
                InputSchema(name="min_importance", type="int", description="最低重要性", required=False),
            ],
            tags=["question", "list"],
        ),
        Capability(
            name="add_answer",
            description="为疑问添加答案",
            input_schema=[
                InputSchema(name="question_id", type="str", description="疑问 ID"),
                InputSchema(name="content", type="str", description="答案内容"),
                InputSchema(name="source", type="str", description="答案来源"),
                InputSchema(name="section", type="str", description="论文章节", required=False),
                InputSchema(name="quote", type="str", description="相关引用", required=False),
                InputSchema(name="confidence", type="float", description="置信度 0-1", required=False),
            ],
            tags=["question", "answer"],
        ),
    ],
)


# Tool handlers — 供 chat_router 自动收集
async def _h_create_question(tool_input):
    result = await create_question(CreateQuestionRequest(**tool_input))
    if isinstance(result, dict):
        result["display_type"] = "confirmation"
    return result

async def _h_list_questions(tool_input):
    result = await list_questions(
        paper_id=tool_input.get("paper_id"),
        status=tool_input.get("status"),
        question_type=tool_input.get("question_type"),
        min_importance=tool_input.get("min_importance")
    )
    if isinstance(result, dict):
        result["display_type"] = "question_list"
    return result

async def _h_add_answer(tool_input):
    ti = dict(tool_input)
    question_id = ti.pop("question_id")
    req = AddAnswerRequest(**ti)
    result = await add_answer(question_id, req)
    if isinstance(result, dict):
        result["display_type"] = "confirmation"
    return result

TOOL_HANDLERS = {
    "create_question": _h_create_question,
    "list_questions": _h_list_questions,
    "add_answer": _h_add_answer,
}
