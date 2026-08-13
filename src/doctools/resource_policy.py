"""资源预算：页数/像素上限，防止长文档与大图导致内存爆炸。

参照飞鼠 ``resource-policy.js`` 的预算思想，默认值对齐其文档策略：
- PDF 页数上限：``MAX_PDF_PAGES``（默认 1000）
- PDF 单页渲染像素预算：``PDF_IMAGE_MAX_PIXELS``（默认 50MP）
- 图片合并 PDF 解码预算：``IMAGE_TO_PDF_MAX_PIXELS``（默认 100MP）

所有上限可通过 ``DOCTOOLS_*`` 环境变量覆盖（非法值回退默认）。
"""

from __future__ import annotations

import os

from doctools.errors import (
    IMAGE_TO_PDF_PIXEL_LIMIT,
    PDF_IMAGE_PIXEL_LIMIT,
    PDF_PAGE_LIMIT,
    DoctoolsError,
)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(1, int(raw))
    except ValueError:  # 非法配置回退默认，不阻塞转换
        return default


MAX_PDF_PAGES = _env_int("DOCTOOLS_MAX_PDF_PAGES", 1000)
PDF_IMAGE_MAX_PIXELS = _env_int("DOCTOOLS_PDF_IMAGE_MAX_PIXELS", 50_000_000)
IMAGE_TO_PDF_MAX_PIXELS = _env_int("DOCTOOLS_IMAGE_TO_PDF_MAX_PIXELS", 100_000_000)

# 对外暴露的预算清单（随 capabilities API 下发，桌面端可展示）
LIMITS: dict[str, int] = {
    "max_pdf_pages": MAX_PDF_PAGES,
    "pdf_image_max_pixels": PDF_IMAGE_MAX_PIXELS,
    "image_to_pdf_max_pixels": IMAGE_TO_PDF_MAX_PIXELS,
}


def assert_pdf_pages(page_count: int, what: str = "PDF") -> None:
    """页数超限抛 ``PDF_PAGE_LIMIT``。``what`` 用于报错文案（如"合并结果"）。"""
    if page_count > MAX_PDF_PAGES:
        raise DoctoolsError(
            PDF_PAGE_LIMIT,
            f"{what}共 {page_count} 页，超出 {MAX_PDF_PAGES} 页的处理上限，请先拆分后再处理。",
            f"{what} has {page_count} pages, exceeding the {MAX_PDF_PAGES}-page limit. "
            "Split the PDF first.",
        )


def assert_pixmap_size(width: int, height: int) -> None:
    """单页渲染像素超限抛 ``PDF_IMAGE_PIXEL_LIMIT``。"""
    if width * height > PDF_IMAGE_MAX_PIXELS:
        raise DoctoolsError(
            PDF_IMAGE_PIXEL_LIMIT,
            f"页面渲染尺寸 {width}×{height} 超出 {PDF_IMAGE_MAX_PIXELS} 像素预算，"
            "请降低 DPI 或拆分页面后重试。",
            f"Rendered page {width}×{height} exceeds the {PDF_IMAGE_MAX_PIXELS}-pixel "
            "budget. Lower the DPI or split the page.",
        )


def assert_image_to_pdf_budget(width: int, height: int, used: int) -> int:
    """图片合并 PDF 的累计解码预算检查，返回新的累计值。

    累计超过 ``IMAGE_TO_PDF_MAX_PIXELS`` 抛 ``IMAGE_TO_PDF_PIXEL_LIMIT``。
    """
    pixels = width * height
    total = used + pixels
    if total > IMAGE_TO_PDF_MAX_PIXELS:
        raise DoctoolsError(
            IMAGE_TO_PDF_PIXEL_LIMIT,
            f"图片合计 {total} 像素，超出 {IMAGE_TO_PDF_MAX_PIXELS} 像素的合并预算，"
            "请分批合并或降低图片分辨率。",
            f"Images total {total} pixels, exceeding the {IMAGE_TO_PDF_MAX_PIXELS}-pixel "
            "merge budget. Merge in smaller batches or downscale images.",
        )
    return total
