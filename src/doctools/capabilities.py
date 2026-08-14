"""引擎能力探测：报告各功能依赖是否可用。

参照飞鼠 ``GET /api/capabilities`` 设计：CLI / Web / 桌面端共享同一探测
函数，桌面端据此禁用不可用功能的按钮，避免用户点下去才报错。
探测保持轻量：只查模块存在性、注册表 CLSID 与文件存在性，不启动任何进程。
"""

from __future__ import annotations

import importlib.util

from doctools.libreoffice import soffice_available
from doctools.ocr import ocr_available
from doctools.office import com_available
from doctools.resource_policy import LIMITS


def _module_available(name: str) -> bool:
    """模块是否可导入（find_spec 不执行模块代码，探测更安全）。"""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def get_capabilities() -> dict:
    """返回 ``{"engines": {...}, "limits": {...}}`` 能力清单。"""
    office_com = com_available()
    office_libreoffice = soffice_available()
    return {
        "engines": {
            # word-to-pdf / ppt-to-pdf：COM 或 LibreOffice 任一可用即整体可用
            "office": office_com or office_libreoffice,
            "office_com": office_com,
            "office_libreoffice": office_libreoffice,
            "pdf2docx": _module_available("pdf2docx"),
            "pymupdf": _module_available("fitz"),
            "pypdf": _module_available("pypdf"),
            "pillow": _module_available("PIL"),
            "python_docx": _module_available("docx"),
            "python_pptx": _module_available("pptx"),
            "ocr": ocr_available(),
        },
        "limits": LIMITS,
    }
