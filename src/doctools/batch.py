"""批量处理的编排层：文件发现、处理计划、多操作分发与逐文件执行。

CLI 与 Web 后端都通过这里驱动批量处理，避免各自实现一遍循环逻辑。
操作通过 ``OPERATION_HANDLERS`` 注册表分发，新增操作只需注册一个 handler。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from doctools.docx import strip_footers, strip_headers, strip_headers_footers
from doctools.errors import UNSUPPORTED_FORMAT, DoctoolsError
from doctools.model import (
    CONVERT_SUFFIXES,
    IMAGE_SUFFIXES,
    PPT_SUFFIXES,
    WORD_SUFFIXES,
    FileResult,
    ProgressFn,
)

# 各转换操作允许的输入后缀
FORMAT_SUFFIXES = {
    "to-pdf": CONVERT_SUFFIXES,
    "word-to-pdf": WORD_SUFFIXES,
    "ppt-to-pdf": PPT_SUFFIXES,
    "image-to-pdf": IMAGE_SUFFIXES,
}


def discover(
    src: Path,
    recursive: bool = False,
    suffixes: tuple[str, ...] = (".docx",),
) -> list[Path]:
    """扫描目录下的文件（匹配任一后缀；recursive 时递归子目录），按路径排序。"""
    iterator = src.rglob("*") if recursive else src.glob("*")
    return sorted(f for f in iterator if f.is_file() and f.suffix.lower() in suffixes)


def _build_plan(
    src: Path,
    dst: Path | None,
    recursive: bool,
    output_is_dir: bool,
    suffixes: tuple[str, ...],
    dir_out_name,
    file_out_name,
    default_out_dir: str,
) -> list[tuple[Path, Path]]:
    """把输入（文件或目录）展开成 [(源文件, 目标文件)] 处理计划。

    ``dir_out_name(src)`` / ``file_out_name(src)`` 分别决定目录模式与
    单文件模式的输出文件名。缺省输出目录命名为 ``{源名}_{default_out_dir}``。
    """
    if src.is_file():
        if src.suffix.lower() not in suffixes:
            raise ValueError(f"不支持的格式：{src}（仅支持 {'、'.join(suffixes)}）")
        if output_is_dir:
            name = file_out_name(src)
            out = dst / name if dst is not None else src.with_name(name)
        else:
            out = dst if dst is not None else src.with_name(file_out_name(src))
        return [(src, out)]

    if not src.is_dir():
        raise ValueError(f"路径不存在：{src}")

    out_dir = dst if dst is not None else src.with_name(f"{src.name}_{default_out_dir}")
    files = discover(src, recursive, suffixes)
    if not files:
        raise ValueError(f"目录中没有找到 {'、'.join(suffixes)} 文件：{src}")

    if recursive:
        return [(f, out_dir / f.relative_to(src).with_name(dir_out_name(f))) for f in files]
    return [(f, out_dir / dir_out_name(f)) for f in files]


def build_plan(
    src: Path,
    dst: Path | None = None,
    recursive: bool = False,
    output_is_dir: bool = False,
) -> list[tuple[Path, Path]]:
    """去页眉的处理计划：.docx → ``{stem}_cleaned.docx``。"""
    return _build_plan(
        src, dst, recursive, output_is_dir,
        (".docx",),
        dir_out_name=lambda s: s.name,
        file_out_name=lambda s: f"{s.stem}_cleaned.docx",
        default_out_dir="cleaned",
    )


def build_convert_plan(
    src: Path,
    dst: Path | None = None,
    recursive: bool = False,
    output_is_dir: bool = False,
    suffixes: tuple[str, ...] = CONVERT_SUFFIXES,
    out_suffix: str = ".pdf",
    default_out_dir: str = "pdf",
) -> list[tuple[Path, Path]]:
    """转换的处理计划：指定后缀的文件 → ``{stem}{out_suffix}``。"""
    return _build_plan(
        src, dst, recursive, output_is_dir,
        suffixes,
        dir_out_name=lambda s: f"{s.stem}{out_suffix}",
        file_out_name=lambda s: f"{s.stem}{out_suffix}",
        default_out_dir=default_out_dir,
    )


def _compress_name(s: Path) -> str:
    """压缩后的输出文件名：JPEG → ``{stem}.jpg``，其余 → ``{stem}.png``。"""
    ext = ".jpg" if s.suffix.lower() in (".jpg", ".jpeg") else ".png"
    return f"{s.stem}{ext}"


def build_compress_plan(
    src: Path,
    dst: Path | None = None,
    recursive: bool = False,
    output_is_dir: bool = False,
) -> list[tuple[Path, Path]]:
    """图片压缩的处理计划：图片 → ``{stem}.jpg`` / ``{stem}.png``。"""
    return _build_plan(
        src, dst, recursive, output_is_dir,
        IMAGE_SUFFIXES,
        dir_out_name=_compress_name,
        file_out_name=_compress_name,
        default_out_dir="compressed",
    )


def process_batch(
    plan: list[tuple[Path, Path]],
    on_progress: ProgressFn | None = None,
    worker=None,
) -> list[FileResult]:
    """按计划逐文件处理，单个文件失败不中断整批。

    每个文件完成后调用 ``on_progress(total, done, result)``。返回全部结果。
    ``worker(src, dst)`` 为单文件处理函数，默认去页眉。
    """
    if worker is None:
        worker = strip_headers
    results: list[FileResult] = []
    total = len(plan)
    for done, (src, dst) in enumerate(plan, start=1):
        result = FileResult(src=src, dst=dst, ok=True)
        try:
            note = worker(src, dst)
            if isinstance(note, str):
                result.note = note
        except DoctoolsError as exc:  # 结构化错误：记录稳定错误码
            result.ok = False
            result.error = exc.zh
            result.code = exc.code
        except Exception as exc:  # noqa: BLE001 - 单文件失败不应中断整批
            result.ok = False
            result.error = str(exc)
        results.append(result)
        if on_progress is not None:
            on_progress(total, done, result)
    return results


# ---------------------------------------------------------------------------
# 操作分发：每个操作一个 handler，签名 ``(op, params) -> list[FileResult]``。
# ---------------------------------------------------------------------------


@dataclass
class OpParams:
    """一次操作的全部参数（含解析后的 Path）。"""

    source_path: str
    output_path: str = ""
    recursive: bool = False
    output_is_dir: bool = False
    sources: list[str] | None = None
    page_ranges: str = ""
    quality: int = 80
    # 图片格式互转的目标格式（去点小写，如 "png"/"jpg"）
    target_format: str = ""
    on_progress: ProgressFn | None = None

    @property
    def src(self) -> Path:
        return Path(self.source_path)

    @property
    def dst(self) -> Path | None:
        return Path(self.output_path) if self.output_path else None

    @property
    def srcs(self) -> list[Path]:
        return [Path(p) for p in (self.sources or [])]

def _handle_remove_parts(op: str, p: OpParams) -> list[FileResult]:
    plan = build_plan(p.src, p.dst, p.recursive, p.output_is_dir)
    worker = {
        "remove-headers": strip_headers,
        "remove-footers": strip_footers,
        "remove-headers-footers": strip_headers_footers,
    }[op]
    return process_batch(plan, on_progress=p.on_progress, worker=worker)


def _handle_office_convert(op: str, p: OpParams) -> list[FileResult]:
    plan = build_convert_plan(p.src, p.dst, p.recursive, p.output_is_dir, FORMAT_SUFFIXES[op])
    from doctools.office_engine import create_pdf_engine  # 惰性：COM / LibreOffice 双后端

    with create_pdf_engine() as engine:
        return process_batch(plan, on_progress=p.on_progress, worker=engine.convert)


def _handle_pdf_to_office(op: str, p: OpParams) -> list[FileResult]:
    plan = build_convert_plan(
        p.src, p.dst, p.recursive, p.output_is_dir,
        suffixes=(".pdf",),
        out_suffix=".docx" if op == "pdf-to-word" else ".pptx",
        default_out_dir="docx" if op == "pdf-to-word" else "pptx",
    )
    from doctools.pdf_convert import pdf_to_docx, pdf_to_pptx  # 惰性

    worker = pdf_to_docx if op == "pdf-to-word" else pdf_to_pptx
    return process_batch(plan, on_progress=p.on_progress, worker=worker)


def _handle_pdf_to_images(op: str, p: OpParams) -> list[FileResult]:
    if not p.src.is_file() or p.src.suffix.lower() != ".pdf":
        raise ValueError(f"PDF 转图片的源必须是单个 .pdf 文件：{p.source_path}")
    out_dir = p.dst if p.dst is not None else p.src.with_name(f"{p.src.stem}_images")
    from doctools.pdf_convert import pdf_to_images  # 惰性

    return pdf_to_images(p.src, out_dir, p.on_progress)


def _handle_pdf_to_excel(op: str, p: OpParams) -> list[FileResult]:
    plan = build_convert_plan(
        p.src, p.dst, p.recursive, p.output_is_dir,
        suffixes=(".pdf",),
        out_suffix=".xlsx",
        default_out_dir="excel",
    )
    from doctools.pdf_excel import pdf_to_excel  # 惰性

    return process_batch(plan, on_progress=p.on_progress, worker=pdf_to_excel)


def _handle_image_to_pdf(op: str, p: OpParams) -> list[FileResult]:
    from doctools.images import merge_images_to_pdf  # 惰性

    # 图片转 PDF 只保留"多合一"：目录内所有图片（或单个图片）合成一个 PDF
    images = discover(p.src, p.recursive, IMAGE_SUFFIXES) if p.src.is_dir() else [p.src]
    if not images:
        raise ValueError(f"目录中没有找到图片文件：{p.source_path}")
    out_dir = p.dst if p.dst is not None else p.src.with_name(f"{p.src.stem}_images")
    target = out_dir / "merged.pdf"
    return merge_images_to_pdf(images, target, p.on_progress)


def _handle_compress_images(op: str, p: OpParams) -> list[FileResult]:
    plan = build_compress_plan(p.src, p.dst, p.recursive, p.output_is_dir)
    from doctools.images import compress_image  # 惰性

    worker = lambda s, d: compress_image(s, d, p.quality)  # noqa: E731
    return process_batch(plan, on_progress=p.on_progress, worker=worker)


def _handle_convert_images(op: str, p: OpParams) -> list[FileResult]:
    from doctools.images import SUPPORTED_TARGET_FORMATS, convert_image  # 惰性

    fmt = (p.target_format or "png").lower().lstrip(".")
    if fmt not in SUPPORTED_TARGET_FORMATS:
        raise DoctoolsError(
            UNSUPPORTED_FORMAT,
            f"不支持的目标图片格式：{fmt}（可选：{'、'.join(SUPPORTED_TARGET_FORMATS)}）",
            f"Unsupported target image format: {fmt}",
        )
    plan = build_convert_plan(
        p.src, p.dst, p.recursive, p.output_is_dir,
        suffixes=IMAGE_SUFFIXES,
        out_suffix=f".{fmt}",
        default_out_dir="converted",
    )
    worker = lambda s, d: convert_image(s, d, fmt)  # noqa: E731
    return process_batch(plan, on_progress=p.on_progress, worker=worker)


def _handle_merge_pdf(op: str, p: OpParams) -> list[FileResult]:
    if not p.srcs:
        raise ValueError("合并 PDF 需要至少一个源文件")
    if p.dst is None:
        raise ValueError("合并 PDF 需要指定输出文件")
    from doctools.pdf import merge_pdfs  # 惰性：pypdf 纯 Python

    return merge_pdfs(p.srcs, p.dst, p.on_progress)


def _handle_split_pdf(op: str, p: OpParams) -> list[FileResult]:
    if not p.src.is_file() or p.src.suffix.lower() != ".pdf":
        raise ValueError(f"拆分源必须是单个 PDF 文件：{p.source_path}")
    out_dir = p.dst if p.dst is not None else p.src.with_name(f"{p.src.stem}_split")
    from doctools.pdf import split_pdf  # 惰性：pypdf 纯 Python

    return split_pdf(p.src, out_dir, p.page_ranges, p.on_progress)


# 操作 → handler 注册表。新增操作只需在此登记 + 写一个 handler。
OPERATION_HANDLERS: dict[str, Callable[[str, OpParams], list[FileResult]]] = {
    "remove-headers": _handle_remove_parts,
    "remove-footers": _handle_remove_parts,
    "remove-headers-footers": _handle_remove_parts,
    "to-pdf": _handle_office_convert,
    "word-to-pdf": _handle_office_convert,
    "ppt-to-pdf": _handle_office_convert,
    "pdf-to-word": _handle_pdf_to_office,
    "pdf-to-ppt": _handle_pdf_to_office,
    "pdf-to-images": _handle_pdf_to_images,
    "pdf-to-excel": _handle_pdf_to_excel,
    "image-to-pdf": _handle_image_to_pdf,
    "compress-images": _handle_compress_images,
    "convert-images": _handle_convert_images,
    "merge-pdf": _handle_merge_pdf,
    "split-pdf": _handle_split_pdf,
}

OPERATIONS = frozenset(OPERATION_HANDLERS)


def run_operation(
    operation: str,
    *,
    source_path: str,
    output_path: str = "",
    recursive: bool = False,
    output_is_dir: bool = False,
    sources: list[str] | None = None,
    page_ranges: str = "",
    quality: int = 80,
    target_format: str = "",
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """按操作名执行并返回逐文件结果。参数校验失败抛 ``ValueError``。"""
    handler = OPERATION_HANDLERS.get(operation)
    if handler is None:
        raise ValueError(f"未知操作：{operation}")
    params = OpParams(
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
    return handler(operation, params)
