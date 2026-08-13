"""引擎能力探测测试。"""

from __future__ import annotations

import pytest

from doctools.capabilities import get_capabilities

pytest.importorskip("fastapi")  # 路由测试依赖 fastapi

from fastapi.testclient import TestClient  # noqa: E402

from web.app import app  # noqa: E402


def test_capabilities_shape() -> None:
    caps = get_capabilities()

    engines = caps["engines"]
    for key in ("office", "pdf2docx", "pymupdf", "pypdf", "pillow", "python_docx", "python_pptx"):
        assert key in engines
        assert isinstance(engines[key], bool)

    limits = caps["limits"]
    assert limits["max_pdf_pages"] >= 1
    assert limits["pdf_image_max_pixels"] >= 1
    assert limits["image_to_pdf_max_pixels"] >= 1


def test_capabilities_api() -> None:
    client = TestClient(app)

    resp = client.get("/api/v1/capabilities")

    assert resp.status_code == 200
    data = resp.json()
    assert "engines" in data and "limits" in data


def test_diagnostics_api() -> None:
    client = TestClient(app)

    resp = client.get("/api/v1/diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data and data["version"]
    assert "python" in data
    assert "platform" in data
    assert "capabilities" in data and "engines" in data["capabilities"]
