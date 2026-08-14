"""图片处理：压缩、格式互转、图片 → PDF（基于 Pillow，纯 Python、跨平台）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from doctools.errors import DoctoolsError
from doctools.model import FileResult, ProgressFn
from doctools.resource_policy import assert_image_to_pdf_budget

# 图片格式互转支持的目标格式（Pillow 原生可写）
# 键为 CLI/API 使用的格式名（去点小写），值为 Pillow 保存格式名。
SUPPORTED_TARGET_FORMATS: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "tiff": "TIFF",
}


def compress_image(src: Path, dst: Path, quality: int = 80) -> None:
    """压缩单张图片（作为 process_batch 的 worker 使用）。

    JPEG 按给定质量重编码；其余格式转成 optimize 的 PNG。输出文件名由
    dst 后缀决定（``_compress_name`` 保证 .jpg/.png 与内容一致）。
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(str(src)) as img:
        img.load()
        if dst.suffix.lower() == ".jpg":
            img.convert("RGB").save(str(dst), "JPEG", quality=quality, optimize=True)
        else:
            img.save(str(dst), "PNG", optimize=True)


def convert_image(src: Path, dst: Path, fmt: str) -> None:
    """把单张图片转成 ``fmt`` 指定格式（作为 process_batch 的 worker 使用）。

    ``fmt`` 须是 :data:`SUPPORTED_TARGET_FORMATS` 的键（如 "png"/"jpg"/"webp"）。
    转 JPEG 时统一转 RGB（JPEG 不支持透明通道），其余格式保留原色彩模式。
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    save_format = SUPPORTED_TARGET_FORMATS[fmt]
    with Image.open(str(src)) as img:
        img.load()
        if fmt in ("jpg", "jpeg"):
            img = img.convert("RGB")
        img.save(str(dst), format=save_format)


def merge_images_to_pdf(
    srcs: list[Path],
    dst: Path,
    on_progress: ProgressFn | None = None,
) -> list[FileResult]:
    """按顺序把多张图片合并成一个 PDF（每张图片一页）。

    单张读取失败不中断整体；只要至少有一张成功就写出结果。
    """
    results: list[FileResult] = []
    images: list[Image.Image] = []
    total = len(srcs)
    used_pixels = 0
    try:
        for done, src in enumerate(srcs, start=1):
            result = FileResult(src=src, dst=dst, ok=True)
            try:
                img = Image.open(str(src))
                # 累计解码预算：超限整个操作失败（fail closed，参照飞鼠）
                used_pixels = assert_image_to_pdf_budget(img.width, img.height, used_pixels)
                images.append(img)
            except DoctoolsError:
                for img in images:
                    img.close()
                raise
            except Exception as exc:  # noqa: BLE001 - 单张失败不应中断整批
                result.ok = False
                result.error = str(exc)
            results.append(result)
            if on_progress is not None:
                on_progress(total, done, result)

        if images:
            dst.parent.mkdir(parents=True, exist_ok=True)
            first = images[0].convert("RGB")
            rest = [img.convert("RGB") for img in images[1:]]
            first.save(str(dst), "PDF", save_all=True, append_images=rest)
    finally:
        for img in images:
            img.close()
    return results
