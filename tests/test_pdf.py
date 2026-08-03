"""PDF 合并 / 拆分 / 页码范围解析测试（纯 pypdf，跨平台）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from doctools.pdf import merge_pdfs, parse_ranges, split_pdf


def _make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as f:
        writer.write(f)


def _page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


# ---------- 页码范围解析 ----------


def test_parse_ranges_basic() -> None:
    assert parse_ranges("1-3,5,8-12", 20) == [(1, 3), (5, 5), (8, 12)]


def test_parse_ranges_single_pages_and_whitespace() -> None:
    assert parse_ranges("2, 4", 10) == [(2, 2), (4, 4)]


@pytest.mark.parametrize(
    "spec,count",
    [
        ("", 5),
        ("   ", 5),
        ("0-2", 5),
        ("3-1", 5),
        ("1-99", 5),
        ("abc", 5),
        ("1-x", 5),
    ],
)
def test_parse_ranges_invalid(spec: str, count: int) -> None:
    with pytest.raises(ValueError):
        parse_ranges(spec, count)


# ---------- 合并 ----------


def test_merge_pdfs_in_order(tmp_path: Path) -> None:
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    _make_pdf(a, 2)
    _make_pdf(b, 3)
    merged = tmp_path / "merged.pdf"

    results = merge_pdfs([a, b], merged)

    assert all(r.ok for r in results)
    assert _page_count(merged) == 5


def test_merge_skips_corrupt_file(tmp_path: Path) -> None:
    good, bad = tmp_path / "good.pdf", tmp_path / "bad.pdf"
    _make_pdf(good, 1)
    bad.write_bytes(b"not a pdf")
    merged = tmp_path / "merged.pdf"

    results = merge_pdfs([bad, good], merged)

    assert results[0].ok is False
    assert results[1].ok is True
    assert merged.exists()
    assert _page_count(merged) == 1


# ---------- 拆分 ----------


def test_split_every_page(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    _make_pdf(src, 3)
    out = tmp_path / "out"

    results = split_pdf(src, out)

    assert all(r.ok for r in results)
    assert sorted(r.dst.name for r in results) == ["in_p1.pdf", "in_p2.pdf", "in_p3.pdf"]
    assert all(_page_count(r.dst) == 1 for r in results)


def test_split_by_ranges(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    _make_pdf(src, 5)
    out = tmp_path / "out"

    results = split_pdf(src, out, page_ranges="1-2,4")

    assert sorted(r.dst.name for r in results) == ["in_p1-2.pdf", "in_p4.pdf"]
    assert _page_count(out / "in_p1-2.pdf") == 2
    assert _page_count(out / "in_p4.pdf") == 1


def test_split_invalid_range_raises(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    _make_pdf(src, 3)

    with pytest.raises(ValueError):
        split_pdf(src, tmp_path / "out", page_ranges="1-9")
