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

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import anthropic
from backend.tools import TOOLS

router = APIRouter(prefix="/api/chat", tags=["chat"])
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """你是 OpenResearch 的 AI 助手，帮助用户管理学术论文研究过程。

你可以通过工具来：
- 下载和查询论文
- 记录阅读洞察
- 管理研究疑问
- 记录研究想法
- 管理阅读会话

请用中文回复，保持简洁。调用工具后，给出简短的确认和说明。
如果用户的请求不清晰，先进行澄清再调用工具。"""


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    """执行工具调用，返回结果"""
    # 动态导入以避免循环依赖
    from backend.routers import papers as papers_router
    from backend.routers import insights as insights_router
    from backend.routers import questions as questions_router
    from backend.routers import ideas as ideas_router
    from pydantic import BaseModel

    try:
        if tool_name == "download_paper":
            from backend.routers.papers import DownloadRequest, download_paper
            req = DownloadRequest(arxiv_id=tool_input["arxiv_id"])
            return await download_paper(req)

        elif tool_name == "list_papers":
            from backend.routers.papers import list_papers
            return await list_papers()

        elif tool_name == "get_paper_info":
            from backend.routers.papers import get_paper
            return await get_paper(tool_input["paper_id"])

        elif tool_name == "create_insight":
            from backend.routers.insights import CreateInsightRequest, create_insight
            req = CreateInsightRequest(**tool_input)
            return await create_insight(req)

        elif tool_name == "list_insights":
            from backend.routers.insights import list_insights
            return await list_insights(
                paper_id=tool_input.get("paper_id"),
                insight_type=tool_input.get("insight_type"),
                unconverted_only=tool_input.get("unconverted_only", False)
            )

        elif tool_name == "create_question":
            from backend.routers.questions import CreateQuestionRequest, create_question
            req = CreateQuestionRequest(**tool_input)
            return await create_question(req)

        elif tool_name == "list_questions":
            from backend.routers.questions import list_questions
            return await list_questions(
                paper_id=tool_input.get("paper_id"),
                status=tool_input.get("status"),
                question_type=tool_input.get("question_type"),
                min_importance=tool_input.get("min_importance")
            )

        elif tool_name == "add_answer":
            from backend.routers.questions import AddAnswerRequest, add_answer
            question_id = tool_input.pop("question_id")
            req = AddAnswerRequest(**tool_input)
            return await add_answer(question_id, req)

        elif tool_name == "create_idea":
            from backend.routers.ideas import CreateIdeaRequest, create_idea
            req = CreateIdeaRequest(**tool_input)
            return await create_idea(req)

        elif tool_name == "list_ideas":
            from backend.routers.ideas import list_ideas
            return await list_ideas(status=tool_input.get("status"))

        elif tool_name == "start_reading_session":
            from backend.routers.insights import StartSessionRequest, start_session
            req = StartSessionRequest(paper_id=tool_input["paper_id"])
            return await start_session(req)

        elif tool_name == "end_reading_session":
            from backend.routers.insights import end_session
            return await end_session()

        elif tool_name == "get_statistics":
            from backend.routers.insights import get_stats as insight_stats
            from backend.routers.questions import get_stats as question_stats
            from backend.routers.ideas import get_stats as idea_stats
            from backend.routers.papers import list_papers
            papers = await list_papers()
            return {
                "papers": {"total": len(papers.get("papers", []))},
                "insights": await insight_stats(),
                "questions": await question_stats(),
                "ideas": await idea_stats()
            }

        else:
            return {"error": f"未知工具: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


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
                tools=TOOLS,
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
