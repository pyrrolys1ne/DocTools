"""Web 后端 API 冒烟测试。

未安装 fastapi 时整模块跳过（``.[dev]`` 裸装也能跑核心测试）。
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from test_docx import _doc_with_headers  # noqa: E402

from web.app import app  # noqa: E402

client = TestClient(app)


def _wait_done(job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get(f"/api/jobs/{job_id}").json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(0.05)
    raise TimeoutError(f"任务 {job_id} 超时未完成")


def test_scan_lists_docx_recursively(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hi")
    (tmp_path / "a.docx").write_bytes(b"x")
    (tmp_path / "sub" / "b.docx").write_bytes(b"x")

    resp = client.post(
        "/api/scan", json={"source_path": str(tmp_path), "recursive": True}
    )

    assert resp.status_code == 200
    assert resp.json()["kind"] == "dir"
    names = [f["name"] for f in resp.json()["files"]]
    assert names == ["a.docx", "sub/b.docx"]


def test_drives_lists_at_least_one() -> None:
    resp = client.get("/api/drives")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["drives"], list)
    assert len(data["drives"]) >= 1
    assert isinstance(data["special"], list)


def test_drives_include_special_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """常见用户目录（桌面/文档…）应解析为可访问的物理路径。"""
    (tmp_path / "Desktop").mkdir()
    (tmp_path / "Documents").mkdir()
    monkeypatch.setattr("web.app.Path.home", staticmethod(lambda: tmp_path))

    resp = client.get("/api/drives")

    assert resp.status_code == 200
    special = resp.json()["special"]
    assert {"name": "桌面", "path": str(tmp_path / "Desktop")} in special
    assert {"name": "文档", "path": str(tmp_path / "Documents")} in special
    assert "视频" not in {s["name"] for s in special}  # 未创建的目录不列出


def test_explore_returns_parent_and_dirs(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hi")
    (tmp_path / "a.docx").write_bytes(b"x")

    resp = client.get(f"/api/explore?dir={tmp_path}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["dirs"] == ["sub"]
    assert data["files"] == ["a.docx"]
    assert data["parent"] == str(tmp_path.resolve().parent)
    assert data["error"] is None


def test_explore_hides_dollar_prefixed_dirs(tmp_path: Path) -> None:
    """以 $ 开头的系统特殊文件夹（如 $RECYCLE.BIN）不应出现在可选项里。"""
    (tmp_path / "$RECYCLE.BIN").mkdir()
    (tmp_path / "sub").mkdir()

    resp = client.get(f"/api/explore?dir={tmp_path}")

    assert resp.status_code == 200
    assert resp.json()["dirs"] == ["sub"]


def test_explore_handles_unreadable_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """权限受限的系统目录（如 $RECYCLE.BIN 子层）不应 500，而是返回提示。"""
    import pathlib

    locked = tmp_path / "locked"
    locked.mkdir()
    real_iterdir = pathlib.Path.iterdir

    def fake_iterdir(self: Path):
        if self == locked:
            raise PermissionError("denied")
        return real_iterdir(self)

    monkeypatch.setattr(pathlib.Path, "iterdir", fake_iterdir)

    resp = client.get(f"/api/explore?dir={locked}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["dirs"] == []
    assert data["files"] == []
    assert data["error"] is not None


def test_explore_404_on_missing_dir(tmp_path: Path) -> None:
    resp = client.get(f"/api/explore?dir={tmp_path / 'nope'}")
    assert resp.status_code == 404


def test_scan_404_on_missing_dir(tmp_path: Path) -> None:
    resp = client.post("/api/scan", json={"source_path": str(tmp_path / "nope")})
    assert resp.status_code == 404


def test_scan_single_file(tmp_path: Path) -> None:
    _doc_with_headers().save(str(tmp_path / "a.docx"))

    resp = client.post("/api/scan", json={"source_path": str(tmp_path / "a.docx")})

    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "file"
    assert data["files"] == [{"name": "a.docx", "size": (tmp_path / "a.docx").stat().st_size}]


def test_job_dry_run(tmp_path: Path) -> None:
    src = tmp_path / "in"
    src.mkdir()
    _doc_with_headers().save(str(src / "a.docx"))

    resp = client.post(
        "/api/jobs",
        json={
            "source_path": str(src),
            "output_path": str(tmp_path / "out"),
            "dry_run": True,
        },
    )
    job_id = resp.json()["id"]

    data = _wait_done(job_id)
    assert data["status"] == "done"
    assert data["total"] == 1
    assert data["done"] == 1
    assert not (tmp_path / "out" / "a.docx").exists()  # dry-run 不写文件


def test_job_processing(tmp_path: Path) -> None:
    src = tmp_path / "in"
    src.mkdir()
    _doc_with_headers().save(str(src / "a.docx"))

    resp = client.post(
        "/api/jobs",
        json={"source_path": str(src), "output_path": str(tmp_path / "out")},
    )
    job_id = resp.json()["id"]

    data = _wait_done(job_id)
    assert data["status"] == "done"
    assert data["results"][0]["ok"] is True
    assert (tmp_path / "out" / "a.docx").exists()


def test_job_single_file(tmp_path: Path) -> None:
    _doc_with_headers().save(str(tmp_path / "a.docx"))

    resp = client.post(
        "/api/jobs",
        json={"source_path": str(tmp_path / "a.docx")},
    )
    job_id = resp.json()["id"]

    data = _wait_done(job_id)
    assert data["status"] == "done"
    assert data["total"] == 1
    assert data["results"][0]["ok"] is True
    # 未指定输出路径时，默认生成 {stem}_cleaned.docx
    assert (tmp_path / "a_cleaned.docx").exists()


def test_job_single_file_output_is_dir(tmp_path: Path) -> None:
    _doc_with_headers().save(str(tmp_path / "a.docx"))
    out_dir = tmp_path / "out"

    resp = client.post(
        "/api/jobs",
        json={
            "source_path": str(tmp_path / "a.docx"),
            "output_path": str(out_dir),
            "output_is_dir": True,
        },
    )
    job_id = resp.json()["id"]

    data = _wait_done(job_id)
    assert data["status"] == "done"
    assert data["results"][0]["ok"] is True
    assert (out_dir / "a_cleaned.docx").exists()


def test_job_ws_streams_progress(tmp_path: Path) -> None:
    src = tmp_path / "in"
    src.mkdir()
    _doc_with_headers().save(str(src / "a.docx"))

    resp = client.post(
        "/api/jobs",
        json={"source_path": str(src), "output_path": str(tmp_path / "out")},
    )
    job_id = resp.json()["id"]

    with client.websocket_connect(f"/api/jobs/{job_id}/ws") as ws:
        data = ws.receive_json()
        assert data["id"] == job_id
        assert data["status"] in ("pending", "running", "done", "failed")
