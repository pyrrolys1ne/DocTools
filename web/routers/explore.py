"""目录浏览相关接口：盘符、特殊文件夹、目录枚举。

交互模型是"目录路径"而非文件上传——后端直接按用户给出的路径读盘处理。
"""

from __future__ import annotations

import os
import string
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["explore"])


def _require_dir(path: str) -> Path:
    p = Path(path)
    if not p.is_dir():
        raise HTTPException(404, f"目录不存在：{path}")
    return p


def _special_folders() -> list[dict[str, str]]:
    """列出常见用户目录（桌面/文档/下载）的物理路径。

    Windows 各语言版本的物理目录名均为英文（本地化只影响资源管理器里
    的显示名），因此用 ``Path.home()`` 拼接即可得到真实可访问路径。
    """
    home = Path.home()
    result: list[dict[str, str]] = []
    for label, name in (
        ("桌面", "Desktop"),
        ("文档", "Documents"),
        ("下载", "Downloads"),
    ):
        p = home / name
        if p.is_dir():
            result.append({"name": label, "path": str(p)})
    return result


@router.get("/drives")
def drives() -> dict:
    """列出可用的盘符（Windows 的 C: D: …）与常见用户目录（桌面/文档…）。"""
    if os.name != "nt":
        return {"drives": ["/"], "special": []}
    found = [
        f"{letter}:" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")
    ]
    return {"drives": found, "special": _special_folders()}


@router.get("/explore")
def explore(dir: str = ".", exts: str = ".docx") -> dict:
    """列出目录下的子目录与匹配扩展名的文件，供前端文件夹浏览。

    对权限受限的系统目录（如 $RECYCLE.BIN 的子层）做容错：读不到的
    条目跳过、整个目录不可读时返回 ``error`` 提示，而不是 500 中断浏览。
    ``exts`` 为逗号分隔的后缀（默认 ``.docx``），如 ``.pdf`` 或 ``.docx,.pptx``。
    """
    suffix_set = {s.strip().lower() for s in exts.split(",") if s.strip()}
    p = _require_dir(dir).resolve()
    dirs: list[str] = []
    files: list[str] = []
    listing_error: str | None = None
    try:
        for entry in p.iterdir():
            try:
                if entry.is_dir():
                    dirs.append(entry.name)
                elif entry.suffix.lower() in suffix_set:
                    files.append(entry.name)
            except OSError:
                continue  # 单个条目访问失败（权限受限），跳过
    except OSError as exc:
        listing_error = f"无法读取该目录：{exc}"
    # 隐藏以 $ 开头的系统特殊文件夹（如 $RECYCLE.BIN），避免误选
    dirs = [d for d in dirs if not d.startswith("$")]
    dirs.sort()
    files.sort()
    # 盘符根目录没有上级，此时 parent 为 null
    parent = str(p.parent) if p.parent != p else None
    return {"dir": str(p), "parent": parent, "dirs": dirs, "files": files, "error": listing_error}
