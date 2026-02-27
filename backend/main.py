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

from core.config import load_app_config
from core.registry import get_registry, ModuleType, TOOL_PROVIDING_TYPES

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
    """自动发现并注册所有路由"""
    # Load unified config (config.yaml + env overrides) before router init
    load_app_config()

    registry = get_registry()

    # 自动发现所有模块（扫描 core/ 和 plugins/ 下的 REGISTRATION / ROUTER_REGISTRATION）
    registry.auto_discover(['core', 'plugins'])

    # 自动挂载所有 router
    for reg, router_obj in registry.get_router_objects():
        app.include_router(router_obj)


_register_routers()


@app.get("/")
async def root():
    """根端点：返回 API 信息和从 registry 动态生成的端点列表"""
    registry = get_registry()
    all_regs = registry.get_all_registrations()

    endpoints = [
        reg.api_prefix for reg in all_regs
        if reg.module_type in TOOL_PROVIDING_TYPES and reg.api_prefix
    ]
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
    """全局统计 — 自动收集所有插件的 get_stats"""
    registry = get_registry()
    stats = {}
    for domain, handler in registry.get_stats_handlers().items():
        stats[domain] = await handler()
    return stats


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
