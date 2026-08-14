"""MinerU 在线 API 客户端测试（mock requests，不真实调用）。"""

from __future__ import annotations

import io
import json
import sys
import types
import zipfile
from pathlib import Path

import pytest

from doctools.errors import MINERU_NOT_CONFIGURED, DoctoolsError
from doctools.mineru import mineru_available, parse_pdf


def _fake_requests_module(monkeypatch: pytest.MonkeyPatch, respond_fn) -> dict:
    """安装假 requests 模块。respond_fn(calls) 返回 (content_bytes, status)。"""
    calls: dict = {}

    class FakeResp:
        def __init__(self, content: bytes, status: int):
            self.content = content
            self.status_code = status

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    class FakeRequests:
        @staticmethod
        def post(url, files=None, data=None, headers=None, json=None, timeout=None):
            calls["url"] = url
            calls["files"] = files
            calls["data"] = data
            calls["json"] = json
            content, status = respond_fn(calls)
            return FakeResp(content, status)

        @staticmethod
        def get(url, headers=None, timeout=None):
            calls["get_url"] = url
            content, status = respond_fn(calls)
            return FakeResp(content, status)

        @staticmethod
        def put(url, data=None, timeout=None):
            calls["put_url"] = url
            content, status = respond_fn(calls)
            return FakeResp(content, status)

    fake = types.ModuleType("requests")
    fake.post = FakeRequests.post
    fake.get = FakeRequests.get
    fake.put = FakeRequests.put
    monkeypatch.setitem(sys.modules, "requests", fake)
    return calls


def test_mineru_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCTOOLS_MINERU_API_URL", raising=False)

    with pytest.raises(DoctoolsError) as excinfo:
        parse_pdf(Path("a.pdf"), Path("out.md"))

    assert excinfo.value.code == MINERU_NOT_CONFIGURED


def test_mineru_available_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "http://localhost:8000")

    assert mineru_available() is True


def test_parse_pdf_self_hosted_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """自建 /file_parse：字段名 files（复数），响应 JSON 取 md_content。"""
    def respond(calls):
        assert calls["files"] is not None, "应使用 files（复数）字段名"
        body = json.dumps({"results": {"a.pdf": {"md_content": "# Title\n\ncontent"}}}).encode()
        return body, 200

    calls = _fake_requests_module(monkeypatch, respond)
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "http://localhost:8000")
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    dst = tmp_path / "out.md"

    note = parse_pdf(src, dst)

    assert calls["files"] is not None
    assert dst.exists()
    assert "# Title" in dst.read_text(encoding="utf-8")
    assert note is not None and "MinerU" in note


def test_parse_pdf_self_hosted_zip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """自建 response_format_zip=true → zip 含 full.md。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("full.md", "# From Zip\n\ncontent")

    def respond(calls):
        return buf.getvalue(), 200

    _fake_requests_module(monkeypatch, respond)
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "http://localhost:8000")
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    dst = tmp_path / "out.md"

    note = parse_pdf(src, dst)

    assert dst.exists()
    assert "# From Zip" in dst.read_text(encoding="utf-8")
    assert note is not None


def test_parse_pdf_mineru_net_requires_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DOCTOOLS_MINERU_API_URL", "https://mineru.net/api/v4")
    monkeypatch.delenv("DOCTOOLS_MINERU_TOKEN", raising=False)
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-1.4 fake")

    with pytest.raises(DoctoolsError) as excinfo:
        parse_pdf(src, tmp_path / "out.md")

    assert excinfo.value.code == MINERU_NOT_CONFIGURED
