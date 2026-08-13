"""共享的数据模型、类型别名与领域常量（避免模块间循环导入）。"""

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
    # 稳定错误码（见 doctools.errors）；失败时可能为 None（非结构化异常）
    code: str | None = None
    # 附注（如"已回退为文字提取"），成功/失败均可携带
    note: str | None = None


ProgressFn = Callable[[int, int, FileResult], None]

# 各类转换支持的输入后缀
WORD_SUFFIXES = (".docx", ".doc")
PPT_SUFFIXES = (".pptx", ".ppt")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")
# 兼容旧 to-pdf（Word + PPT 混合）
CONVERT_SUFFIXES = WORD_SUFFIXES + PPT_SUFFIXES
