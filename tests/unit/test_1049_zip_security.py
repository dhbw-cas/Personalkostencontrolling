from __future__ import annotations

import io
import sys
import types
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from pypdf import PdfWriter
from pytest import MonkeyPatch

from dashboard.imports.contracts import EXPECTED_1049_COLUMNS
from dashboard.integrations import tool_1049_adapter
from dashboard.integrations.base import ToolIntegrationError
from dashboard.integrations.tool_1049_adapter import extract_pdf_zip


def _zip_payload(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, payload in files.items():
            archive.writestr(filename, payload)
    return buffer.getvalue()


def test_extract_pdf_zip_extracts_nested_pdfs(tmp_path: Path) -> None:
    payload = _zip_payload({"abrechnung/eins.pdf": _minimal_pdf()})

    extracted = extract_pdf_zip(payload, tmp_path)

    assert extracted == [(tmp_path / "abrechnung" / "eins.pdf").resolve()]
    assert extracted[0].read_bytes() == _minimal_pdf()


@pytest.mark.parametrize("filename", ["../escape.pdf", "/absolute.pdf", "a\\b.pdf"])
def test_extract_pdf_zip_rejects_unsafe_paths(tmp_path: Path, filename: str) -> None:
    payload = _zip_payload({filename: _minimal_pdf()})

    with pytest.raises(ToolIntegrationError, match="Dateipfad"):
        extract_pdf_zip(payload, tmp_path)


def test_extract_pdf_zip_rejects_non_pdf(tmp_path: Path) -> None:
    payload = _zip_payload({"notiz.txt": b"text"})

    with pytest.raises(ToolIntegrationError, match="nur PDF-Dateien"):
        extract_pdf_zip(payload, tmp_path)


def test_extract_pdf_zip_rejects_too_many_files(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(tool_1049_adapter, "MAX_1049_PDF_FILES", 1)
    payload = _zip_payload({"eins.pdf": b"1", "zwei.pdf": b"2"})

    with pytest.raises(ToolIntegrationError, match="maximal 1"):
        extract_pdf_zip(payload, tmp_path)


def test_extract_pdf_zip_limits_directory_entries(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(tool_1049_adapter, "MAX_1049_ZIP_ENTRIES", 1)
    payload = _zip_payload({"ordner/": b"", "ordner/eins.pdf": b"pdf"})

    with pytest.raises(ToolIntegrationError, match="maximal 1 Eintraege"):
        extract_pdf_zip(payload, tmp_path)


def test_extract_pdf_zip_wraps_unsupported_compression(tmp_path: Path) -> None:
    payload = bytearray(_zip_payload({"eins.pdf": b"pdf"}))
    local_header = payload.index(b"PK\x03\x04")
    central_header = payload.index(b"PK\x01\x02")
    payload[local_header + 8 : local_header + 10] = (99).to_bytes(2, "little")
    payload[central_header + 10 : central_header + 12] = (99).to_bytes(2, "little")

    with pytest.raises(ToolIntegrationError, match="nicht unterstuetzte"):
        extract_pdf_zip(bytes(payload), tmp_path)


def test_extract_pdf_zip_checks_actual_entry_count(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(tool_1049_adapter, "MAX_1049_ZIP_ENTRIES", 1)
    payload = bytearray(_zip_payload({"eins.pdf": b"1", "zwei.pdf": b"2"}))
    end_record = payload.rindex(b"PK\x05\x06")
    payload[end_record + 8 : end_record + 12] = (1).to_bytes(2, "little") * 2

    with pytest.raises(ToolIntegrationError, match="maximal 1 Eintraege"):
        extract_pdf_zip(bytes(payload), tmp_path)


def _minimal_pdf() -> bytes:
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    return buffer.getvalue()


class DummyUpload:
    name = "abrechnungen.zip"

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


class FakePdfProcessingError(RuntimeError):
    pass


def _install_fake_1049_module(
    monkeypatch: MonkeyPatch,
    process_all_pdfs: object,
) -> None:
    module = types.ModuleType("main")

    monkeypatch.setattr(
        module, "PdfProcessingError", FakePdfProcessingError, raising=False
    )
    monkeypatch.setattr(module, "process_all_pdfs", process_all_pdfs, raising=False)
    monkeypatch.setattr(
        module, "export_to_excel_bytes", lambda dataframe: b"excel", raising=False
    )
    monkeypatch.setitem(sys.modules, "main", module)
    monkeypatch.setattr(
        tool_1049_adapter,
        "register_tool_import_paths",
        lambda tool: Path("."),
    )


def test_extract_zip_payload_wraps_strict_pdf_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_processing(directory: str, *, strict: bool, verbose: bool) -> pd.DataFrame:
        del directory, strict, verbose
        raise FakePdfProcessingError("PDF konnte nicht verarbeitet werden: defekt.pdf")

    _install_fake_1049_module(monkeypatch, fail_processing)
    upload = DummyUpload(_zip_payload({"defekt.pdf": _minimal_pdf()}))

    with pytest.raises(ToolIntegrationError, match="defekt.pdf"):
        tool_1049_adapter.extract_zip_payload(upload)


def test_extract_zip_payload_disables_tool_output(monkeypatch: MonkeyPatch) -> None:
    def process(directory: str, *, strict: bool, verbose: bool) -> pd.DataFrame:
        del directory, strict
        assert verbose is False
        return pd.DataFrame(
            [["Position", 1.0, "Ort", None, "a.pdf", "7002", "", 8]],
            columns=EXPECTED_1049_COLUMNS,
        )

    _install_fake_1049_module(monkeypatch, process)
    upload = DummyUpload(_zip_payload({"a.pdf": _minimal_pdf()}))

    tool_1049_adapter.extract_zip_payload(upload)
