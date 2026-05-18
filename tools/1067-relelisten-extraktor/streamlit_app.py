from __future__ import annotations

import pandas as pd
import streamlit as st

from relelisten_extraktor import (
    DocumentLoadError,
    collect_pdf_documents,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    parse_documents,
)
from relelisten_extraktor.export import rows_to_dataframe


st.set_page_config(page_title="RELElisten-Extraktor", page_icon="📄", layout="wide")

st.title("RELElisten-Extraktor")
st.caption("Textbasierte RELE-PDFs als CSV oder Excel exportieren")

uploaded_files = st.file_uploader(
    "PDF-Dateien oder ZIP-Buendel hochladen",
    type=["pdf", "zip"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Bitte mindestens eine PDF oder ZIP-Datei hochladen.")
    st.stop()

try:
    documents = collect_pdf_documents(uploaded_files)
except DocumentLoadError as error:
    st.error(str(error))
    st.stop()

if not documents:
    st.warning("Es wurden keine PDF-Dateien gefunden.")
    st.stop()

rows = parse_documents(documents)
if not rows:
    st.warning("Keine auswertbaren Datensaetze gefunden.")
    st.stop()

dataframe = rows_to_dataframe(rows)
st.success(f"{len(rows)} Datensaetze aus {len(documents)} Dokument(en) extrahiert.")

preview_tab, download_tab = st.tabs(["Vorschau", "Export"])

with preview_tab:
    st.dataframe(dataframe, use_container_width=True, hide_index=True)

with download_tab:
    csv_content = dataframe_to_csv_bytes(dataframe)
    excel_content = dataframe_to_excel_bytes(dataframe)
    month_value = (
        str(dataframe["Abrechnungsmonat/Jahr"].iloc[0])
        if not dataframe.empty
        else "export"
    )

    left, right = st.columns(2)
    with left:
        st.download_button(
            "CSV herunterladen",
            data=csv_content,
            file_name=f"releliste_{month_value}.csv",
            mime="text/csv",
        )
    with right:
        st.download_button(
            "Excel herunterladen",
            data=excel_content,
            file_name=f"releliste_{month_value}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.divider()
st.subheader("Kurzstatistik")
summary: pd.DataFrame = (
    dataframe.groupby("Buchungsstelle", as_index=False)
    .agg(Anzahl=("Personalnummer", "count"))
    .sort_values("Buchungsstelle")
)
st.dataframe(summary, use_container_width=True, hide_index=True)
