# RELElisten-Extraktor

Streamlit-App zum Extrahieren von Abrechnungsdaten aus textbasierten RELE-PDFs (Besoldung und Verguetung).

## Start

```bash
uv sync
uv run streamlit run streamlit_app.py
```

## Qualitaetschecks

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```
