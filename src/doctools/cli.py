"""doctools 命令行入口。"""

from __future__ import annotations

from pathlib import Path

import typer

from doctools import __version__
from doctools.docx import strip_headers

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


def _plan(src: Path, dst: Path | None) -> list[tuple[Path, Path]]:
    """把输入（文件或目录）展开成 [(源文件, 目标文件)] 处理计划。"""
    if src.is_file():
        if src.suffix.lower() != ".docx":
            raise typer.BadParameter(f"不支持的格式：{src}（仅支持 .docx）")
        out = dst if dst is not None else src.with_name(f"{src.stem}_cleaned.docx")
        return [(src, out)]

    out_dir = dst if dst is not None else src.with_name(f"{src.name}_cleaned")
    files = sorted(src.glob("*.docx"))
    if not files:
        raise typer.BadParameter(f"目录中没有找到 .docx 文件：{src}")
    return [(f, out_dir / f.name) for f in files]


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
) -> None:
    """批量去除 Word（.docx）文档的页眉。"""
    pairs = _plan(input_path, output)

    if dry_run:
        for src, dst in pairs:
            typer.echo(f"[dry-run] 将处理 {src} -> {dst}")
        return

    ok = 0
    for src, dst in pairs:
        try:
            strip_headers(src, dst)
        except Exception as exc:
            typer.echo(f"[FAIL] 处理失败 {src}: {exc}", err=True)
        else:
            ok += 1
            typer.echo(f"[OK] {src} -> {dst}")

    if ok < len(pairs):
        raise typer.Exit(1)
