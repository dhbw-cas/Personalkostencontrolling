from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base import (
    BinaryArtifact,
    ToolIntegrationError,
    ToolKey,
    register_tool_import_paths,
)


@dataclass(slots=True)
class ReleExtractionResult:
    dataframe: pd.DataFrame
    documents_count: int


def extract_rele_documents(uploaded_files: list[Any]) -> ReleExtractionResult:
    if not uploaded_files:
        raise ToolIntegrationError(
            "Bitte mindestens eine PDF- oder ZIP-Datei hochladen."
        )

    register_tool_import_paths(ToolKey.RELE_1067)

    try:
        from relelisten_extraktor import (  # type: ignore
            DocumentLoadError,
            collect_pdf_documents,
            parse_documents,
        )
        from relelisten_extraktor.export import rows_to_dataframe  # type: ignore
    except Exception as exc:
        raise ToolIntegrationError(
            "1067-Toolmodul konnte nicht importiert werden."
        ) from exc

    try:
        documents = collect_pdf_documents(uploaded_files)
    except DocumentLoadError as exc:
        raise ToolIntegrationError(str(exc)) from exc

    if not documents:
        raise ToolIntegrationError("Es wurden keine PDF-Dokumente gefunden.")

    rows = parse_documents(documents)
    if not rows:
        raise ToolIntegrationError("Keine auswertbaren Datensätze gefunden.")

    dataframe = rows_to_dataframe(rows)
    return ReleExtractionResult(dataframe=dataframe, documents_count=len(documents))


def build_rele_exports(
    dataframe: pd.DataFrame, suffix: str
) -> tuple[BinaryArtifact, BinaryArtifact]:
    register_tool_import_paths(ToolKey.RELE_1067)

    try:
        from relelisten_extraktor import (  # type: ignore
            dataframe_to_csv_bytes,
            dataframe_to_excel_bytes,
        )
    except Exception as exc:
        raise ToolIntegrationError(
            "1067-Exportfunktionen konnten nicht geladen werden."
        ) from exc

    csv_artifact = BinaryArtifact(
        file_name=f"releliste_{suffix}.csv",
        payload=dataframe_to_csv_bytes(dataframe),
        mime_type="text/csv",
    )
    xlsx_artifact = BinaryArtifact(
        file_name=f"releliste_{suffix}.xlsx",
        payload=dataframe_to_excel_bytes(dataframe),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return csv_artifact, xlsx_artifact
