from __future__ import annotations

import streamlit as st

from dashboard.integrations.base import collect_tool_diagnostics
from dashboard.state import init_state
from dashboard.ui import render_hero

init_state(st.session_state)

TOOL_BOX_HEIGHT = 220

render_hero(
    title="Willkommen in der RELE-Toolbox",
    description=(
        "Diese Anwendung bündelt die RELE-Werkzeuge. "
        "Sie können jedes Tool direkt auswählen."
    ),
)

st.subheader("Toolübersicht")
left, middle, right, inventory = st.columns(4, vertical_alignment="top")
with left:
    with st.container(border=True, height=TOOL_BOX_HEIGHT):
        st.markdown("**PDF-Extraktor**")
        st.caption(
            "Extrahiert Positionen aus PDF-Bündeln und erzeugt eine Excel-Ausgabe."
        )
        st.page_link(
            "app_pages/tool_1049_pdf_extraktor.py",
            label="Tool öffnen",
            use_container_width=True,
        )
with middle:
    with st.container(border=True, height=TOOL_BOX_HEIGHT):
        st.markdown("**RELE-Listen-Extraktor**")
        st.caption(
            "Liest RELE-PDF-Dateien aus und exportiert strukturierte Abrechnungsdaten."
        )
        st.page_link(
            "app_pages/tool_1067_relelisten_extraktor.py",
            label="Tool öffnen",
            use_container_width=True,
        )
with right:
    with st.container(border=True, height=TOOL_BOX_HEIGHT):
        st.markdown("**Buchungsimporteur**")
        st.caption("Validiert Eingaben und erzeugt die finale SAP-LBV-Importdatei.")
        st.page_link(
            "app_pages/tool_1052_buchungsimporteur.py",
            label="Tool öffnen",
            use_container_width=True,
        )
with inventory:
    with st.container(border=True, height=TOOL_BOX_HEIGHT):
        st.markdown("**Datenbestand**")
        st.caption("Zeigt gespeicherte Imports und ihre technischen Quelldaten.")
        st.page_link(
            "app_pages/data_browser.py",
            label="Datenbestand öffnen",
            use_container_width=True,
        )

st.caption(
    "Diese Anwendung enthält nur Orchestrierung "
    "und Bedienoberfläche. "
    "Die Fachlogik bleibt in den jeweiligen Einzel-Repos."
)

with st.expander("Systemdiagnose", expanded=False):
    diagnostics = collect_tool_diagnostics()
    rows = [
        {
            "Tool": diagnostic.display_name,
            "Tool-Verzeichnis": "bereit" if diagnostic.tool_available else "fehlt",
            "Import": "ok" if diagnostic.import_available else "fehlerhaft",
            "Pfad": str(diagnostic.path),
            "Details": diagnostic.detail,
        }
        for diagnostic in diagnostics
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
