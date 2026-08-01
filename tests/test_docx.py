from pathlib import Path

from docx import Document
from typer.testing import CliRunner

from doctools.cli import app
from doctools.docx import clear_headers, strip_headers

runner = CliRunner()


def _doc_with_headers() -> Document:
    doc = Document()

    # 第一节：普通页眉（多行文字）
    h1 = doc.sections[0].header
    h1.is_linked_to_previous = False
    h1.paragraphs[0].text = "CONFIDENTIAL"
    h1.add_paragraph("第二行页眉")
    doc.add_paragraph("正文第一段")

    # 第二节：自定义页眉
    s2 = doc.add_section()
    h2 = s2.header
    h2.is_linked_to_previous = False
    h2.paragraphs[0].text = "Section2 header"
    doc.add_paragraph("正文第二段")
    return doc


def test_clear_headers_removes_all_header_text() -> None:
    doc = _doc_with_headers()
    clear_headers(doc)
    for section in doc.sections:
        assert all(p.text == "" for p in section.header.paragraphs)
        assert all(p.text == "" for p in section.first_page_header.paragraphs)
        assert all(p.text == "" for p in section.even_page_header.paragraphs)


def test_clear_headers_keeps_body_text() -> None:
    doc = _doc_with_headers()
    clear_headers(doc)
    body = [p.text for p in doc.paragraphs]
    assert "正文第一段" in body
    assert "正文第二段" in body


def test_clear_headers_handles_first_page_header() -> None:
    doc = _doc_with_headers()
    doc.sections[0].different_first_page_header_footer = True
    first = doc.sections[0].first_page_header
    first.is_linked_to_previous = False
    first.paragraphs[0].text = "FIRST PAGE"
    clear_headers(doc)
    assert doc.sections[0].first_page_header.paragraphs[0].text == ""


def test_strip_headers_file(tmp_path: Path) -> None:
    src = tmp_path / "in.docx"
    dst = tmp_path / "out.docx"
    _doc_with_headers().save(str(src))

    strip_headers(src, dst)

    out = Document(str(dst))
    assert all(p.text == "" for s in out.sections for p in s.header.paragraphs)
    assert any(p.text.startswith("正文") for p in out.paragraphs)


def test_cli_remove_headers_single_file(tmp_path: Path) -> None:
    src = tmp_path / "in.docx"
    dst = tmp_path / "out.docx"
    _doc_with_headers().save(str(src))

    result = runner.invoke(app, ["remove-headers", str(src), "--output", str(dst)])

    assert result.exit_code == 0, result.stdout
    out = Document(str(dst))
    assert all(p.text == "" for s in out.sections for p in s.header.paragraphs)


def test_cli_remove_headers_dry_run(tmp_path: Path) -> None:
    src = tmp_path / "in.docx"
    _doc_with_headers().save(str(src))

    result = runner.invoke(app, ["remove-headers", str(src), "--dry-run"])

    assert result.exit_code == 0
    assert "[dry-run]" in result.stdout
    assert not (tmp_path / "in_cleaned.docx").exists()


def test_cli_rejects_non_docx(tmp_path: Path) -> None:
    src = tmp_path / "notes.txt"
    src.write_text("hi")

    result = runner.invoke(app, ["remove-headers", str(src)])

    assert result.exit_code != 0
    assert "仅支持 .docx" in result.stderr
