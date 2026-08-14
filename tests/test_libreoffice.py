"""LibreOffice 引擎与 Office → PDF 引擎工厂测试。"""

from __future__ import annotations

import pytest

from doctools.errors import OFFICE_NOT_INSTALLED, DoctoolsError
from doctools.libreoffice import LibreOfficePdfConverter, find_soffice, soffice_available


def test_find_soffice_env_override(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "soffice.exe"
    fake.write_bytes(b"x")
    monkeypatch.setenv("DOCTOOLS_LIBREOFFICE_PATH", str(fake))

    assert find_soffice() == str(fake)


def test_soffice_available_false_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("doctools.libreoffice.find_soffice", lambda: None)

    assert soffice_available() is False


def test_converter_raises_when_soffice_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("doctools.libreoffice.find_soffice", lambda: None)

    with pytest.raises(DoctoolsError) as excinfo:
        LibreOfficePdfConverter()

    assert excinfo.value.code == OFFICE_NOT_INSTALLED


def test_create_pdf_engine_prefers_com(monkeypatch: pytest.MonkeyPatch) -> None:
    from doctools.office_engine import create_pdf_engine

    class FakeCom:
        def close(self) -> None: ...

    monkeypatch.setattr("doctools.office.com_available", lambda: True)
    monkeypatch.setattr("doctools.office.OfficeConverter", lambda: FakeCom())

    engine = create_pdf_engine()

    assert isinstance(engine, FakeCom)


def test_create_pdf_engine_falls_back_to_libreoffice(monkeypatch: pytest.MonkeyPatch) -> None:
    from doctools.libreoffice import LibreOfficePdfConverter
    from doctools.office_engine import create_pdf_engine

    monkeypatch.setattr("doctools.office.com_available", lambda: False)
    monkeypatch.setattr("doctools.libreoffice.find_soffice", lambda: "C:/fake/soffice.exe")

    engine = create_pdf_engine()

    assert isinstance(engine, LibreOfficePdfConverter)
    engine.close()
