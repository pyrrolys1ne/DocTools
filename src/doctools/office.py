"""Word / PowerPoint → PDF，基于本机 Microsoft Office 的 COM 自动化。

仅在 Windows 且安装了 Office 时可用（pywin32）。模块顶部不 import
pywin32，避免非 Windows 环境导入即失败；使用方通过 :class:`OfficeConverter`
惰性加载。对 Word 常见的 ``RPC_E_CALL_REJECTED`` 做重试，降低偶发失败。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

# 文件后缀 → 需要的 Office 应用
_APP_BY_SUFFIX = {
    ".doc": "Word",
    ".docx": "Word",
    ".ppt": "PowerPoint",
    ".pptx": "PowerPoint",
}

# Word 导出类型常量（wdExportFormatPDF）
_WD_EXPORT_PDF = 17
# PowerPoint 另存为 PDF 的格式常量（ppSaveAsPDF）
# 用 SaveAs 而非 ExportAsFixedFormat：后者在不同 PowerPoint 版本的
# typelib 签名不一致，易触发 "cannot be converted to a COM object"。
_PP_SAVE_AS_PDF = 32

# Word 在忙碌/初始化时可能拒绝调用，这两种错误值得重试
_RETRYABLE_HRESULTS = (-2147418111, -2147417848)  # RPC_E_CALL_REJECTED / CO_E_RELEASED
_MAX_RETRIES = 5


class OfficeConverter:
    """持有一个 Word / PowerPoint 实例，批量转换后统一退出。

    作为上下文管理器使用，``with`` 块结束后 Quit 全部应用并做 COM 反初始化。
    COM 需要 STA 线程初始化，构造时调用 ``pythoncom.CoInitialize()``（本类
    设计为在任务线程内创建）。
    """

    def __init__(self) -> None:
        import pythoncom  # noqa: PLC0415
        import win32com.client  # noqa: PLC0415

        self._pythoncom = pythoncom
        self._win32com = win32com.client
        self._apps: dict[str, Any] = {}
        pythoncom.CoInitialize()
        try:
            # 启动校验：确认本机装了对应用户要用的 Office 组件
            self._app("Word")
        except Exception as exc:  # noqa: BLE001 - 转为清晰的中文提示
            raise RuntimeError(
                f"未能启动 Microsoft Word。转 PDF 需要本机安装 Microsoft Office，"
                f"并安装依赖：pip install \"doctools[office]\"。\n底层错误：{exc}"
            ) from exc

    def _retry(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """对可重试的 COM 错误（Word 忙/初始化中）做有限次重试。"""
        last: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - 依据 hresult 判断是否重试
                last = exc
                hresult = getattr(exc, "hresult", None)
                if hresult not in _RETRYABLE_HRESULTS or attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(0.6 * (attempt + 1))
        raise last  # pragma: no cover - 上面的循环在最后一次尝试后必然 raise

    def _app(self, name: str) -> Any:
        if name not in self._apps:
            # 用 EnsureDispatch 生成类型库包装，避免动态分发导致
            # Word 的 Document.Close 等方法出现不可预期的 AttributeError。
            app = self._ensure_dispatch(name)
            app.DisplayAlerts = False
            if hasattr(app, "Visible"):
                try:
                    app.Visible = False
                except Exception:  # noqa: BLE001 - 个别应用不允许隐藏窗口
                    pass
            self._apps[name] = app
        return self._apps[name]

    def _ensure_dispatch(self, name: str) -> Any:
        """EnsureDispatch，并对损坏的 win32com.gen_py 缓存自愈。

        gen_py 类型库缓存若在生成中途被中断（如桌面端退出、杀进程），会残留
        半成品模块，导致 EnsureDispatch 抛 AttributeError（典型报错
        ``no attribute 'CLSIDToClassMap'``）。此时重建缓存后重试一次。
        """
        try:
            return self._retry(self._win32com.gencache.EnsureDispatch, f"{name}.Application")
        except (AttributeError, ImportError, SyntaxError):
            # gen_py 缓存损坏：清掉磁盘缓存与进程内已导入的损坏模块，
            # 下次 EnsureDispatch 会按需重建（自动重新生成 Word typelib）。
            self._repair_gen_py_cache()
            return self._retry(self._win32com.gencache.EnsureDispatch, f"{name}.Application")


    def _repair_gen_py_cache(self) -> None:
        """删除损坏的 win32com.gen_py 类型库缓存（磁盘 + 已导入模块）。

        缓存若在生成中途被中断（桌面端退出/杀进程），会残留半成品模块，
        表现为 EnsureDispatch 抛 ``no attribute 'CLSIDToClassMap'`` 等错误。
        删除后由 win32com 按需重建，避免把锅误判成“没装 Office”。
        """
        import shutil  # noqa: PLC0415
        import sys as _sys  # noqa: PLC0415

        for mod_name in [m for m in _sys.modules if m.startswith("win32com.gen_py.")]:
            _sys.modules.pop(mod_name, None)
        gen_dir = self._win32com.gencache.GetGeneratePath()
        shutil.rmtree(gen_dir, ignore_errors=True)


    def convert(self, src: Path, dst: Path) -> None:
        """把单个 Office 文件转成 PDF。``src`` 后缀决定用哪个应用。"""
        suffix = src.suffix.lower()
        app_name = _APP_BY_SUFFIX.get(suffix)
        if app_name is None:
            raise ValueError(f"不支持的 Office 格式：{src}")
        app = self._app(app_name)
        src_abs = str(src.resolve())
        dst_abs = str(dst.resolve())
        dst.parent.mkdir(parents=True, exist_ok=True)

        if app_name == "Word":
            doc = self._retry(app.Documents.Open, src_abs, ReadOnly=True)
            try:
                self._retry(doc.ExportAsFixedFormat, dst_abs, _WD_EXPORT_PDF)
            finally:
                self._retry(doc.Close, False)
        else:
            pres = self._retry(app.Presentations.Open, src_abs, ReadOnly=True, WithWindow=False)
            try:
                self._retry(pres.SaveAs, dst_abs, _PP_SAVE_AS_PDF)
            finally:
                self._retry(pres.Close)

    def close(self) -> None:
        """退出全部 Office 应用并做 COM 反初始化。重复调用安全。"""
        for name, app in list(self._apps.items()):
            try:
                app.Quit()
            except Exception:  # noqa: BLE001 - 应用可能已退出
                pass
        self._apps.clear()
        self._pythoncom.CoUninitialize()

    def __enter__(self) -> OfficeConverter:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
