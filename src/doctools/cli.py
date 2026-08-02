"""doctools 命令行入口。"""

from __future__ import annotations

from pathlib import Path

import typer

from doctools import __version__
from doctools.batch import FileResult, build_plan, process_batch

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
        typer.echo(f"[OK] {result.src} -> {result.dst}")
    else:
        typer.echo(f"[FAIL] 处理失败 {result.src}: {result.error}", err=True)


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
        help="单文件时指定输出文件路径；目录时指定输出目录。默认自动生成 *_cleaned 结果",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="只打印将要执行的操作，不写入文件"
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

    if dry_run:
        for src, dst in pairs:
            typer.echo(f"[dry-run] 将处理 {src} -> {dst}")
        return

    results = process_batch(pairs, on_progress=_report)
    if any(not r.ok for r in results):
        raise typer.Exit(1)
