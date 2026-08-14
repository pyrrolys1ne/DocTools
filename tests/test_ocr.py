"""OCR（RapidOCR）测试。

真实 OCR 依赖 RapidOCR 安装与模型下载，未安装时整模块跳过关键用例。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from doctools.errors import OCR_NOT_AVAILABLE, DoctoolsError
from doctools.ocr import ocr_available, recognize_image


def _make_text_image(path: Path) -> None:
    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 70), "Hello World 123", fill="black", font=font)
    img.save(path)


def test_ocr_not_available_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("doctools.ocr.ocr_available", lambda: False)

    with pytest.raises(DoctoolsError) as excinfo:
        recognize_image("whatever.png")

    assert excinfo.value.code == OCR_NOT_AVAILABLE


@pytest.mark.skipif(not ocr_available(), reason="RapidOCR 未安装")
def test_recognize_image_text(tmp_path: Path) -> None:
    src = tmp_path / "text.png"
    _make_text_image(src)

    text = recognize_image(str(src))

    assert "Hello" in text
