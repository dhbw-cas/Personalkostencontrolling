from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.config import DatabaseConfigError, get_app_version
from dashboard.db.engine import get_session_factory
from dashboard.imports.contracts import DataContractError, ImportFileMetadata
from dashboard.imports.service import (
    DuplicateImportError,
    ImportPersistenceError,
    ImportService,
)
from dashboard.integrations.base import ToolIntegrationError
from dashboard.integrations.tool_1049_adapter import extract_zip_payload
from dashboard.state import (
    KEY_1049_DATAFRAME,
    KEY_1049_EXPORT_BYTES,
    KEY_1049_EXPORT_NAME,
    KEY_1049_FILE_METADATA,
    KEY_1049_IMPORT_ID,
    KEY_1049_UPLOAD_SIGNATURE,
    clear_1049_result,
    init_state,
)
from dashboard.ui import render_hero
from dashboard.upload_validation import UploadValidationError, validate_1049_zip_upload

init_state(st.session_state)

render_hero(
    title="PDF-Extraktion",
    description=(
        "Lade ein ZIP-Bündel mit PDF-Dateien hoch. "
        "Die Anwendung extrahiert Positionen und erstellt eine Excel-Ausgabe."
    ),
)

with st.container(border=True):
    st.markdown("**Eingabe**")
    uploaded_zip = st.file_uploader("ZIP-Datei hochladen", type=["zip"])
    st.caption(
        "Erlaubt sind ausschließlich PDF-Dateien innerhalb des ZIP-Bündels. "
        "Maximale Uploadgröße: 200 MB, maximal 100 PDFs."
    )

current_metadata = None
current_signature = None
if uploaded_zip is not None:
    current_metadata = ImportFileMetadata.from_payload(
        str(uploaded_zip.name), uploaded_zip.getvalue()
    )
    current_signature = current_metadata.sha256
stored_signature = st.session_state.get(KEY_1049_UPLOAD_SIGNATURE)
if stored_signature is not None and current_signature != stored_signature:
    clear_1049_result(st.session_state)

if uploaded_zip is not None and st.button(
    "Extraktion starten", use_container_width=True
):
    clear_1049_result(st.session_state)
    with st.spinner("Die Extraktion wird ausgeführt..."):
        try:
            validate_1049_zip_upload(uploaded_zip)
            result = extract_zip_payload(uploaded_zip)
        except (ToolIntegrationError, UploadValidationError) as exc:
            st.error(str(exc))
        else:
            st.session_state[KEY_1049_DATAFRAME] = result.dataframe
            st.session_state[KEY_1049_EXPORT_BYTES] = result.excel_artifact.payload
            st.session_state[KEY_1049_EXPORT_NAME] = result.excel_artifact.file_name
            st.session_state[KEY_1049_FILE_METADATA] = result.file_metadata
            st.session_state[KEY_1049_UPLOAD_SIGNATURE] = current_signature
            st.success(f"Extraktion erfolgreich: {len(result.dataframe)} Positionen.")

dataframe: pd.DataFrame | None = st.session_state.get(KEY_1049_DATAFRAME)
if isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
    total_amount = (
        dataframe["Betrag (€)"].sum() if "Betrag (€)" in dataframe.columns else 0
    )
    c1, c2, c3 = st.columns(3, vertical_alignment="center")
    c1.metric("Positionen", value=len(dataframe))
    c2.metric("Dateien", value=int(dataframe["Quelldatei"].nunique()))
    c3.metric("Gesamtsumme", value=f"{total_amount:,.2f} EUR")

    tab_daten, tab_auswertung = st.tabs(["Datenvorschau", "Auswertung"])
    with tab_daten:
        st.dataframe(dataframe, use_container_width=True, hide_index=True)
    with tab_auswertung:
        if "Standort" in dataframe.columns and "Betrag (€)" in dataframe.columns:
            standort_summary = dataframe.groupby("Standort", as_index=False).agg(
                **{
                    "Anzahl Positionen": ("Betrag (€)", "count"),
                    "Gesamtbetrag": ("Betrag (€)", "sum"),
                }
            )
            st.dataframe(standort_summary, use_container_width=True, hide_index=True)
        else:
            st.caption("Keine Standortauswertung verfügbar.")

file_metadata = st.session_state.get(KEY_1049_FILE_METADATA)
saved_import_id = st.session_state.get(KEY_1049_IMPORT_ID)
if (
    isinstance(dataframe, pd.DataFrame)
    and not dataframe.empty
    and isinstance(file_metadata, ImportFileMetadata)
):
    with st.container(border=True):
        st.markdown("**PostgreSQL**")
        st.caption(
            f"Upload: {file_metadata.original_filename} · "
            f"SHA256: {file_metadata.sha256[:12]}..."
        )
        if isinstance(saved_import_id, str):
            st.success(f"Import gespeichert. Import-ID: {saved_import_id}")
            st.page_link(
                "app_pages/data_browser.py",
                label="Import im Datenbestand öffnen",
                use_container_width=True,
            )
        elif st.button("In PostgreSQL speichern", use_container_width=True):
            try:
                if uploaded_zip is None:
                    raise DataContractError(
                        "Die zugehörige ZIP-Datei ist nicht mehr ausgewählt."
                    )
                if current_metadata is None or current_metadata != file_metadata:
                    raise DataContractError(
                        "Der aktuelle Upload gehört nicht zur angezeigten Vorschau. "
                        "Bitte die Extraktion erneut starten."
                    )
                service = ImportService(get_session_factory())
                saved = service.save_1049_import(
                    dataframe,
                    file_metadata,
                    app_version=get_app_version(),
                )
            except DuplicateImportError as exc:
                st.warning(str(exc))
            except (
                DataContractError,
                DatabaseConfigError,
                ImportPersistenceError,
            ) as exc:
                st.error(str(exc))
            else:
                st.session_state[KEY_1049_IMPORT_ID] = str(saved.id)
                st.success(
                    f"Import erfolgreich gespeichert: {saved.row_count} Positionen."
                )
                st.rerun()

export_bytes = st.session_state.get(KEY_1049_EXPORT_BYTES)
export_name = st.session_state.get(KEY_1049_EXPORT_NAME)
if isinstance(export_bytes, bytes) and isinstance(export_name, str):
    with st.container(border=True):
        st.markdown("**Export**")
        st.download_button(
            "Excel-Datei herunterladen",
            data=export_bytes,
            file_name=export_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
