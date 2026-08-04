"""图片 → PDF 测试（Pillow，跨平台）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from doctools.images import compress_image, image_to_pdf, merge_images_to_pdf


def _make_img(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (100, 80), color).save(path)


def test_image_to_pdf_single(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    _make_img(src, (200, 40, 40))
    dst = tmp_path / "a.pdf"

    image_to_pdf(src, dst)

    assert dst.exists()
    assert dst.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(str(dst)).pages) == 1


def test_merge_images_to_pdf_pages_in_order(tmp_path: Path) -> None:
    a, b = tmp_path / "a.png", tmp_path / "b.jpg"
    _make_img(a, (200, 40, 40))
    _make_img(b, (40, 120, 200))
    dst = tmp_path / "merged.pdf"

    results = merge_images_to_pdf([a, b], dst)

    assert all(r.ok for r in results)
    assert len(PdfReader(str(dst)).pages) == 2


def test_compress_image_jpeg_quality_shrinks(tmp_path: Path) -> None:
    src = tmp_path / "a.jpg"
    dst = tmp_path / "out.jpg"
    Image.new("RGB", (1200, 800), (200, 60, 60)).save(str(src), quality=95)

    compress_image(src, dst, quality=60)

    assert dst.exists()
    assert Image.open(dst).format == "JPEG"
    assert dst.stat().st_size < src.stat().st_size


def test_merge_skips_corrupt_image(tmp_path: Path) -> None:
    good, bad = tmp_path / "good.png", tmp_path / "bad.png"
    _make_img(good, (10, 10, 10))
    bad.write_bytes(b"not an image")
    dst = tmp_path / "merged.pdf"

    results = merge_images_to_pdf([bad, good], dst)

    assert results[0].ok is False
    assert results[1].ok is True
    assert len(PdfReader(str(dst)).pages) == 1
