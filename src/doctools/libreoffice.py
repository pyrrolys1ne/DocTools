"""Office → PDF 的 LibreOffice 后端（headless 子进程调用）。

参照飞鼠 office-engine.js 与调研结论：
- 固定 ``-env:UserInstallation`` 为每次转换分配**隔离 profile**，避免并行争抢锁；
- subprocess 超时后 ``taskkill /T /F`` 清理残留的 soffice.bin；
- 校验输出文件存在且非空（soffice 失败也可能返回退出码 0，不轻信退出码）。

引擎探测顺序：环境变量 ``DOCTOOLS_LIBREOFFICE_PATH`` → 注册表系统安装版 →
捆绑便携版（随 docserver 分发）→ 常见安装路径。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from doctools.errors import (
    OFFICE_CONVERT_FAILED,
    OFFICE_NOT_INSTALLED,
    DoctoolsError,
)

# 单文件转换超时（秒）。复杂文档可放宽，但必须有限避免 soffice 挂起拖死服务。
_CONVERT_TIMEOUT_SECONDS = 120
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _registry_install_path() -> str | None:
    """探测系统安装的 LibreOffice（注册表 UNO InstallPath），失败返回 None。"""
    if os.name != "nt":
        return None
    try:
        import winreg  # noqa: PLC0415
    except ImportError:  # pragma: no cover - 非 Windows
        return None
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        key_paths = (
            r"SOFTWARE\LibreOffice\UNO\InstallPath",
            r"Software\LibreOffice\UNO\InstallPath",
        )
        for key_path in key_paths:
            try:
                with winreg.OpenKey(root, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, "InstallPath")
                    if value:
                        return str(value)
            except OSError:
                continue
    return None


def find_soffice() -> str | None:
    """返回 soffice 可执行文件路径，找不到返回 None。"""
    candidates: list[str] = []

    env = os.environ.get("DOCTOOLS_LIBREOFFICE_PATH")
    if env:
        candidates.append(env)

    # 捆绑便携版：优先取 PyInstaller 打包后的 resources 目录，否则取仓库 bin/
    import sys

    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(str(base / "libreoffice" / "program" / "soffice.exe"))
    else:
        repo_bin = Path(__file__).resolve().parent.parent.parent / "bin" / "libreoffice"
        candidates.append(str(repo_bin / "program" / "soffice.exe"))

    install_path = _registry_install_path()
    if install_path:
        candidates.append(str(Path(install_path) / "program" / "soffice.exe"))

    candidates += [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def soffice_available() -> bool:
    """本机是否可用 LibreOffice（系统安装版或捆绑便携版）。"""
    return find_soffice() is not None


class LibreOfficePdfConverter:
    """把 Office 文档转 PDF（作为 process_batch 的 worker 使用）。

    上下文管理器：``with`` 块内批量转换，结束后清理全部临时 profile。
    """

    def __init__(self) -> None:
        self._soffice = find_soffice()
        if self._soffice is None:
            raise DoctoolsError(
                OFFICE_NOT_INSTALLED,
                "未找到 LibreOffice。转 PDF 需要本机安装 LibreOffice，"
                "或使用内置的便携版（设置 DOCTOOLS_LIBREOFFICE_PATH 指向 soffice.exe）。",
                "LibreOffice not found. Install LibreOffice or set DOCTOOLS_LIBREOFFICE_PATH.",
            )
        self._profiles: list[Path] = []

    def convert(self, src: Path, dst: Path) -> None:
        """把单个 Office 文件转成 PDF（soffice 输出名由源 stem 决定，随后改名到 dst）。"""
        dst.parent.mkdir(parents=True, exist_ok=True)
        profile = Path(tempfile.mkdtemp(prefix="doctools-lo-profile-"))
        self._profiles.append(profile)
        cmd = [
            self._soffice,
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--nodefault",
            f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(dst.parent),
            str(src),
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW,
            )
            proc.communicate(timeout=_CONVERT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            raise DoctoolsError(
                OFFICE_CONVERT_FAILED,
                f"LibreOffice 转换超时（>{_CONVERT_TIMEOUT_SECONDS}s）：{src}",
                f"LibreOffice conversion timed out: {src}",
            ) from None

        produced = dst.parent / f"{src.stem}.pdf"
        if not produced.exists() or produced.stat().st_size == 0:
            raise DoctoolsError(
                OFFICE_CONVERT_FAILED,
                f"LibreOffice 未生成有效 PDF：{src}",
                f"LibreOffice produced no valid PDF: {src}",
            )
        if produced != dst:
            produced.replace(dst)

    def close(self) -> None:
        """清理全部临时 profile。重复调用安全。"""
        for profile in self._profiles:
            shutil.rmtree(profile, ignore_errors=True)
        self._profiles.clear()

    def __enter__(self) -> LibreOfficePdfConverter:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _kill_tree(proc: subprocess.Popen) -> None:
    """强制结束进程及其子进程（清理挂起的 soffice.bin）。"""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW,
            )
        else:
            proc.kill()
    except Exception:  # noqa: BLE001 - 清理失败不影响主流程
        pass
