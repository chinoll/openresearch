"""想法管理 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from plugins.ideas.manager import IdeasManager
from core.registry import ModuleRegistration, ModuleType, Capability, InputSchema

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


# Router 注册元数据
ROUTER_REGISTRATION = ModuleRegistration(
    name="ideas_router",
    module_type=ModuleType.TOOL,
    display_name="想法管理 API",
    description="研究想法记录、列表、统计",
    api_prefix="/api/ideas",
    api_tags=["ideas"],
    capabilities=[
        Capability(
            name="create_idea",
            description="记录研究想法",
            input_schema=[
                InputSchema(name="title", type="str", description="想法标题"),
                InputSchema(name="content", type="str", description="想法内容"),
                InputSchema(name="paper_id", type="str", description="相关论文 ID", required=False),
                InputSchema(name="tags", type="array", description="标签", required=False),
            ],
            tags=["idea", "create"],
        ),
        Capability(
            name="list_ideas",
            description="列出研究想法",
            input_schema=[
                InputSchema(name="status", type="str", description="按状态筛选", required=False),
            ],
            tags=["idea", "list"],
        ),
    ],
)


# Tool handlers — 供 chat_router 自动收集
async def _h_create_idea(tool_input):
    result = await create_idea(CreateIdeaRequest(**tool_input))
    if isinstance(result, dict):
        result["display_type"] = "confirmation"
    return result

async def _h_list_ideas(tool_input):
    result = await list_ideas(status=tool_input.get("status"))
    if isinstance(result, dict):
        result["display_type"] = "idea_list"
    return result

TOOL_HANDLERS = {
    "create_idea": _h_create_idea,
    "list_ideas": _h_list_ideas,
}
