"""引擎能力探测：报告各功能依赖是否可用。

参照飞鼠 ``GET /api/capabilities`` 设计：CLI / Web / 桌面端共享同一探测
函数，桌面端据此禁用不可用功能的按钮，避免用户点下去才报错。
探测保持轻量：只查模块存在性与注册表 CLSID，不启动任何进程。
"""

from __future__ import annotations

import importlib.util
import sys

try:
    import winreg  # 仅 Windows
except ImportError:  # pragma: no cover - 非 Windows 分支
    winreg = None  # type: ignore[assignment]

from doctools.resource_policy import LIMITS


def _module_available(name: str) -> bool:
    """模块是否可导入（find_spec 不执行模块代码，探测更安全）。"""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _office_com_available(app_name: str) -> bool:
    """查注册表 ``<App>.Application\\CLSID`` 是否存在，不启动 Office 进程。"""
    if sys.platform != "win32" or winreg is None:
        return False
    if not _module_available("win32com"):
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{app_name}.Application\\CLSID"):
            return True
    except OSError:
        return False


def get_capabilities() -> dict:
    """返回 ``{"engines": {...}, "limits": {...}}`` 能力清单。"""
    return {
        "engines": {
            # word-to-pdf / ppt-to-pdf：Word 或 PowerPoint 任一可用即整体可用
            "office": _office_com_available("Word") or _office_com_available("PowerPoint"),
            "pdf2docx": _module_available("pdf2docx"),
            "pymupdf": _module_available("fitz"),
            "pypdf": _module_available("pypdf"),
            "pillow": _module_available("PIL"),
            "python_docx": _module_available("docx"),
            "python_pptx": _module_available("pptx"),
        },
        "limits": LIMITS,
    }
