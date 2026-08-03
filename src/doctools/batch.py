"""批量处理的编排层：文件发现、处理计划、多操作分发与逐文件执行。

CLI 与 Web 后端都通过这里驱动批量处理，避免各自实现一遍循环逻辑。
支持的操作：``remove-headers`` / ``to-pdf`` / ``merge-pdf`` / ``split-pdf``。
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from doctools.docx import strip_headers
from doctools.model import FileResult, ProgressFn  # noqa: F401  # 从 batch 重新导出

# 各类转换支持的输入后缀
WORD_SUFFIXES = (".docx", ".doc")
PPT_SUFFIXES = (".pptx", ".ppt")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")
# 兼容旧 to-pdf（Word + PPT 混合）
CONVERT_SUFFIXES = WORD_SUFFIXES + PPT_SUFFIXES

FORMAT_SUFFIXES = {
    "to-pdf": CONVERT_SUFFIXES,
    "word-to-pdf": WORD_SUFFIXES,
    "ppt-to-pdf": PPT_SUFFIXES,
    "image-to-pdf": IMAGE_SUFFIXES,
}

OPERATIONS = {
    "remove-headers",
    "to-pdf",
    "word-to-pdf",
    "ppt-to-pdf",
    "image-to-pdf",
    "merge-pdf",
    "split-pdf",
}


def discover(
    src: Path,
    recursive: bool = False,
    suffixes: tuple[str, ...] = (".docx",),
) -> list[Path]:
    """扫描目录下的文件（匹配任一后缀；recursive 时递归子目录），按路径排序。"""
    iterator = src.rglob("*") if recursive else src.glob("*")
    return sorted(f for f in iterator if f.is_file() and f.suffix.lower() in suffixes)


def discover_docx(src: Path, recursive: bool = False) -> list[Path]:
    """扫描目录下的 .docx 文件（保留向后兼容）。"""
    return discover(src, recursive, (".docx",))


def _build_plan(
    src: Path,
    dst: Path | None,
    recursive: bool,
    output_is_dir: bool,
    suffixes: tuple[str, ...],
    dir_out_name,
    file_out_name,
) -> list[tuple[Path, Path]]:
    """把输入（文件或目录）展开成 [(源文件, 目标文件)] 处理计划。

    ``dir_out_name(src)`` / ``file_out_name(src)`` 分别决定目录模式与
    单文件模式的输出文件名。
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

    out_dir = dst if dst is not None else src.with_name(f"{src.name}_cleaned")
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
    )


def build_convert_plan(
    src: Path,
    dst: Path | None = None,
    recursive: bool = False,
    output_is_dir: bool = False,
    suffixes: tuple[str, ...] = CONVERT_SUFFIXES,
) -> list[tuple[Path, Path]]:
    """转 PDF 的处理计划：指定后缀的文件 → ``{stem}.pdf``。"""
    return _build_plan(
        src, dst, recursive, output_is_dir,
        suffixes,
        dir_out_name=lambda s: f"{s.stem}.pdf",
        file_out_name=lambda s: f"{s.stem}.pdf",
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
            worker(src, dst)
        except Exception as exc:  # noqa: BLE001 - 单文件失败不应中断整批
            result.ok = False
            result.error = str(exc)
        results.append(result)
        if on_progress is not None:
            on_progress(total, done, result)
    return results


def run_operation(
    operation: str,
    *,
    source_path: str,
    output_path: str = "",
    recursive: bool = False,
    dry_run: bool = False,
    output_is_dir: bool = False,
    sources: list[str] | None = None,
    page_ranges: str = "",
    merge_images: bool = False,
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """按操作名执行并返回逐文件结果。参数校验失败抛 ``ValueError``。"""
    if operation not in OPERATIONS:
        raise ValueError(f"未知操作：{operation}")

    src = Path(source_path)
    dst = Path(output_path) if output_path else None
    srcs = [Path(p) for p in (sources or [])]

    if operation == "remove-headers":
        plan = build_plan(src, dst, recursive, output_is_dir)
        if dry_run:
            return [FileResult(s, d, ok=True) for s, d in plan]
        return process_batch(plan, on_progress=on_progress)

    if operation in ("to-pdf", "word-to-pdf", "ppt-to-pdf"):
        suffixes = FORMAT_SUFFIXES[operation]
        plan = build_convert_plan(src, dst, recursive, output_is_dir, suffixes)
        if dry_run:
            return [FileResult(s, d, ok=True) for s, d in plan]
        from doctools.office import OfficeConverter  # 惰性：pywin32 仅 Windows

        with OfficeConverter() as converter:
            return process_batch(plan, on_progress=on_progress, worker=converter.convert)

    if operation == "image-to-pdf":
        from doctools.images import IMAGE_SUFFIXES, image_to_pdf, merge_images_to_pdf

        if merge_images:
            images = (
                discover(src, recursive, IMAGE_SUFFIXES)
                if src.is_dir()
                else [src]
            )
            if not images:
                raise ValueError(f"目录中没有找到图片文件：{source_path}")
            out_dir = dst if dst is not None else src.with_name(f"{src.name}_images")
            target = out_dir / "merged.pdf"
            if dry_run:
                return [FileResult(s, target, ok=True) for s in images]
            return merge_images_to_pdf(images, target, on_progress)

        plan = build_convert_plan(src, dst, recursive, output_is_dir, IMAGE_SUFFIXES)
        if dry_run:
            return [FileResult(s, d, ok=True) for s, d in plan]
        return process_batch(plan, on_progress=on_progress, worker=image_to_pdf)

    if operation == "merge-pdf":
        if not srcs:
            raise ValueError("合并 PDF 需要至少一个源文件")
        merged = dst if dst is not None else srcs[0].with_name("merged.pdf")
        if dry_run:
            return [FileResult(s, merged, ok=True) for s in srcs]
        if dst is None:
            raise ValueError("合并 PDF 需要指定输出文件")
        from doctools.pdf import merge_pdfs  # 惰性：pypdf 纯 Python

        return merge_pdfs(srcs, dst, on_progress)

    if operation == "split-pdf":
        if not src.is_file():
            raise ValueError(f"拆分源必须是单个 PDF 文件：{source_path}")
        if src.suffix.lower() != ".pdf":
            raise ValueError("拆分源必须是 .pdf 文件")
        out_dir = dst if dst is not None else src.with_name(f"{src.stem}_split")
        from doctools.pdf import parse_ranges, split_pdf

        if dry_run:
            reader = PdfReader(str(src))
            count = len(reader.pages)
            ranges = (
                parse_ranges(page_ranges, count)
                if page_ranges.strip()
                else [(i, i) for i in range(1, count + 1)]
            )
            results = []
            for start, end in ranges:
                name = (
                    f"{src.stem}_p{start}-{end}.pdf"
                    if start != end
                    else f"{src.stem}_p{start}.pdf"
                )
                results.append(FileResult(src, out_dir / name, ok=True))
            return results
        return split_pdf(src, out_dir, page_ranges, on_progress)

    raise AssertionError(f"未处理的操作分支：{operation}")  # pragma: no cover
