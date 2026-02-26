"""洞察管理 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from plugins.insights.manager import InsightsManager
from core.registry import ModuleRegistration, ModuleType, Capability, InputSchema

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


# Router 注册元数据
ROUTER_REGISTRATION = ModuleRegistration(
    name="insights_router",
    module_type=ModuleType.ROUTER,
    display_name="洞察管理 API",
    description="洞察记录、列表、统计、阅读会话",
    api_prefix="/api/insights",
    api_tags=["insights"],
    capabilities=[
        Capability(
            name="create_insight",
            description="记录阅读论文时的洞察或观察",
            input_schema=[
                InputSchema(name="content", type="str", description="洞察内容"),
                InputSchema(name="paper_id", type="str", description="来源论文 ID"),
                InputSchema(name="insight_type", type="str", description="洞察类型", required=False,
                           enum_values=["observation", "question", "connection", "surprise", "critique", "insight"]),
                InputSchema(name="importance", type="int", description="重要性 1-5", required=False),
                InputSchema(name="section", type="str", description="论文章节", required=False),
            ],
            tags=["insight", "create"],
        ),
        Capability(
            name="list_insights",
            description="列出洞察记录",
            input_schema=[
                InputSchema(name="paper_id", type="str", description="按论文筛选", required=False),
                InputSchema(name="insight_type", type="str", description="按类型筛选", required=False),
                InputSchema(name="unconverted_only", type="bool", description="只看未转化的洞察", required=False),
            ],
            tags=["insight", "list"],
        ),
        Capability(
            name="start_reading_session",
            description="开始阅读一篇论文的会话",
            input_schema=[InputSchema(name="paper_id", type="str", description="要阅读的论文 ID")],
            tags=["session", "start"],
        ),
        Capability(
            name="end_reading_session",
            description="结束当前阅读会话",
            input_schema=[InputSchema(name="notes", type="str", description="会话总结笔记", required=False)],
            tags=["session", "end"],
        ),
    ],
)


# Tool handlers — 供 chat_router 自动收集
async def _h_create_insight(tool_input):
    result = await create_insight(CreateInsightRequest(**tool_input))
    if isinstance(result, dict):
        result["display_type"] = "confirmation"
    return result

async def _h_list_insights(tool_input):
    result = await list_insights(
        paper_id=tool_input.get("paper_id"),
        insight_type=tool_input.get("insight_type"),
        unconverted_only=tool_input.get("unconverted_only", False)
    )
    if isinstance(result, dict):
        result["display_type"] = "insight_list"
    return result

async def _h_start_reading_session(tool_input):
    req = StartSessionRequest(paper_id=tool_input["paper_id"])
    result = await start_session(req)
    if isinstance(result, dict):
        result["display_type"] = "confirmation"
    return result

async def _h_end_reading_session(tool_input):
    result = await end_session()
    if isinstance(result, dict):
        result["display_type"] = "confirmation"
    return result

TOOL_HANDLERS = {
    "create_insight": _h_create_insight,
    "list_insights": _h_list_insights,
    "start_reading_session": _h_start_reading_session,
    "end_reading_session": _h_end_reading_session,
}
