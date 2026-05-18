from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


class UploadedFileLike(Protocol):
    name: str

    def getvalue(self) -> bytes: ...


class DocumentLoadError(ValueError):
    pass


@dataclass(frozen=True)
class PdfDocument:
    name: str
    content: bytes


def collect_pdf_documents(
    uploaded_files: Iterable[UploadedFileLike],
) -> list[PdfDocument]:
    documents: list[PdfDocument] = []

    for uploaded_file in uploaded_files:
        filename = Path(uploaded_file.name).name
        suffix = Path(filename).suffix.lower()
        file_content = uploaded_file.getvalue()

        if suffix == ".pdf":
            documents.append(PdfDocument(name=filename, content=file_content))
            continue

        if suffix == ".zip":
            documents.extend(_extract_pdf_documents_from_zip(filename, file_content))
            continue

        raise DocumentLoadError(f"Nicht unterstuetzter Dateityp: {filename}")

    return documents


def _extract_pdf_documents_from_zip(
    zip_name: str, zip_content: bytes
) -> list[PdfDocument]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as archive:
            pdf_names = sorted(
                name
                for name in archive.namelist()
                if not name.endswith("/") and Path(name).suffix.lower() == ".pdf"
            )
            return [
                PdfDocument(name=Path(name).name, content=archive.read(name))
                for name in pdf_names
            ]
    except zipfile.BadZipFile as error:
        raise DocumentLoadError(f"Ungueltiges ZIP-Archiv: {zip_name}") from error
