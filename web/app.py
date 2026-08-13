"""DocTools Web 后端（FastAPI）。

无头本地服务：仅提供 /api/v1 接口与 /docs 调试文档，不托管前端。
桌面客户端（C/S）与个人开发调试（浏览器 /docs）共用同一套 API。
交互模型是"目录路径"而非文件上传——后端直接按用户给出的路径读盘处理。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from web.config import API_PREFIX, cors_origin_list
from web.routers import capabilities, diagnostics, explore, jobs

app = FastAPI(title="DocTools Web", description="批量文档处理本地 API 服务")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(capabilities.router, prefix=API_PREFIX)
app.include_router(diagnostics.router, prefix=API_PREFIX)
app.include_router(explore.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)


@app.get("/api/health")
def health() -> JSONResponse:
    """健康检查（部署探测 / 运维用），返回服务信息与接口文档地址。"""
    return JSONResponse(
        {
            "status": "ok",
            "name": "DocTools API",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    )


@app.get("/")
def index() -> JSONResponse:
    """服务信息（根路径，供调试确认服务已就绪）。"""
    return JSONResponse(
        {
            "name": "DocTools API",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    )
