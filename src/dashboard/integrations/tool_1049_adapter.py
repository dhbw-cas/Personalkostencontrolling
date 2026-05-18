from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

from .base import (
    BinaryArtifact,
    ToolIntegrationError,
    ToolKey,
    register_tool_import_paths,
)


@dataclass(slots=True)
class PdfExtractionResult:
    dataframe: pd.DataFrame
    excel_artifact: BinaryArtifact


def extract_zip_payload(uploaded_zip: Any) -> PdfExtractionResult:
    if uploaded_zip is None:
        raise ToolIntegrationError("Bitte eine ZIP-Datei hochladen.")

    register_tool_import_paths(ToolKey.PDF_1049)

    try:
        from main import export_to_excel_bytes, process_all_pdfs  # type: ignore
    except Exception as exc:
        raise ToolIntegrationError(
            "1049-Toolmodul konnte nicht importiert werden."
        ) from exc

    payload = uploaded_zip.getvalue()

    with TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as zip_ref:
                members = [m for m in zip_ref.infolist() if not m.is_dir()]
                non_pdfs = [
                    member.filename
                    for member in members
                    if not member.filename.lower().endswith(".pdf")
                ]
                if non_pdfs:
                    preview = ", ".join(non_pdfs[:5])
                    suffix = " ..." if len(non_pdfs) > 5 else ""
                    raise ToolIntegrationError(
                        "Die ZIP darf nur PDF-Dateien enthalten. "
                        f"Gefunden: {preview}{suffix}"
                    )
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile as exc:
            raise ToolIntegrationError(
                "Die hochgeladene Datei ist keine gültige ZIP."
            ) from exc

        dataframe: pd.DataFrame = process_all_pdfs(temp_dir)

    if dataframe.empty:
        raise ToolIntegrationError("Keine auswertbaren Positionen gefunden.")

    excel_payload: bytes = export_to_excel_bytes(dataframe)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact = BinaryArtifact(
        file_name=f"PDF_Extract_{timestamp}.xlsx",
        payload=excel_payload,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return PdfExtractionResult(dataframe=dataframe, excel_artifact=artifact)
