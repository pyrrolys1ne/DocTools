"""内存中的批处理任务管理。

本地单用户场景无需数据库：Job 存内存，处理跑在后台线程。
将来演变成线上服务时，把 JobManager 换成 Redis + 任务队列即可，
``POST /api/jobs`` 的接口形状保持不变。
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from doctools.batch import FileResult, run_operation


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


class JobManager:
    """持有所有 Job 的简单字典，处理在后台线程执行。"""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(
        self,
        operation: str = "remove-headers",
        source_path: str = "",
        output_path: str = "",
        recursive: bool = False,
        dry_run: bool = False,
        output_is_dir: bool = False,
        sources: list[str] | None = None,
        page_ranges: str = "",
        merge_images: bool = False,
    ) -> Job:
        job = Job(id=uuid.uuid4().hex[:8])
        with self._lock:
            self._jobs[job.id] = job
        thread = threading.Thread(
            target=self._run,
            args=(
                job,
                operation,
                source_path,
                output_path,
                recursive,
                dry_run,
                output_is_dir,
                sources,
                page_ranges,
                merge_images,
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
        dry_run: bool,
        output_is_dir: bool,
        sources: list[str] | None,
        page_ranges: str,
        merge_images: bool,
    ) -> None:
        job.status = "running"

        def on_progress(total: int, done: int, result: FileResult) -> None:
            job.total = total
            job.done = done
            job.current = str(result.src)
            job.results.append(result)

        try:
            results = run_operation(
                operation,
                source_path=source_path,
                output_path=output_path,
                recursive=recursive,
                dry_run=dry_run,
                output_is_dir=output_is_dir,
                sources=sources,
                page_ranges=page_ranges,
                merge_images=merge_images,
                on_progress=on_progress,
            )
        except Exception as exc:  # noqa: BLE001 - 参数校验/引擎缺失等统一上报
            job.status = "failed"
            job.error = str(exc)
            return

        job.results = results
        job.total = len(results)
        job.done = len(results)
        job.status = "done"

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return list(self._jobs.values())
