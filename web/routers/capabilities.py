"""能力清单接口：返回可用引擎与资源预算，供桌面端禁用不可用功能。"""

from __future__ import annotations

from fastapi import APIRouter

from doctools.capabilities import get_capabilities

router = APIRouter(tags=["capabilities"])


@router.get("/capabilities")
def capabilities() -> dict:
    """返回当前可用引擎（engines）与资源预算（limits）。"""
    return get_capabilities()
