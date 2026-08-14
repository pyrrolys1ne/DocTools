"""内存中的批处理任务管理。

本地单用户场景无需数据库：Job 存内存，处理跑在后台线程。
将来演变成线上服务时，实现同一 ``JobStore`` 协议的 Redis + 任务队列即可，
``POST /api/v1/jobs`` 的接口形状保持不变。
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from doctools.batch import FileResult, run_operation

# 任务完成后的保留时长；超期后从内存清理，避免常驻服务无限累积。
JOB_TTL_SECONDS = 3600


@dataclass
class Job:
    """一次批量处理任务的运行状态。"""

    id: str
    status: str = "pending"  # pending | running | done | failed
    total: int = 0
    done: int = 0
    current: str | None = None
    error: str | None = None
    results: list[FileResult] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    # 每次进度更新或任务结束时触发，WebSocket 据此推送，避免固定间隔轮询
    updated: threading.Event = field(default_factory=threading.Event)

    def to_dict(self) -> dict:
        """任务快照，GET 与 WebSocket 共用的响应形状。"""
        return {
            "id": self.id,
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "current": self.current,
            "error": self.error,
            "results": [
                {
                    "src": str(r.src),
                    "dst": str(r.dst),
                    "ok": r.ok,
                    "error": r.error,
                    "error_code": r.code,
                    "note": r.note,
                }
                for r in self.results
            ],
        }


class JobStore(Protocol):
    """任务存储抽象：内存版 ``JobManager``；未来可换成 Redis + 任务队列实现。"""

    def create(self, **kwargs: object) -> Job: ...

    def get(self, job_id: str) -> Job | None: ...

    def list(self) -> list[Job]: ...


class JobManager:
    """持有所有 Job 的简单字典，处理在后台线程执行。"""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def _prune(self) -> None:
        """清理已结束且超时的任务（顺带执行，不单独开后台任务）。"""
        now = time.time()
        stale = [
            jid
            for jid, job in self._jobs.items()
            if job.status in ("done", "failed") and now - job.created_at > JOB_TTL_SECONDS
        ]
        for jid in stale:
            self._jobs.pop(jid, None)

    def create(
        self,
        operation: str = "remove-headers",
        source_path: str = "",
        output_path: str = "",
        recursive: bool = False,
        output_is_dir: bool = False,
        sources: list[str] | None = None,
        page_ranges: str = "",
        quality: int = 80,
        target_format: str = "",
    ) -> Job:
        job = Job(id=uuid.uuid4().hex[:8])
        with self._lock:
            self._prune()
            self._jobs[job.id] = job
        thread = threading.Thread(
            target=self._run,
            args=(
                job,
                operation,
                source_path,
                output_path,
                recursive,
                output_is_dir,
                sources,
                page_ranges,
                quality,
                target_format,
            ),
            daemon=True,
        )
        thread.start()
        return job

    def _run(
        self,
        job: Job,
        operation: str,
        source_path: str,
        output_path: str,
        recursive: bool,
        output_is_dir: bool,
        sources: list[str] | None,
        page_ranges: str,
        quality: int,
        target_format: str,
    ) -> None:
        job.status = "running"
        # 立即给出"正在处理哪个输入"的反馈，避免单文件/慢转换期间界面毫无动静
        job.current = source_path or (sources[0] if sources else "")
        job.updated.set()

        def on_progress(total: int, done: int, result: FileResult) -> None:
            job.total = total
            job.done = done
            job.current = str(result.src)
            job.results.append(result)
            job.updated.set()

        try:
            results = run_operation(
                operation,
                source_path=source_path,
                output_path=output_path,
                recursive=recursive,
                output_is_dir=output_is_dir,
                sources=sources,
                page_ranges=page_ranges,
                quality=quality,
                target_format=target_format,
                on_progress=on_progress,
            )
        except Exception as exc:  # noqa: BLE001 - 参数校验/引擎缺失等统一上报
            job.status = "failed"
            job.error = str(exc)
            job.updated.set()
            return

        job.results = results
        job.total = len(results)
        job.done = len(results)
        job.status = "done"
        job.updated.set()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._prune()
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            self._prune()
            return list(self._jobs.values())
