"""Office → PDF 引擎选择：优先 COM，回退 LibreOffice。

优先 COM 是因为本机装有 Microsoft Office 时 fidelity 最高；未装或 COM 启动
失败时回退 LibreOffice（系统安装版或捆绑便携版），消除对本机 Office 的硬依赖。
两套后端实现同一接口：上下文管理器 + ``convert(src, dst)``。
"""

from __future__ import annotations

from typing import Any


class OfficePdfEngine:
    """Office → PDF 引擎的统一接口（上下文管理器 + 单文件 convert）。"""

    def convert(self, src: Any, dst: Any) -> None:  # pragma: no cover - 接口定义
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - 接口定义
        raise NotImplementedError

    def __enter__(self) -> OfficePdfEngine:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


def create_pdf_engine() -> OfficePdfEngine:
    """按可用性返回一个 PDF 转换引擎（COM 优先，LibreOffice 兜底）。

    两者都不可用时抛 ``OFFICE_NOT_INSTALLED``（由各自构造函数抛出）。
    """
    from doctools.office import OfficeConverter, com_available  # 惰性

    if com_available():
        try:
            return OfficeConverter()
        except Exception:  # noqa: BLE001 - COM 启动失败则回退 LibreOffice
            pass

    from doctools.libreoffice import LibreOfficePdfConverter  # 惰性

    return LibreOfficePdfConverter()
