"""扫描 OCR（RapidOCR / onnxruntime）。

把扫描版 PDF 页或图片识别成文本。RapidOCR 惰性加载并缓存引擎实例，
避免每次转换重复初始化模型（模型加载约 1-2 秒）。模块顶部不导入三方库，
保持 CLI 启动轻快。
"""

from __future__ import annotations

import importlib.util
from typing import Any

from doctools.errors import OCR_FAILED, OCR_NOT_AVAILABLE, DoctoolsError

_engine: Any | None = None


def ocr_available() -> bool:
    """RapidOCR 是否可导入。"""
    try:
        return importlib.util.find_spec("rapidocr") is not None
    except (ImportError, ValueError):
        return False


def _get_engine() -> Any:
    """惰性加载并缓存 RapidOCR 引擎。"""
    global _engine
    if _engine is None:
        from rapidocr import RapidOCR  # noqa: PLC0415

        _engine = RapidOCR()
    return _engine


def recognize_image(img: Any) -> str:
    """识别一张图片（numpy 数组或文件路径），返回按识别顺序拼接的文本。

    RapidOCR 3.x 返回 ``RapidOCROutput``，取 ``.txts`` 元组按顺序拼接为多行。
    引擎不可用时抛 ``OCR_NOT_AVAILABLE``。
    """
    if not ocr_available():
        raise DoctoolsError(
            OCR_NOT_AVAILABLE,
            "OCR 引擎（RapidOCR）不可用。请安装：pip install \"doctools[ocr]\"",
            'OCR engine (RapidOCR) unavailable. Install: pip install "doctools[ocr]"',
        )
    engine = _get_engine()
    output = engine(img)
    if output is None or not output.txts:
        raise DoctoolsError(
            OCR_FAILED,
            "OCR 没有识别出文字。请确认图片清晰、文字方向正确。",
            "OCR produced no text.",
        )
    return "\n".join(str(text) for text in output.txts if text)


def ocr_pdf_page(page: Any, dpi: int = 300) -> str:
    """渲染 PDF 页为图片并 OCR，返回文本（PyMuPDF 页面对象）。"""
    import fitz  # noqa: PLC0415  # PyMuPDF
    import numpy as np  # noqa: PLC0415

    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return recognize_image(img)
