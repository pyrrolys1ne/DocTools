"""批量处理的编排层：文件发现、处理计划、逐文件执行并上报进度。

CLI 与 Web 后端都通过这里驱动批量处理，避免各自实现一遍循环逻辑。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from doctools.docx import strip_headers

DOCX_PATTERN = "*.docx"


@dataclass
class FileResult:
    """单个文件的处理结果。"""

    src: Path
    dst: Path
    ok: bool
    error: str | None = None


ProgressFn = Callable[[int, int, FileResult], None]


def discover_docx(src: Path, recursive: bool = False) -> list[Path]:
    """扫描目录下的 .docx 文件（recursive 时递归子目录），按路径排序。"""
    glob = src.rglob if recursive else src.glob
    return sorted(glob(DOCX_PATTERN))


def build_plan(
    src: Path,
    dst: Path | None = None,
    recursive: bool = False,
    output_is_dir: bool = False,
) -> list[tuple[Path, Path]]:
    """把输入（文件或目录）展开成 [(源文件, 目标文件)] 处理计划。

    - 单文件：``output_is_dir=False`` 时 ``dst`` 为完整输出文件路径；
      ``output_is_dir=True`` 时 ``dst`` 为输出目录，生成 ``dst/{stem}_cleaned.docx``。
      缺省输出为源文件旁的 ``{stem}_cleaned.docx``。
    - 目录：输出目录由 ``dst`` 决定，缺省生成 ``{dirname}_cleaned``。
      非递归时结果平铺到输出目录；递归时镜像源目录的子目录结构。
    """
    if src.is_file():
        if src.suffix.lower() != ".docx":
            raise ValueError(f"不支持的格式：{src}（仅支持 .docx）")
        if output_is_dir:
            out = (
                dst / f"{src.stem}_cleaned.docx"
                if dst is not None
                else src.with_name(f"{src.stem}_cleaned.docx")
            )
        else:
            out = dst if dst is not None else src.with_name(f"{src.stem}_cleaned.docx")
        return [(src, out)]

    if not src.is_dir():
        raise ValueError(f"路径不存在：{src}")

    out_dir = dst if dst is not None else src.with_name(f"{src.name}_cleaned")
    files = discover_docx(src, recursive)
    if not files:
        raise ValueError(f"目录中没有找到 .docx 文件：{src}")

    if recursive:
        return [(f, out_dir / f.relative_to(src)) for f in files]
    return [(f, out_dir / f.name) for f in files]


def process_batch(
    plan: list[tuple[Path, Path]],
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """按计划逐文件处理，单个文件失败不中断整批。

    每个文件完成后调用 ``on_progress(total, done, result)``。返回全部结果。
    """
    results: list[FileResult] = []
    total = len(plan)
    for done, (src, dst) in enumerate(plan, start=1):
        result = FileResult(src=src, dst=dst, ok=True)
        try:
            strip_headers(src, dst)
        except Exception as exc:  # noqa: BLE001 - 单文件失败不应中断整批
            result.ok = False
            result.error = str(exc)
        results.append(result)
        if on_progress is not None:
            on_progress(total, done, result)
    return results
