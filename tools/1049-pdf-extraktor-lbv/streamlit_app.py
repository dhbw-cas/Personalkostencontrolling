import os
import tempfile
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

from main import export_to_excel_bytes, process_all_pdfs


st.set_page_config(page_title="PDF-Extraktor", page_icon="📄", layout="wide")

st.title("PDF-Extraktor")

st.markdown(
    """
<style>
.card {
  border: 1px solid #e6e6e6;
  border-radius: 12px;
  padding: 16px;
  background: #fafafa;
}
.step-title {
  font-weight: 600;
  margin-bottom: 6px;
}
</style>
""",
    unsafe_allow_html=True,
)

st.subheader("So funktioniert's")
step_cols = st.columns(3)
with step_cols[0]:
    st.markdown(
        "<div class='card'><div class='step-title'>1) ZIP hochladen</div>"
        "Enthält nur PDFs, optional in Unterordnern.</div>",
        unsafe_allow_html=True,
    )
with step_cols[1]:
    st.markdown(
        "<div class='card'><div class='step-title'>2) Extraktion</div>"
        "PDFs werden automatisch verarbeitet.</div>",
        unsafe_allow_html=True,
    )
with step_cols[2]:
    st.markdown(
        "<div class='card'><div class='step-title'>3) Excel herunterladen</div>"
        "Download des fertigen Extrakts.</div>",
        unsafe_allow_html=True,
    )

st.divider()
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("Upload")
    st.markdown(
        "<div class='card'>ZIP-Datei mit PDFs auswählen und hochladen.</div>",
        unsafe_allow_html=True,
    )
    uploaded_zip = st.file_uploader("ZIP-Datei", type=["zip"], accept_multiple_files=False)
    if uploaded_zip is not None:
        with st.spinner("ZIP wird verarbeitet..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    with zipfile.ZipFile(uploaded_zip) as zip_ref:
                        members = [m for m in zip_ref.infolist() if not m.is_dir()]
                        non_pdfs = [
                            m.filename
                            for m in members
                            if not m.filename.lower().endswith(".pdf")
                        ]
                        if non_pdfs:
                            st.error(
                                "Die ZIP darf nur PDF-Dateien enthalten. "
                                "Gefundene Nicht-PDF-Dateien: "
                                + ", ".join(non_pdfs[:5])
                                + (" ..." if len(non_pdfs) > 5 else "")
                            )
                            st.stop()
                        zip_ref.extractall(temp_dir)
                except zipfile.BadZipFile:
                    st.error("Die hochgeladene Datei ist keine gültige ZIP-Datei.")
                else:
                    progress = st.progress(0)
                    status = st.empty()

                    def progress_callback(current, total, pdf_path):
                        progress.progress(int(current / total * 100))
                        status.write(
                            f"Verarbeite {current}/{total}: {os.path.basename(pdf_path)}"
                        )

                    df = process_all_pdfs(temp_dir, progress_callback=progress_callback)
                    progress.empty()
                    status.empty()

                    if df.empty:
                        st.warning(
                            "Keine PDF-Daten gefunden oder keine Einträge extrahiert."
                        )
                    else:
                        st.success(f"{len(df)} Positionen extrahiert.")

                        excel_bytes = export_to_excel_bytes(df)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"PDF_Extract_{timestamp}.xlsx"

                        st.download_button(
                            label="Excel herunterladen",
                            data=excel_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

with right_col:
    st.subheader("Vorschau & Auswertung")
    if uploaded_zip is None:
        st.markdown(
            "<div class='card'>Nach dem Upload erscheinen hier Vorschau und Summary.</div>",
            unsafe_allow_html=True,
        )
    else:
        if "df" in locals() and not df.empty:
            st.dataframe(df, use_container_width=True)

            st.subheader("Zusammenfassung")
            total = df["Betrag (€)"].sum()
            summary_df = pd.DataFrame(
                {
                    "Metrik": [
                        "Anzahl Positionen",
                        "Gesamtsumme (€)",
                        "Anzahl Standorte",
                        "Anzahl Dateien",
                    ],
                    "Wert": [
                        len(df),
                        f"{total:,.2f}",
                        df["Standort"].nunique(),
                        df["Quelldatei"].nunique(),
                    ],
                }
            )
            st.table(summary_df)

            if "Standort" in df.columns:
                st.subheader("Standort-Übersicht")
                standort_summary = (
                    df.groupby("Standort")["Betrag (€)"]
                    .agg(["count", "sum"])
                    .reset_index()
                )
                standort_summary.columns = [
                    "Standort",
                    "Anzahl Positionen",
                    "Gesamtbetrag (€)",
                ]
                st.dataframe(standort_summary, use_container_width=True)


st.caption("Tipp: Die ZIP kann Unterordner enthalten. Es werden alle PDFs verarbeitet.")
