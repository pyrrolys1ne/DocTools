"""任务接口：创建、查询、WebSocket 进度流。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from web.jobs import JobManager
from web.schemas import JobRequest, JobResponse

router = APIRouter(tags=["jobs"])

# 本地单用户场景：单例 JobManager 存内存即可，见 web/jobs.py 的 JobStore 抽象
jobs = JobManager()


@router.post("/jobs", response_model=JobResponse)
def create_job(req: JobRequest) -> JobResponse:
    """创建并启动一个批处理任务（后台线程执行，立即返回任务快照）。"""
    job = jobs.create(**req.model_dump())
    return JobResponse.from_job(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    """查询任务状态与逐文件结果。"""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"任务不存在：{job_id}")
    return JobResponse.from_job(job)


@router.websocket("/jobs/{job_id}/ws")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    """任务进度流：任务状态每次变化（进度推进或结束）时推送一次快照。"""
    await websocket.accept()
    job = jobs.get(job_id)
    if job is None:
        await websocket.close()
        return
    try:
        while True:
            # 阻塞直到任务有更新（进度推进或结束），替代固定间隔轮询
            await asyncio.to_thread(job.updated.wait)
            job.updated.clear()
            await websocket.send_json(job.to_dict())
            if job.status in ("done", "failed"):
                break
    except WebSocketDisconnect:
        pass
