from __future__ import annotations

import io
import shutil
import stat
import struct
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd
from pypdf import PdfReader

from dashboard.imports.contracts import (
    DataContractError,
    ImportFileMetadata,
    validate_1049_dataframe_contract,
)

from .base import (
    BinaryArtifact,
    ToolIntegrationError,
    ToolKey,
    register_tool_import_paths,
)

MAX_1049_PDF_FILES = 100
MAX_1049_ZIP_ENTRIES = 200
MAX_1049_CENTRAL_DIRECTORY_BYTES = 2 * 1024 * 1024
MAX_1049_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_1049_SINGLE_PDF_BYTES = 100 * 1024 * 1024
MAX_1049_COMPRESSION_RATIO = 100
MAX_1049_PAGES_PER_PDF = 250
MAX_1049_TOTAL_PAGES = 1_000
MAX_1049_RESULT_ROWS = 50_000


@dataclass(slots=True)
class PdfExtractionResult:
    dataframe: pd.DataFrame
    excel_artifact: BinaryArtifact
    file_metadata: ImportFileMetadata


def extract_pdf_zip(payload: bytes, target_directory: Path) -> list[Path]:
    _validate_zip_directory(payload)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as zip_ref:
            archive_members = zip_ref.infolist()
            if len(archive_members) > MAX_1049_ZIP_ENTRIES:
                raise ToolIntegrationError(
                    f"Die ZIP darf maximal {MAX_1049_ZIP_ENTRIES} Eintraege enthalten."
                )
            members = _validate_pdf_members(archive_members)
            extracted_files: list[Path] = []
            target_root = target_directory.resolve()
            for member, relative_path in members:
                target_path = (target_root / relative_path).resolve()
                if not target_path.is_relative_to(target_root):
                    raise ToolIntegrationError(
                        "Die ZIP enthaelt einen unzulaessigen Dateipfad."
                    )
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_ref.open(member) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_files.append(target_path)
    except ToolIntegrationError:
        raise
    except zipfile.BadZipFile as exc:
        raise ToolIntegrationError(
            "Die hochgeladene Datei ist keine gueltige ZIP."
        ) from exc
    except (NotImplementedError, RuntimeError, zipfile.LargeZipFile) as exc:
        raise ToolIntegrationError(
            "Die ZIP verwendet eine nicht unterstuetzte Komprimierung."
        ) from exc

    _validate_pdf_complexity(extracted_files)
    return extracted_files


def _validate_zip_directory(payload: bytes) -> None:
    signature = b"PK\x05\x06"
    minimum_record_size = 22
    search_start = max(0, len(payload) - (65_535 + minimum_record_size))
    search_end = len(payload)
    record_offset = -1

    while search_end > search_start:
        candidate = payload.rfind(signature, search_start, search_end)
        if candidate < 0:
            break
        if candidate + minimum_record_size <= len(payload):
            comment_length = struct.unpack_from("<H", payload, candidate + 20)[0]
            if candidate + minimum_record_size + comment_length == len(payload):
                record_offset = candidate
                break
        search_end = candidate

    if record_offset < 0:
        raise ToolIntegrationError("Die hochgeladene Datei ist keine gueltige ZIP.")

    entry_count = struct.unpack_from("<H", payload, record_offset + 10)[0]
    directory_size = struct.unpack_from("<I", payload, record_offset + 12)[0]
    if entry_count == 0xFFFF or directory_size == 0xFFFFFFFF:
        raise ToolIntegrationError("ZIP64-Archive werden nicht unterstuetzt.")
    if entry_count > MAX_1049_ZIP_ENTRIES:
        raise ToolIntegrationError(
            f"Die ZIP darf maximal {MAX_1049_ZIP_ENTRIES} Eintraege enthalten."
        )
    if directory_size > MAX_1049_CENTRAL_DIRECTORY_BYTES:
        raise ToolIntegrationError("Das ZIP-Dateiverzeichnis ist zu gross.")


