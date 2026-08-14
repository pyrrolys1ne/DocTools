"""MinerU 在线 API 客户端测试（mock requests，不真实调用）。"""

from __future__ import annotations

import io
import sys
import types
import zipfile
from pathlib import Path

import pytest

from doctools.errors import MINERU_NOT_CONFIGURED, DoctoolsError
from doctools.mineru import mineru_available, parse_pdf


def _install_fake_requests(monkeypatch: pytest.MonkeyPatch, content: bytes, text: str = "") -> None:
    class FakeResp:
        def __init__(self) -> None:
            self.content = content
            self.text = text or content.decode("utf-8", "replace")

        def raise_for_status(self) -> None: ...

    class FakeRequests:
        @staticmethod
        def post(url: str, files=None, data=None, headers=None, timeout=None) -> FakeResp:
            return FakeResp()

    fake = types.ModuleType("requests")
    fake.post = FakeRequests.post
    monkeypatch.setitem(sys.modules, "requests", fake)


def test_mineru_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCTOOLS_MINERU_API_URL", raising=False)

    with pytest.raises(DoctoolsError) as excinfo:
        parse_pdf(Path("a.pdf"), Path("out.md"))

    assert excinfo.value.code == MINERU_NOT_CONFIGURED


def test_mineru_available_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "http://localhost:8000")

    assert mineru_available() is True


def test_parse_pdf_markdown_response(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_requests(monkeypatch, b"# Title\n\ncontent")
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "http://localhost:8000")
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    dst = tmp_path / "out.md"

    note = parse_pdf(src, dst)

    assert dst.exists()
    assert "# Title" in dst.read_text(encoding="utf-8")
    assert note is not None and "MinerU" in note


def test_parse_pdf_zip_response(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc.md", "# From Zip\n\ncontent")
    _install_fake_requests(monkeypatch, buf.getvalue())
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "http://localhost:8000")
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    dst = tmp_path / "out.md"

    note = parse_pdf(src, dst)

    assert dst.exists()
    assert "# From Zip" in dst.read_text(encoding="utf-8")
    assert note is not None
