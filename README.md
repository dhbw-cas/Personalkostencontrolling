# 1071 MultiRepo RELE Tools

Orchestrierungs-Repository fuer ein zentrales Streamlit-Dashboard.
Die Fachlogik der drei Werkzeuge liegt in diesem Repo unter `tools/` als Code.

## Zielbild

- Ein gemeinsamer Einstiegspunkt fuer Anwender
- Drei Tool-Seiten in einer App:
- 1049 PDF-Extraktor LBV
- 1067 RELElisten-Extraktor
- 1052 Buchungsimporteur SAP LBV
- Hohe Wartbarkeit durch klare Trennung: UI/Orchestrierung hier, Business-Logik in den Tool-Modulen

## Lokaler Start

```bash
uv sync
uv run streamlit run streamlit_app.py
```

## Struktur

```text
streamlit_app.py
app_pages/
src/dashboard/
src/dashboard/integrations/
tools/
```

- `app_pages/`: Streamlit-Unterseiten je Tool
- `src/dashboard/integrations/`: Adapter-Schicht zu den Tool-Modulen
- `tools/`: vendorte Tool-Repositories

## Pflege der vendorten Tools

### Grundprinzip

Die Verzeichnisse unter `tools/` sind normale Repo-Inhalte.
Es gibt keine Git-Submodule und keine automatische Pointer-Synchronisierung.

Das bedeutet:

- Tool-Aenderungen sind erst sichtbar, wenn sie in diesem Repo uebernommen und committed wurden.

### Tool-Update Ablauf

```bash
git clone <1071-repo-url>
cd 1071_MultiRepo_Rele-Tools
uv sync
```

1. Im jeweiligen Tool-Repo entwickeln, testen und committen.
2. Geaenderte Dateien in das passende Verzeichnis unter `tools/` uebernehmen.
3. Im Dashboard-Repo Qualitaetschecks laufen lassen und alles gemeinsam committen.

Empfehlung: Tool-Updates immer zusammen mit einer kurzen Notiz dokumentieren,
welcher Upstream-Stand uebernommen wurde.

## Qualitaetschecks

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```
