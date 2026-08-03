"""共享的数据模型与类型别名（避免 batch ↔ pdf 之间循环导入）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileResult:
    """单个文件的处理结果。"""

    src: Path
    dst: Path
    ok: bool
    error: str | None = None


ProgressFn = Callable[[int, int, FileResult], None]
