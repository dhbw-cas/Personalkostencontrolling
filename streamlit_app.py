from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dashboard.state import init_state  # noqa: E402
from dashboard.ui import apply_global_style  # noqa: E402

st.set_page_config(
    page_title="RELE Prozesszentrale",
    layout="wide",
)

init_state(st.session_state)
apply_global_style()

page = st.navigation(
    [
        st.Page("app_pages/home.py", title="Startseite"),
        st.Page(
            "app_pages/tool_1049_pdf_extraktor.py",
            title="1049 PDF-Extraktor",
        ),
        st.Page(
            "app_pages/tool_1067_relelisten_extraktor.py",
            title="1067 RELElisten-Extraktor",
        ),
        st.Page(
            "app_pages/tool_1052_buchungsimporteur.py",
            title="1052 Buchungsimporteur",
        ),
        st.Page("app_pages/data_browser.py", title="Datenbestand"),
    ],
    position="top",
)

st.title(page.title)
st.caption(
    "Zentrale Oberfläche für die LBV-Werkzeuge und gespeicherte Imports. "
    "Wählen Sie das passende Tool für Ihren Anwendungsfall."
)

page.run()
