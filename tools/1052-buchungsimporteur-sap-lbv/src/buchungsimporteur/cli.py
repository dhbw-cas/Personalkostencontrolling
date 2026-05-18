"""Command Line Interface für den SAP LBV Buchungsimporteur."""

import json
import logging
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config.schema import TransformationConfig
from .transform.processor import DataProcessor, ProcessorError

# Setup Rich Console
console = Console()
app = typer.Typer(
    name="buchungsimporteur",
    help="SAP LBV Buchungsimporteur - Excel zu Excel Transformation",
    add_completion=False,
)


def setup_logging(verbose: bool = False) -> None:
    """Richtet Logging mit Rich-Formatierung ein."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def transform(
    input_file: Path = typer.Argument(
        ...,
        help="Pfad zur Quell-Excel-Datei",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output_file: Path = typer.Argument(..., help="Pfad für die Ziel-Excel-Datei"),
    config_file: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur JSON-Konfigurationsdatei (optional)",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Ausführliche Ausgabe aktivieren"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Überschreibe Zieldatei ohne Nachfrage"
    ),
) -> None:
    """Transformiert Excel-Quelldaten in SAP LBV Buchungsformat.

    Beispiele:

        buchungsimporteur input.xlsx output.xlsx

        buchungsimporteur input.xlsx output.xlsx --config custom_config.json

        buchungsimporteur input.xlsx output.xlsx --verbose --force
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        # Validiere Eingaben
        if input_file.suffix.lower() not in [".xlsx", ".xls"]:
            rprint(f"[red]❌ Ungültiges Eingabedateiformat: {input_file.suffix}")
            raise typer.Exit(1)

        if output_file.suffix.lower() not in [".xlsx", ".xls"]:
            rprint(f"[red]❌ Ungültiges Ausgabedateiformat: {output_file.suffix}")
            raise typer.Exit(1)

        # Überprüfe ob Zieldatei existiert
        if output_file.exists() and not force:
            overwrite = typer.confirm(
                f"Datei '{output_file}' existiert bereits. Überschreiben?"
            )
            if not overwrite:
                rprint("[yellow]⏹️  Abgebrochen.")
                raise typer.Exit(0)

        # Lade Konfiguration
        config = None
        if config_file:
            rprint(f"[blue]📝 Lade Konfiguration: {config_file}")
            try:
                with config_file.open("r", encoding="utf-8") as f:
                    config_data = json.load(f)
                config = TransformationConfig(**config_data)
                logger.info(f"Konfiguration geladen: {config.name}")
            except Exception as e:
                rprint(f"[red]❌ Fehler beim Laden der Konfiguration: {e}")
                raise typer.Exit(1)

        # Starte Transformation mit Progress-Anzeige
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Initialisiere Processor
            task = progress.add_task("Initialisiere Processor...", total=None)
            processor = DataProcessor(config)

            # Verarbeite Datei
            progress.update(task, description=f"Verarbeite {input_file.name}...")
            processor.process_file(input_file, output_file)

            progress.update(task, description="✅ Transformation abgeschlossen")

        # Erfolg melden
        rprint("[green]✅ Transformation erfolgreich abgeschlossen!")
        rprint(f"[green]📄 Eingabe: {input_file}")
        rprint(f"[green]📄 Ausgabe: {output_file}")

        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            rprint(f"[green]📊 Dateigröße: {size_mb:.2f} MB")

    except ProcessorError as e:
        rprint(f"[red]❌ Transformationsfehler: {e}")
        logger.error(f"Processor Error: {e}")
        raise typer.Exit(1)

    except Exception as e:
        rprint(f"[red]❌ Unerwarteter Fehler: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise typer.Exit(1)


@app.command()
def validate(
    input_file: Path = typer.Argument(
        ...,
        help="Pfad zur zu validierenden Excel-Datei",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    config_file: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Pfad zur JSON-Konfigurationsdatei (optional)",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Ausführliche Ausgabe aktivieren"
    ),
) -> None:
    """Validiert eine Excel-Datei gegen die Konfigurationsanforderungen."""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        from .config.schema import create_default_config
        from .excel.reader import ExcelReader

        # Lade Konfiguration
        config = None
        if config_file:
            with config_file.open("r", encoding="utf-8") as f:
                config_data = json.load(f)
            config = TransformationConfig(**config_data)
        else:
            config = create_default_config()

        rprint(f"[blue]🔍 Validiere {input_file.name}...")

        # Lese und validiere Datei
        reader = ExcelReader(input_file)
        df = reader.read_data()

        # Ermittle benötigte Spalten
        processor = DataProcessor(config)
        required_columns = processor._get_required_source_columns()

        # Validiere Spalten
        reader.validate_required_columns(df, required_columns)

        rprint("[green]✅ Datei ist gültig!")
        rprint(f"[green]📊 {len(df)} Zeilen, {len(df.columns)} Spalten")
        rprint(f"[green]📝 Benötigte Spalten vorhanden: {required_columns}")

        if "excel_column_mapping" in df.attrs:
            mapping = df.attrs["excel_column_mapping"]
            rprint(f"[blue]🗂️  Verfügbare Excel-Spalten: {list(mapping.keys())}")

    except Exception as e:
        rprint(f"[red]❌ Validierungsfehler: {e}")
        logger.error(f"Validation error: {e}")
        raise typer.Exit(1)


@app.command()
def create_config(
    output_file: Path = typer.Argument(
        "config.json", help="Pfad für die zu erstellende Konfigurationsdatei"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Überschreibe existierende Datei ohne Nachfrage"
    ),
) -> None:
    """Erstellt eine Standard-Konfigurationsdatei."""

    try:
        if output_file.exists() and not force:
            overwrite = typer.confirm(
                f"Datei '{output_file}' existiert bereits. Überschreiben?"
            )
            if not overwrite:
                rprint("[yellow]⏹️  Abgebrochen.")
                raise typer.Exit(0)

        from .config.schema import create_default_config

        # Erstelle Standard-Konfiguration
        config = create_default_config()

        # Schreibe als JSON
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)

        rprint(f"[green]✅ Konfiguration erstellt: {output_file}")
        rprint("[blue]📝 Sie können diese Datei anpassen und mit --config verwenden")

    except Exception as e:
        rprint(f"[red]❌ Fehler beim Erstellen der Konfiguration: {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Zeigt die Version des Buchungsimporteurs an."""
    from . import __version__

    rprint(f"[blue]SAP LBV Buchungsimporteur v{__version__}")


if __name__ == "__main__":
    app()
