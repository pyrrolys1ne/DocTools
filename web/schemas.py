"""API 请求 / 响应模型（Pydantic v2）。

前后端契约统一在此定义；``JobResponse`` 从 ``Job.to_dict()`` 构建，
路由层不手拼响应 dict。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from web.jobs import Job

JobStatus = Literal["pending", "running", "done", "failed"]


class JobRequest(BaseModel):
    """创建任务的请求体。"""

    operation: str = "remove-headers"
    source_path: str = ""
    output_path: str = ""
    recursive: bool = False
    # 单文件模式下，output_path 视为目录而非完整文件路径
    output_is_dir: bool = False
    # 合并 PDF：多选源文件（按顺序合并）
    sources: list[str] = Field(default_factory=list)
    # 拆分 PDF：自定义页码范围（如 "1-3,5,8-12"；留空则每页一个）
    page_ranges: str = ""
    # 图片压缩：JPEG 重编码质量（1-100）
    quality: int = 80


class JobResult(BaseModel):
    """单个文件的处理结果。"""

    src: str
    dst: str
    ok: bool
    error: str | None = None
    # 稳定错误码（见 doctools.errors）；失败时可能为 None（非结构化异常）
    error_code: str | None = None
    # 附注（如"已回退为文字提取"）
    note: str | None = None


class JobResponse(BaseModel):
    """任务状态快照（GET 与 WebSocket 推送共用同一结构）。"""

    id: str
    status: JobStatus
    total: int
    done: int
    current: str | None = None
    error: str | None = None
    results: list[JobResult] = Field(default_factory=list)

    @classmethod
    def from_job(cls, job: Job) -> JobResponse:
        return cls.model_validate(job.to_dict())