def _validate_pdf_members(
    members: list[zipfile.ZipInfo],
) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
    files = [member for member in members if not member.is_dir()]
    if not files:
        raise ToolIntegrationError("Die ZIP enthaelt keine PDF-Dateien.")
    if len(files) > MAX_1049_PDF_FILES:
        raise ToolIntegrationError(
            f"Die ZIP darf maximal {MAX_1049_PDF_FILES} PDF-Dateien enthalten."
        )

    total_size = sum(member.file_size for member in files)
    if total_size > MAX_1049_UNCOMPRESSED_BYTES:
        raise ToolIntegrationError("Die entpackte Gesamtgroesse der ZIP ist zu hoch.")

    validated: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    normalized_names: set[str] = set()
    for member in files:
        relative_path = PurePosixPath(member.filename)
        if (
            relative_path.is_absolute()
            or "\\" in member.filename
            or any(part in {"", ".", ".."} for part in relative_path.parts)
        ):
            raise ToolIntegrationError(
                f"Unzulaessiger Dateipfad in der ZIP: {member.filename}"
            )
        if relative_path.suffix.lower() != ".pdf":
            raise ToolIntegrationError(
                f"Die ZIP darf nur PDF-Dateien enthalten. Gefunden: {member.filename}"
            )
        if member.flag_bits & 0x1:
            raise ToolIntegrationError(
                f"Verschluesselte ZIP-Eintraege werden nicht unterstuetzt: "
                f"{member.filename}"
            )
        if stat.S_ISLNK(member.external_attr >> 16):
            raise ToolIntegrationError(
                f"Symbolische Links sind in der ZIP nicht erlaubt: {member.filename}"
            )
        if member.file_size > MAX_1049_SINGLE_PDF_BYTES:
            raise ToolIntegrationError(
                f"Eine PDF in der ZIP ist zu gross: {member.filename}"
            )
        if member.file_size and (
            member.file_size / max(member.compress_size, 1) > MAX_1049_COMPRESSION_RATIO
        ):
            raise ToolIntegrationError(
                f"Unzulaessig hohe Kompressionsrate: {member.filename}"
            )

        normalized_name = relative_path.as_posix().casefold()
        if normalized_name in normalized_names:
            raise ToolIntegrationError(
                f"Doppelter Dateipfad in der ZIP: {member.filename}"
            )
        normalized_names.add(normalized_name)
        validated.append((member, relative_path))

    return validated


def _validate_pdf_complexity(pdf_files: list[Path]) -> None:
    total_pages = 0
    for pdf_file in pdf_files:
        try:
            reader = PdfReader(pdf_file)
            if reader.is_encrypted:
                raise ToolIntegrationError(
                    f"Verschluesselte PDFs werden nicht unterstuetzt: {pdf_file.name}"
                )
            page_count = len(reader.pages)
        except ToolIntegrationError:
            raise
        except Exception as exc:
            raise ToolIntegrationError(
                f"PDF konnte nicht gelesen werden: {pdf_file.name}"
            ) from exc
        if page_count > MAX_1049_PAGES_PER_PDF:
            raise ToolIntegrationError(
                f"PDF hat zu viele Seiten: {pdf_file.name} "
                f"(maximal {MAX_1049_PAGES_PER_PDF})"
            )
        total_pages += page_count
        if total_pages > MAX_1049_TOTAL_PAGES:
            raise ToolIntegrationError(
                f"Die PDFs duerfen zusammen maximal {MAX_1049_TOTAL_PAGES} "
                "Seiten enthalten."
            )


def extract_zip_payload(uploaded_zip: Any) -> PdfExtractionResult:
    if uploaded_zip is None:
        raise ToolIntegrationError("Bitte eine ZIP-Datei hochladen.")

    register_tool_import_paths(ToolKey.PDF_1049)

    try:
        from main import (  # type: ignore
            PdfProcessingError,
            export_to_excel_bytes,
            process_all_pdfs,
        )
    except Exception as exc:
        raise ToolIntegrationError(
            "1049-Toolmodul konnte nicht importiert werden."
        ) from exc

    payload = uploaded_zip.getvalue()
    if not isinstance(payload, bytes):
        raise ToolIntegrationError("Die hochgeladene ZIP konnte nicht gelesen werden.")
    file_metadata = ImportFileMetadata.from_payload(
        str(getattr(uploaded_zip, "name", "")), payload
    )

    with TemporaryDirectory() as temp_dir:
        extract_pdf_zip(payload, Path(temp_dir))
        try:
            dataframe: pd.DataFrame = process_all_pdfs(
                temp_dir, strict=True, verbose=False
            )
        except PdfProcessingError as exc:
            raise ToolIntegrationError(str(exc)) from exc
        except Exception as exc:
            raise ToolIntegrationError(
                "Die 1049-PDF-Verarbeitung ist fehlgeschlagen."
            ) from exc

    try:
        validate_1049_dataframe_contract(dataframe)
    except DataContractError as exc:
        raise ToolIntegrationError(str(exc)) from exc
    if len(dataframe) > MAX_1049_RESULT_ROWS:
        raise ToolIntegrationError(
            f"Der 1049-Import darf maximal {MAX_1049_RESULT_ROWS} Positionen enthalten."
        )

    try:
        excel_payload: bytes = export_to_excel_bytes(dataframe)
    except Exception as exc:
        raise ToolIntegrationError(
            "Die 1049-Excel-Ausgabe konnte nicht erstellt werden."
        ) from exc
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact = BinaryArtifact(
        file_name=f"PDF_Extract_{timestamp}.xlsx",
        payload=excel_payload,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return PdfExtractionResult(
        dataframe=dataframe,
        excel_artifact=artifact,
        file_metadata=file_metadata,
    )
