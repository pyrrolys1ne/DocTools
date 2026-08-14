"""doctools 命令行入口。"""

from __future__ import annotations

from pathlib import Path

import typer

from doctools import __version__
from doctools.batch import FileResult, build_plan, process_batch, run_operation

app = typer.Typer(
    name="doctools",
    help="批量文档处理工具：Word 去页眉、PDF 转 PPT 等。",
    add_completion=False,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"doctools {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        help="显示版本号并退出",
    ),
) -> None:
    """DocTools 命令行入口。"""


def _report(_total: int, _done: int, result: FileResult) -> None:
    if result.ok:
        suffix = f"（{result.note}）" if result.note else ""
        typer.echo(f"[OK] {result.src} -> {result.dst}{suffix}")
    else:
        code = f"[{result.code}] " if result.code else ""
        typer.echo(f"[FAIL] 处理失败 {result.src}: {code}{result.error}", err=True)


@app.command("remove-headers")
def remove_headers_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 .docx 文件或包含 .docx 的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成 *_cleaned 结果",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的 .docx，输出目录镜像源目录结构",
    ),
) -> None:
    """批量去除 Word（.docx）文档的页眉。"""
    try:
        pairs = build_plan(input_path, output, recursive)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    results = process_batch(pairs, on_progress=_report)
    if any(not r.ok for r in results):
        raise typer.Exit(1)


@app.command("remove-footers")
def remove_footers_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 .docx 文件或包含 .docx 的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成 *_cleaned 结果",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的 .docx，输出目录镜像源目录结构",
    ),
) -> None:
    """批量去除 Word（.docx）文档的页脚。"""
    _run_operation_report(
        "remove-footers",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("remove-headers-footers")
def remove_headers_footers_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 .docx 文件或包含 .docx 的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成 *_cleaned 结果",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的 .docx，输出目录镜像源目录结构",
    ),
) -> None:
    """批量同时去除 Word（.docx）文档的页眉与页脚。"""
    _run_operation_report(
        "remove-headers-footers",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


def _run_operation_report(operation: str, **kwargs) -> None:
    """执行 run_operation 并逐条上报、按失败结果设置退出码。"""
    try:
        results = run_operation(operation, on_progress=_report, **kwargs)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if any(not r.ok for r in results):
        raise typer.Exit(1)


@app.command("to-pdf")
def to_pdf_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 Office 文件（.docx/.doc/.pptx/.ppt）或包含它们的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成同名 .pdf",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的文件，输出目录镜像源目录结构",
    ),
) -> None:
    """（已弃用）混合转换：改用 word-to-pdf / ppt-to-pdf。保留兼容，勿用于新脚本。"""
    _run_operation_report(
        "to-pdf",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("word-to-pdf")
def word_to_pdf_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 Word 文件（.docx/.doc）或包含它们的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成同名 .pdf",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的文件，输出目录镜像源目录结构",
    ),
) -> None:
    """把 Word 文档转换为 PDF（需要本机安装 Microsoft Office）。"""
    _run_operation_report(
        "word-to-pdf",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("ppt-to-pdf")
def ppt_to_pdf_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 PowerPoint 文件（.pptx/.ppt）或包含它们的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成同名 .pdf",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的文件，输出目录镜像源目录结构",
    ),
) -> None:
    """把 PowerPoint 演示文稿转换为 PDF（需要本机安装 Microsoft Office）。"""
    _run_operation_report(
        "ppt-to-pdf",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("image-to-pdf")
def image_to_pdf_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的图片文件（.png/.jpg/...）或包含它们的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="输出目录。默认在源路径旁生成 {stem}_images/merged.pdf",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的图片，输出目录镜像源目录结构",
    ),
) -> None:
    """把图片转换为 PDF（目录内所有图片合成一个，每张一页）。"""
    _run_operation_report(
        "image-to-pdf",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("compress-images")
def compress_images_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的图片文件或包含图片的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="输出目录。默认在源路径旁生成 {目录名}_compressed",
    ),
    quality: int = typer.Option(
        80, "--quality", "-q", min=1, max=100, help="JPEG 重编码质量（1-100，默认 80）"
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的图片，输出目录镜像源目录结构",
    ),
) -> None:
    """压缩图片（JPEG 按质量重编码，其余转优化 PNG）。"""
    _run_operation_report(
        "compress-images",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
        quality=quality,
    )


@app.command("convert-images")
def convert_images_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的图片文件或包含图片的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="输出目录。默认在源路径旁生成 {目录名}_converted",
    ),
    to: str = typer.Option(
        "png", "--to", help="目标格式（png/jpg/webp/bmp/gif/tiff，默认 png）"
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的图片，输出目录镜像源目录结构",
    ),
) -> None:
    """图片格式互转（Pillow，支持 png/jpg/webp/bmp/gif/tiff）。"""
    _run_operation_report(
        "convert-images",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
        target_format=to,
    )


@app.command("pdf-to-word")
def pdf_to_word_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 PDF 文件或包含 .pdf 的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成同名 .docx",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的 .pdf，输出目录镜像源目录结构",
    ),
) -> None:
    """把 PDF 转换为 Word（有损：复杂排版/扫描件质量有限）。"""
    _run_operation_report(
        "pdf-to-word",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("pdf-to-ppt")
def pdf_to_ppt_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="输入的 PDF 文件或包含 .pdf 的目录",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="单文件时指定输出文件路径；目录时指定输出目录。默认在源路径旁生成同名 .pptx",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="递归处理子目录中的 .pdf，输出目录镜像源目录结构",
    ),
) -> None:
    """把 PDF 转换为 PPT（每页渲染成一张幻灯片）。"""
    _run_operation_report(
        "pdf-to-ppt",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        recursive=recursive,
    )


@app.command("pdf-to-images")
def pdf_to_images_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="要转图片的 PDF 文件",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出目录。默认在源路径旁生成 {stem}_images"
    ),
) -> None:
    """把 PDF 的每一页转成一张 PNG 图片。"""
    _run_operation_report(
        "pdf-to-images",
        source_path=str(input_path),
        output_path=str(output) if output else "",
    )


@app.command("merge-pdf")
def merge_pdf_cmd(
    files: list[Path] = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="要合并的 PDF 文件（按命令行顺序合并）",
    ),
    output: Path = typer.Option(
        ..., "--output", "-o", help="合并后的输出 PDF 文件路径"
    ),
) -> None:
    """把多个 PDF 按顺序合并为一个。"""
    _run_operation_report(
        "merge-pdf",
        source_path="",
        output_path=str(output),
        sources=[str(f) for f in files],
    )


@app.command("split-pdf")
def split_pdf_cmd(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="要拆分的 PDF 文件",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出目录。默认在源路径旁生成 {stem}_split"
    ),
    ranges: str = typer.Option(
        "", "--ranges", help='页码范围，如 "1-3,5,8-12"；留空则每页一个文件'
    ),
) -> None:
    """把 PDF 拆分成多个文件（每页一个，或按页码范围）。"""
    _run_operation_report(
        "split-pdf",
        source_path=str(input_path),
        output_path=str(output) if output else "",
        page_ranges=ranges,
    )
