"""Word 文档（.docx）处理逻辑。"""

from __future__ import annotations

from pathlib import Path

from docx import Document


def _clear_defined_header(header) -> None:
    """清空一个已定义（未继承）页眉的所有内容。

    包括文字、图片等 run 元素，以及表格。被其他节继承的页眉无需单独
    处理——它们继承自本页眉，来源清空后自然随之清空。
    """
    for paragraph in list(header.paragraphs):
        for run in list(paragraph.runs):
            run._r.getparent().remove(run._r)

    for table in list(header.tables):
        table._tbl.getparent().remove(table._tbl)


def clear_headers(doc: Document) -> None:
    """去除文档所有节的页眉（含首页、奇偶页变体）。

    只处理那些自带内容的页眉（``is_linked_to_previous`` 为 False 的），
    避免为不使用的首页 / 奇偶页页眉生成多余的 XML 定义。
    """
    for section in doc.sections:
        for header in (
            section.header,
            section.first_page_header,
            section.even_page_header,
        ):
            if not header.is_linked_to_previous:
                _clear_defined_header(header)


def strip_headers(src: Path, dst: Path) -> None:
    """读取一个 .docx，去除页眉后保存到 dst。"""
    doc = Document(str(src))
    clear_headers(doc)
    doc.save(str(dst))
