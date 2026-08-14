"""图片 → PDF / 图片格式互转测试（Pillow，跨平台）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from doctools.errors import UNSUPPORTED_FORMAT, DoctoolsError
from doctools.images import compress_image, convert_image, merge_images_to_pdf


def _make_img(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (100, 80), color).save(path)


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


def test_convert_image_png_to_jpeg(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    dst = tmp_path / "out.jpg"
    Image.new("RGBA", (60, 40), (200, 60, 60, 128)).save(src)  # 带透明通道

    convert_image(src, dst, "jpg")

    assert dst.exists()
    img = Image.open(dst)
    assert img.format == "JPEG"
    assert img.mode == "RGB"  # JPEG 无透明通道，已转 RGB


def test_convert_image_png_to_webp(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    dst = tmp_path / "out.webp"
    _make_img(src, (10, 120, 10))

    convert_image(src, dst, "webp")

    assert dst.exists()
    assert Image.open(dst).format == "WEBP"


def test_convert_images_operation_unsupported_format(tmp_path: Path) -> None:
    from doctools.batch import run_operation

    src = tmp_path / "a.png"
    _make_img(src, (10, 10, 10))

    with pytest.raises(DoctoolsError) as excinfo:
        run_operation(
            "convert-images",
            source_path=str(src),
            output_path=str(tmp_path),
            target_format="heic",
        )

    assert excinfo.value.code == UNSUPPORTED_FORMAT


def test_image_to_pdf_queue_order(tmp_path: Path) -> None:
    """队列模式：按 sources 显式顺序合成 PDF。"""
    from doctools.batch import run_operation

    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _make_img(a, (200, 40, 40))
    _make_img(b, (40, 120, 200))
    out = tmp_path / "merged.pdf"

    results = run_operation(
        "image-to-pdf",
        source_path="",
        output_path=str(out),
        sources=[str(b), str(a)],  # 显式顺序：b 在前
    )

    assert all(r.ok for r in results)
    assert [Path(r.src).name for r in results] == ["b.png", "a.png"]
    assert len(PdfReader(str(out)).pages) == 2
