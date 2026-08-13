"""诊断接口：一键导出诊断报告所需的全部信息。

参照飞鼠的"导出诊断报告"设计：桌面端一个按钮拿到版本、平台、能力清单
与相关环境变量，用于远程排查"用户机器上转换失败"类问题。
"""

from __future__ import annotations

import os
import platform
import sys
import time

from fastapi import APIRouter

from doctools import __version__
from doctools.capabilities import get_capabilities

router = APIRouter(tags=["diagnostics"])

# 服务启动时间（模块加载时），供"运行时长"使用
_STARTED_AT = time.time()


@router.get("/diagnostics")
def diagnostics() -> dict:
    """返回版本、平台、引擎能力、资源预算与 DOCTOOLS_* 环境变量。"""
    env = {k: v for k, v in os.environ.items() if k.startswith("DOCTOOLS_")}
    return {
        "name": "DocTools API",
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        "capabilities": get_capabilities(),
        "env": env,
    }
