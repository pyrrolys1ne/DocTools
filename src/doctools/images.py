"""图片 → PDF（基于 Pillow，纯 Python、跨平台）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from doctools.model import FileResult, ProgressFn

# 支持的图片后缀
IMAGE_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
)


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


def image_to_pdf(src: Path, dst: Path) -> None:
    """把单张图片转成 PDF（作为 process_batch 的 worker 使用）。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(str(src)) as img:
        img.convert("RGB").save(str(dst), "PDF")


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
    try:
        for done, src in enumerate(srcs, start=1):
            result = FileResult(src=src, dst=dst, ok=True)
            try:
                images.append(Image.open(str(src)))
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
