# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：把 web/ 后端打包成 onedir 控制台程序 docserver.exe。

桌面客户端以子进程拉起 docserver.exe（--port 0），并从 stdout 读取
``DOCSERVER_PORT=<port>`` 拿到实际端口，因此必须是 console 程序（不能
用 --windowed，否则 stdout 不可读）。
"""

import os

from PyInstaller.utils.hooks import collect_submodules

# PyInstaller 中相对路径以 spec 文件所在目录为基准，这里显式基于 SPECPATH。
spec_dir = os.path.abspath(SPECPATH)
repo_root = os.path.abspath(os.path.join(spec_dir, ".."))

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("pydantic_settings")
# doctools 引擎多为惰性导入，显式列出核心第三方库，避免漏包。
hiddenimports += [
    "fitz",
    "pdf2docx",
    "pptx",
    "PIL",
    "docx",
    "pypdf",
    "win32com",
    "win32com.client",
]

a = Analysis(
    [os.path.join(spec_dir, "docserver_entry.py")],
    pathex=[repo_root, os.path.join(repo_root, "src")],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc", "test", "tests"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="docserver",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="docserver",
)