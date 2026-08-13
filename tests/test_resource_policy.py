"""资源预算（resource_policy）测试。

模块常量在导入时从环境变量求值，因此每个测试先 reload 模块再断言，
保证测试之间互不影响。
"""

from __future__ import annotations

import importlib

import pytest

import doctools.resource_policy as rp
from doctools.errors import (
    IMAGE_TO_PDF_PIXEL_LIMIT,
    PDF_IMAGE_PIXEL_LIMIT,
    PDF_PAGE_LIMIT,
    DoctoolsError,
)


def _reload(monkeypatch: pytest.MonkeyPatch, **env: int) -> object:
    for name, value in env.items():
        monkeypatch.setenv(name, str(value))
    return importlib.reload(rp)


def test_pdf_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload(monkeypatch, DOCTOOLS_MAX_PDF_PAGES=5)

    with pytest.raises(DoctoolsError) as excinfo:
        mod.assert_pdf_pages(6)

    assert excinfo.value.code == PDF_PAGE_LIMIT
    mod.assert_pdf_pages(5)  # 边界内不抛


def test_pixmap_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload(monkeypatch, DOCTOOLS_PDF_IMAGE_MAX_PIXELS=1_000_000)

    with pytest.raises(DoctoolsError) as excinfo:
        mod.assert_pixmap_size(2000, 1000)  # 2MP > 1MP

    assert excinfo.value.code == PDF_IMAGE_PIXEL_LIMIT
    mod.assert_pixmap_size(1000, 1000)  # 边界内不抛


def test_image_to_pdf_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload(monkeypatch, DOCTOOLS_IMAGE_TO_PDF_MAX_PIXELS=1_000_000)

    used = mod.assert_image_to_pdf_budget(1000, 1000, used=0)  # 1MP
    assert used == 1_000_000

    with pytest.raises(DoctoolsError) as excinfo:
        mod.assert_image_to_pdf_budget(1000, 1000, used=used)  # 累计 2MP > 1MP

    assert excinfo.value.code == IMAGE_TO_PDF_PIXEL_LIMIT


def test_limits_shape_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload(monkeypatch)  # 无环境变量 → 默认值

    assert mod.LIMITS["max_pdf_pages"] == 1000
    assert mod.LIMITS["pdf_image_max_pixels"] == 50_000_000
    assert mod.LIMITS["image_to_pdf_max_pixels"] == 100_000_000


def test_invalid_env_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _reload(monkeypatch, DOCTOOLS_MAX_PDF_PAGES="not-a-number")

    assert mod.MAX_PDF_PAGES == 1000
