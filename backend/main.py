"""
OpenResearch FastAPI 后端

统一 API 入口，供 TUI 和 Web 界面共用。
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.routers import papers, insights, questions, ideas, chat

app = FastAPI(
    title="OpenResearch API",
    description="深度研究系统后端 API",
    version="1.0.0"
)

# 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(papers.router)
app.include_router(insights.router)
app.include_router(questions.router)
app.include_router(ideas.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "name": "OpenResearch API",
        "version": "1.0.0",
        "endpoints": [
            "/api/papers",
            "/api/insights",
            "/api/questions",
            "/api/ideas",
            "/api/chat",
            "/docs"  # Swagger UI
        ]
    }


@app.get("/api/stats")
async def global_stats():
    """全局统计"""
    from backend.routers.papers import list_papers
    from backend.routers.insights import get_stats as i_stats
    from backend.routers.questions import get_stats as q_stats
    from backend.routers.ideas import get_stats as id_stats

    papers_data = await list_papers()
    return {
        "papers": {"total": len(papers_data.get("papers", []))},
        "insights": await i_stats(),
        "questions": await q_stats(),
        "ideas": await id_stats()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
