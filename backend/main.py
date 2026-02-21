"""
OpenResearch FastAPI 后端

统一 API 入口，供 TUI 和 Web 界面共用。
通过 Registry 自动发现路由（扫描 backend.routers 中的 ROUTER_REGISTRATION）。
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.registry import get_registry, ModuleType

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


def _register_routers():
    """注册所有路由"""
    registry = get_registry()

    # 自动发现所有模块
    registry.auto_discover(['core', 'agents', 'backend.routers'])

    # 导入路由模块（确保 router 对象被创建 + ROUTER_REGISTRATION 被扫描）
    from backend.routers import papers, insights, questions, ideas, chat

    # 注册路由
    app.include_router(papers.router)
    app.include_router(insights.router)
    app.include_router(questions.router)
    app.include_router(ideas.router)
    app.include_router(chat.router)


_register_routers()


@app.get("/")
async def root():
    """根端点：返回 API 信息和从 registry 动态生成的端点列表"""
    registry = get_registry()
    router_regs = registry.get_all_registrations(ModuleType.ROUTER)

    endpoints = [reg.api_prefix for reg in router_regs if reg.api_prefix]
    endpoints.append("/docs")
    endpoints.sort()

    return {
        "name": "OpenResearch API",
        "version": "1.0.0",
        "registered_modules": len(registry.get_all_registrations()),
        "endpoints": endpoints
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


@app.get("/api/registry")
async def registry_info():
    """查看注册中心信息（调试用）"""
    registry = get_registry()
    all_regs = registry.get_all_registrations()

    return {
        "total_modules": len(all_regs),
        "modules": [
            {
                "name": reg.name,
                "type": reg.module_type.value,
                "display_name": reg.display_name,
                "capabilities": [cap.name for cap in reg.capabilities],
            }
            for reg in all_regs
        ],
        "capabilities_description": registry.describe_capabilities(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
