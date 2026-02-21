"""
AI 对话 + Tool Use API

接收自然语言输入，调用 Anthropic API，AI 自动决定调用哪些工具。
"""
import os
import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any

import anthropic
from backend.tools import generate_tools_from_registry
from prompts.loader import load as load_prompt
from core.registry import ModuleRegistration, ModuleType, Capability, get_registry

router = APIRouter(prefix="/api/chat", tags=["chat"])
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = load_prompt("system/chat_assistant")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


# 工具名 → 执行函数 的静态映射（用于快速分发）
_TOOL_DISPATCH = {}


def _build_tool_dispatch():
    """构建工具分发表（延迟初始化，避免循环导入）"""
    if _TOOL_DISPATCH:
        return

    from plugins.papers.router import DownloadRequest, download_paper, list_papers, get_paper
    from plugins.insights.router import (
        CreateInsightRequest, create_insight, list_insights,
        StartSessionRequest, start_session, end_session,
        get_stats as insight_stats
    )
    from plugins.questions.router import (
        CreateQuestionRequest, create_question, list_questions,
        AddAnswerRequest, add_answer,
        get_stats as question_stats
    )
    from plugins.ideas.router import (
        CreateIdeaRequest, create_idea, list_ideas,
        get_stats as idea_stats
    )

    async def _download_paper(tool_input):
        req = DownloadRequest(arxiv_id=tool_input["arxiv_id"])
        return await download_paper(req)

    async def _list_papers(tool_input):
        return await list_papers()

    async def _get_paper_info(tool_input):
        return await get_paper(tool_input["paper_id"])

    async def _create_insight(tool_input):
        req = CreateInsightRequest(**tool_input)
        return await create_insight(req)

    async def _list_insights(tool_input):
        return await list_insights(
            paper_id=tool_input.get("paper_id"),
            insight_type=tool_input.get("insight_type"),
            unconverted_only=tool_input.get("unconverted_only", False)
        )

    async def _create_question(tool_input):
        req = CreateQuestionRequest(**tool_input)
        return await create_question(req)

    async def _list_questions(tool_input):
        return await list_questions(
            paper_id=tool_input.get("paper_id"),
            status=tool_input.get("status"),
            question_type=tool_input.get("question_type"),
            min_importance=tool_input.get("min_importance")
        )

    async def _add_answer(tool_input):
        ti = dict(tool_input)
        question_id = ti.pop("question_id")
        req = AddAnswerRequest(**ti)
        return await add_answer(question_id, req)

    async def _create_idea(tool_input):
        req = CreateIdeaRequest(**tool_input)
        return await create_idea(req)

    async def _list_ideas(tool_input):
        return await list_ideas(status=tool_input.get("status"))

    async def _start_reading_session(tool_input):
        req = StartSessionRequest(paper_id=tool_input["paper_id"])
        return await start_session(req)

    async def _end_reading_session(tool_input):
        return await end_session()

    async def _get_statistics(tool_input):
        papers = await list_papers()
        return {
            "papers": {"total": len(papers.get("papers", []))},
            "insights": await insight_stats(),
            "questions": await question_stats(),
            "ideas": await idea_stats()
        }

    _TOOL_DISPATCH.update({
        "download_paper": _download_paper,
        "list_papers": _list_papers,
        "get_paper_info": _get_paper_info,
        "create_insight": _create_insight,
        "list_insights": _list_insights,
        "create_question": _create_question,
        "list_questions": _list_questions,
        "add_answer": _add_answer,
        "create_idea": _create_idea,
        "list_ideas": _list_ideas,
        "start_reading_session": _start_reading_session,
        "end_reading_session": _end_reading_session,
        "get_statistics": _get_statistics,
    })


async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    """执行工具调用，返回结果（基于注册表动态分发）"""
    _build_tool_dispatch()

    handler = _TOOL_DISPATCH.get(tool_name)
    if handler:
        try:
            return await handler(tool_input)
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"未知工具: {tool_name}"}


@router.post("/")
async def chat(req: ChatRequest):
    """处理聊天请求，支持工具调用，流式返回"""

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    async def generate():
        # 多轮工具调用循环
        current_messages = messages.copy()

        for _ in range(5):  # 最多 5 轮工具调用
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=generate_tools_from_registry(),
                messages=current_messages
            )

            tool_calls = []
            text_content = ""

            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(block)

            # 流式发送文本
            if text_content:
                yield f"data: {json.dumps({'type': 'text', 'content': text_content})}\n\n"

            # 如果没有工具调用，结束
            if not tool_calls or response.stop_reason == "end_turn":
                break

            # 执行工具调用
            tool_results = []
            for tool_call in tool_calls:
                # 通知前端正在调用工具
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_call.name, 'input': tool_call.input})}\n\n"

                result = await execute_tool(tool_call.name, dict(tool_call.input))

                # 通知前端工具调用结果
                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_call.name, 'result': result})}\n\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            # 将工具调用和结果加入消息历史
            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# Router 注册元数据
ROUTER_REGISTRATION = ModuleRegistration(
    name="chat_router",
    module_type=ModuleType.ROUTER,
    display_name="AI 对话 API",
    description="自然语言对话，AI 自动决定调用工具",
    api_prefix="/api/chat",
    api_tags=["chat"],
    capabilities=[
        Capability(name="chat", description="AI 对话（支持工具调用和流式返回）", tags=["chat", "ai"]),
    ],
)
