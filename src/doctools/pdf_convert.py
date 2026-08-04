"""PDF → Word / PDF → PPT。

- PDF → Word：用 pdf2docx 解析文字/图片/表格重建可编辑 docx（有损，复杂排版
  与扫描件质量有限）。
- PDF → PPT：每页 PDF 渲染成高清图片，插入一张幻灯片（版式还原、文字不可编辑）。

模块顶部不导入三方库，worker 内惰性加载，避免拖慢 CLI 启动。
"""

from __future__ import annotations

from pathlib import Path

from doctools.model import FileResult, ProgressFn


def pdf_to_docx(src: Path, dst: Path) -> None:
    """把单个 PDF 转成 Word（作为 process_batch 的 worker 使用）。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    from pdf2docx import Converter  # noqa: PLC0415

    converter = Converter(str(src))
    try:
        converter.convert(str(dst))
    finally:
        converter.close()


def pdf_to_pptx(src: Path, dst: Path) -> None:
    """把单个 PDF 转成 PPT：每页渲染成图片，插入一张幻灯片（铺满整页）。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    import io  # noqa: PLC0415

    import fitz  # noqa: PLC0415  # PyMuPDF
    from pptx import Presentation  # noqa: PLC0415

    prs = Presentation()
    doc = fitz.open(str(src))
    try:
        for index, page in enumerate(doc):
            if index == 0:
                # 幻灯片尺寸取第一页大小（PDF 单位是 pt，1pt = 12700 EMU）
                prs.slide_width = int(page.rect.width * 12700)
                prs.slide_height = int(page.rect.height * 12700)
            pix = page.get_pixmap(dpi=150)
            image = io.BytesIO(pix.tobytes("png"))
            slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白版式
            slide.shapes.add_picture(image, 0, 0, width=prs.slide_width, height=prs.slide_height)
    finally:
        doc.close()
    prs.save(str(dst))


def pdf_to_images(
    src: Path,
    out_dir: Path,
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """把 PDF 的每一页渲染成一张 PNG 图片，命名 ``{stem}_p{n}.png``。"""
    import fitz  # noqa: PLC0415  # PyMuPDF

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(src))
    results: list[FileResult] = []
    try:
        total = len(doc)
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=150)
            dst = out_dir / f"{src.stem}_p{index}.png"
            pix.save(str(dst))
            result = FileResult(src=src, dst=dst, ok=True)
            results.append(result)
            if on_progress is not None:
                on_progress(total, index, result)
    finally:
        doc.close()
    return results
