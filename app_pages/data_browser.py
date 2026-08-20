from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

import pandas as pd
import streamlit as st

from dashboard.config import DatabaseConfigError
from dashboard.db.engine import get_session_factory
from dashboard.imports.service import ImportPersistenceError, ImportService
from dashboard.state import KEY_1049_IMPORT_ID, init_state
from dashboard.ui import render_hero

init_state(st.session_state)

render_hero(
    title="Datenbestand",
    description=(
        "Prüfen Sie gespeicherte 1049-Imports und ihre technischen "
        "Herkunftsinformationen."
    ),
)

try:
    service = ImportService(get_session_factory())
    imports = service.list_1049_imports(limit=100)
except (DatabaseConfigError, ImportPersistenceError) as exc:
    st.info(str(exc))
    st.stop()

if not imports:
    st.info("Es wurden noch keine 1049-Imports gespeichert.")
    st.stop()

st.subheader("Importhistorie")
history_rows = [
    {
        "Datum": item.created_at,
        "Quelle": "1049",
        "Import-ID": str(item.id),
        "Benutzer": item.imported_by or "nicht erfasst",
        "Dateien": ", ".join(item.filenames),
        "Datensätze": item.row_count,
    }
    for item in imports
]
st.dataframe(history_rows, use_container_width=True, hide_index=True)

import_ids = [str(item.id) for item in imports]
preferred_import_id = st.session_state.get(KEY_1049_IMPORT_ID)
selected_index = (
    import_ids.index(preferred_import_id)
    if isinstance(preferred_import_id, str) and preferred_import_id in import_ids
    else 0
)
selected_import_id = st.selectbox(
    "Import auswählen",
    options=import_ids,
    index=selected_index,
)

try:
    rows = service.list_1049_rows(UUID(selected_import_id), limit=1_000)
except ImportPersistenceError as exc:
    st.error(str(exc))
else:
    st.subheader("Gespeicherte Positionen")
    if len(rows) == 1_000:
        st.warning("Die Ansicht ist auf 1.000 Positionen begrenzt.")
    dataframe = pd.DataFrame(asdict(row) for row in rows)
    st.dataframe(dataframe, use_container_width=True, hide_index=True)
