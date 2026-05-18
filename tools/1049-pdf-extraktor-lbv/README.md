# PDF-Extraktor LBV

Dieses Tool extrahiert Tabellenpositionen aus PDF-Dateien und erstellt einen Excel-Export.

## Streamlit-Frontend

1. ZIP-Datei mit PDFs erstellen
2. Streamlit starten

```bash
uv run streamlit run streamlit_app.py
```

Im Browser die ZIP-Datei hochladen und die Excel-Datei herunterladen.

## CLI (optional)

```bash
uv run python main.py
```

`main.py` verarbeitet die PDFs aus dem Ordner, der in `FOLDER_PATH` gesetzt ist.
