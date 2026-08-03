"""PDF 合并与拆分（基于 pypdf，纯 Python、跨平台）。"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from doctools.model import FileResult, ProgressFn


def parse_ranges(spec: str, page_count: int) -> list[tuple[int, int]]:
    """把页码范围字符串解析成 1 基 (start, end) 区间列表。

    支持 ``1-3,5,8-12``；单个数字表示单页。区间必须落在 [1, page_count]，
    否则抛 ``ValueError``。每段按起始页排序，重叠/逆序视为合法但会被
    规整（仅用于定位页面，不做去重）。
    """
    if not spec.strip():
        raise ValueError("页码范围为空")
    ranges: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                start, end = int(a.strip()), int(b.strip())
            except ValueError:
                raise ValueError(f"无法解析页码范围：{part}") from None
        else:
            try:
                start = end = int(part)
            except ValueError:
                raise ValueError(f"无法解析页码范围：{part}") from None
        if not (1 <= start <= end <= page_count):
            raise ValueError(
                f"页码范围 {part} 超出文档范围（1-{page_count}）"
            )
        ranges.append((start, end))
    if not ranges:
        raise ValueError("页码范围为空")
    return ranges


def merge_pdfs(
    srcs: list[Path],
    dst: Path,
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """按传入顺序把多个 PDF 合并到 ``dst``。

    用逐页 ``add_page`` 而非 ``PdfWriter.append`` 合并：``append`` 会尝试导入
    PDF 的 outline/注释等，结构特殊的文件会在那里抛错导致整个文件被跳过
    （表现为"只合成了一个"）。逐页复制更健壮，且 ``strict=False`` 能容忍
    部分非标准 PDF。
    """
    writer = PdfWriter()
    results: list[FileResult] = []
    total = len(srcs)
    for done, src in enumerate(srcs, start=1):
        result = FileResult(src=src, dst=dst, ok=True)
        try:
            reader = PdfReader(str(src), strict=False)
            for page in reader.pages:
                writer.add_page(page)
        except Exception as exc:  # noqa: BLE001 - 单文件失败不应中断整批
            result.ok = False
            result.error = f"读取失败：{exc}"
        results.append(result)
        if on_progress is not None:
            on_progress(total, done, result)

    if any(r.ok for r in results):
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as f:
            writer.write(f)
    return results


def split_pdf(
    src: Path,
    out_dir: Path,
    page_ranges: str = "",
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """拆分 PDF。

    ``page_ranges`` 为空 → 每页一个 ``{stem}_p{n}.pdf``；
    否则按 ``1-3,5,8-12`` 区间拆分，区间命名 ``{stem}_p{a}-{b}.pdf``。
    """
    reader = PdfReader(str(src))
    page_count = len(reader.pages)

    if page_ranges.strip():
        ranges = parse_ranges(page_ranges, page_count)
    else:
        ranges = [(i, i) for i in range(1, page_count + 1)]

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[FileResult] = []
    total = len(ranges)
    for done, (start, end) in enumerate(ranges, start=1):
        name = f"{src.stem}_p{start}-{end}.pdf" if start != end else f"{src.stem}_p{start}.pdf"
        dst = out_dir / name
        writer = PdfWriter()
        for page_index in range(start - 1, end):
            writer.add_page(reader.pages[page_index])
        with dst.open("wb") as f:
            writer.write(f)
        result = FileResult(src=src, dst=dst, ok=True)
        results.append(result)
        if on_progress is not None:
            on_progress(total, done, result)
    return results
