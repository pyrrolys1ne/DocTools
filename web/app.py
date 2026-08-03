"""DocTools 本地 Web 后端（FastAPI）。

绑定 127.0.0.1，只服务本机。交互模型是"目录路径"而非文件上传——
后端直接按用户给出的路径读盘处理，文件不离开本机。
"""

from __future__ import annotations

import asyncio
import os
import string
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from doctools.batch import discover_docx
from web.jobs import JobManager

app = FastAPI(title="DocTools Web", description="批量文档处理本地 Web 界面")
jobs = JobManager()

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class ScanRequest(BaseModel):
    source_path: str
    recursive: bool = False


class JobRequest(BaseModel):
    source_path: str
    output_path: str = ""
    recursive: bool = False
    dry_run: bool = False
    # 单文件模式下，output_path 视为目录而非完整文件路径
    output_is_dir: bool = False


def _require_dir(path: str) -> Path:
    p = Path(path)
    if not p.is_dir():
        raise HTTPException(404, f"目录不存在：{path}")
    return p


def _job_dict(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"任务不存在：{job_id}")
    return {
        "id": job.id,
        "status": job.status,
        "total": job.total,
        "done": job.done,
        "current": job.current,
        "error": job.error,
        "results": [
            {"src": str(r.src), "dst": str(r.dst), "ok": r.ok, "error": r.error}
            for r in job.results
        ],
    }


def _special_folders() -> list[dict[str, str]]:
    """列出常见用户目录（桌面/文档/下载/图片/音乐/视频）的物理路径。

    Windows 各语言版本的物理目录名均为英文（本地化只影响资源管理器里
    的显示名），因此用 ``Path.home()`` 拼接即可得到真实可访问路径。
    """
    home = Path.home()
    result: list[dict[str, str]] = []
    for label, name in (
        ("桌面", "Desktop"),
        ("文档", "Documents"),
        ("下载", "Downloads"),
    ):
        p = home / name
        if p.is_dir():
            result.append({"name": label, "path": str(p)})
    return result


@app.get("/api/drives")
def drives() -> dict:
    """列出可用的盘符（Windows 的 C: D: …）与常见用户目录（桌面/文档…）。"""
    if os.name != "nt":
        return {"drives": ["/"], "special": []}
    found = [
        f"{letter}:" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")
    ]
    return {"drives": found, "special": _special_folders()}


@app.get("/api/explore")
def explore(dir: str = ".") -> dict:
    """列出目录下的子目录与 .docx 文件，供前端文件夹浏览。

    对权限受限的系统目录（如 $RECYCLE.BIN 的子层）做容错：读不到的
    条目跳过、整个目录不可读时返回 ``error`` 提示，而不是 500 中断浏览。
    """
    p = _require_dir(dir).resolve()
    dirs: list[str] = []
    files: list[str] = []
    listing_error: str | None = None
    try:
        for entry in p.iterdir():
            try:
                if entry.is_dir():
                    dirs.append(entry.name)
                elif entry.suffix.lower() == ".docx":
                    files.append(entry.name)
            except OSError:
                continue  # 单个条目访问失败（权限受限），跳过
    except OSError as exc:
        listing_error = f"无法读取该目录：{exc}"
    # 隐藏以 $ 开头的系统特殊文件夹（如 $RECYCLE.BIN），避免误选
    dirs = [d for d in dirs if not d.startswith("$")]
    dirs.sort()
    files.sort()
    # 盘符根目录没有上级，此时 parent 为 null
    parent = str(p.parent) if p.parent != p else None
    return {"dir": str(p), "parent": parent, "dirs": dirs, "files": files, "error": listing_error}


@app.post("/api/scan")
def scan(req: ScanRequest) -> dict:
    """预扫描，返回 .docx 清单。支持目录或单个文件作为源。"""
    p = Path(req.source_path)
    if not p.exists():
        raise HTTPException(404, f"路径不存在：{req.source_path}")
    if p.is_file():
        if p.suffix.lower() != ".docx":
            raise HTTPException(400, f"仅支持 .docx：{p}")
        return {
            "source_path": str(p.resolve()),
            "kind": "file",
            "recursive": False,
            "files": [{"name": p.name, "size": p.stat().st_size}],
        }
    files = discover_docx(p, req.recursive)
    return {
        "source_path": str(p.resolve()),
        "kind": "dir",
        "recursive": req.recursive,
        "files": [
            {"name": f.relative_to(p).as_posix(), "size": f.stat().st_size}
            for f in files
        ],
    }


@app.post("/api/jobs")
def create_job(req: JobRequest) -> dict:
    job = jobs.create(
        source_path=req.source_path,
        output_path=req.output_path,
        recursive=req.recursive,
        dry_run=req.dry_run,
        output_is_dir=req.output_is_dir,
    )
    return {"id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    return _job_dict(job_id)


@app.websocket("/api/jobs/{job_id}/ws")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    """任务进度流：任务完成前每 200ms 推一次快照。"""
    await websocket.accept()
    try:
        while True:
            job = jobs.get(job_id)
            if job is None:
                await websocket.close()
                return
            await websocket.send_json(
                {
                    "id": job.id,
                    "status": job.status,
                    "total": job.total,
                    "done": job.done,
                    "current": job.current,
                    "error": job.error,
                }
            )
            if job.status in ("done", "failed"):
                break
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass


if FRONTEND_DIST.is_dir():
    # 托管前端构建产物；API 路由已先注册，不会被静态挂载遮蔽
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/")
    def index() -> JSONResponse:
        return JSONResponse(
            {
                "name": "DocTools Web",
                "message": "前端尚未构建。请先在 frontend/ 运行 npm install && npm run build，"
                "或直接调用 /api 接口。",
                "docs": "见 ARCHITECTURE.md",
            }
        )
