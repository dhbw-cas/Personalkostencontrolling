# Personalkostencontrolling

Streamlit-Prozesszentrale für die RELE-Toolkette. Die Anwendung bündelt die
vendorten Werkzeuge 1049, 1052 und 1067 und baut schrittweise eine
nachvollziehbare PostgreSQL-Datenbasis auf.

Der aktuelle Slice persistiert ausschließlich Ergebnisse des
1049-LBV-PDF-Extraktors. 1067, 1052 und der fachliche Abgleich folgen in
späteren Ausbaustufen.

## Lokale Entwicklung

Voraussetzungen:

- Python 3.12
- `uv`
- erreichbare PostgreSQL-Datenbank für Migration und Speichertests

Installation und Start:

```bash
uv sync --locked
export DATABASE_URL="postgres://...?...sslmode=verify-full&sslrootcert=system"
uv run alembic upgrade head
uv run streamlit run streamlit_app.py
```

Ohne `DATABASE_URL` bleiben Extraktion, Vorschau und Download nutzbar. Speichern
und Datenbestand zeigen dann einen Konfigurationshinweis.

## Architektur

```text
streamlit_app.py
app_pages/                 Streamlit-Seiten
src/dashboard/integrations Adapter zu den vendorten Tools
src/dashboard/imports/     Datenvertraege, Mapper und Import-Service
src/dashboard/db/          SQLAlchemy-Modelle und Repositories
alembic/                   versionierte PostgreSQL-Migrationen
tools/                     vendorte Fachlogik
tests/                     Root-Tests
```

Streamlit-Seiten schreiben kein SQL. Import-Service und Repository teilen sich
eine Transaktion, sodass ein Fehler keine Teilbestände hinterlässt.

## 1049-Persistenzpfad

```text
ZIP-Upload
-> sichere PDF-Extraktion
-> DataFrame-Vorschau
-> expliziter Speicherbutton
-> import_runs + import_files + lbv_1049_rows
-> Datenbestand
```

Originaldateien werden nicht dauerhaft gespeichert. Die Anwendung persistiert
nur Uploadmetadaten, SHA256 und strukturierte Positionen. Details stehen in
[`docs/data-contracts.md`](docs/data-contracts.md).

## Sliplane

Das Repository enthält eine `railpack.json`. Sie führt Migrationen vor dem
App-Start aus und bindet Streamlit an den von Sliplane gesetzten Port.

Die vollständige Einrichtung von PostgreSQL, privater App und öffentlichem
Basic-Auth-Proxy ist in [`docs/sliplane.md`](docs/sliplane.md) beschrieben.

Keine echten Zugangsdaten in `.env`, `.streamlit/secrets.toml`, Quellcode oder
Logs speichern.

## Qualitaetschecks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest
```

Die Tests der vendorten Werkzeuge werden zusätzlich explizit ausgeführt, da
`tools/` bewusst nicht durch die Root-Konfiguration gesammelt wird.
