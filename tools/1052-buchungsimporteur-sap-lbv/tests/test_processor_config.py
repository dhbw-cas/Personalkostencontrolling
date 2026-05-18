"""Tests für Processor-spezifische Konfiguration."""

from datetime import date

import pandas as pd

from buchungsimporteur.config.schema import ColumnType, create_default_config
from buchungsimporteur.excel.writer import create_sap_template_columns
from buchungsimporteur.transform.processor import DataProcessor


def test_required_source_columns_cover_plan() -> None:
    """Stellt sicher, dass alle benötigten Quelldaten-Spalten ermittelt werden."""
    processor = DataProcessor(create_default_config())

    assert processor._get_required_source_columns() == ["A", "B", "D", "F", "G"]


def test_buchungsdatum_rule_in_processor_uses_dynamic_plan_logic() -> None:
    """Spalte h nutzt dynamische Monatslogik aus den Rules, wenn keine Fixdaten gesetzt sind."""
    processor = DataProcessor(create_default_config(), reference_date=date(2025, 7, 5))
    source_df = pd.DataFrame({"Belegkopftext": ["Vergütung", "Monatliche Besoldung"]})
    source_df.attrs["excel_column_mapping"] = {"A": "Belegkopftext"}

    column_config = processor.config.columns["h"]

    assert (
        processor._calculate_computed_value(source_df, 0, column_config, {})
        == "30.06.2025"
    )
    assert (
        processor._calculate_computed_value(source_df, 1, column_config, {})
        == "01.07.2025"
    )


def test_template_columns_insert_empty_buchungsperiode_after_buchungsdatum() -> None:
    """Das SAP-Template enthält Buchungsperiode direkt nach Buchungsdatum."""
    columns = create_sap_template_columns()

    assert "Buchungsperiode" in columns
    assert columns.index("Buchungsperiode") == columns.index("Buchungsdatum") + 1
    assert columns.index("Referenz") == columns.index("Buchungsperiode") + 1


def test_default_config_inserts_buchungsperiode_at_i_and_shifts_following_columns() -> (
    None
):
    """Standard-Konfiguration fügt Buchungsperiode als leere Spalte i ein."""
    config = create_default_config()

    assert config.columns["i"].title == "Buchungsperiode"
    assert config.columns["i"].column_type == ColumnType.EMPTY
    assert config.columns["j"].title == "Referenz"
    assert config.columns["al"].title == "Informationen"


def test_transform_data_keeps_output_buchungsperiode_empty() -> None:
    """Buchungsperiode bleibt in der Ausgabe leer, Referenz bleibt aus Quelle F."""
    processor = DataProcessor(create_default_config(), reference_date=date(2025, 11, 3))
    source_df = pd.DataFrame(
        {
            "Belegkopftext": ["Vergütung"],
            "Betrag": [123.45],
            "Rechnungsdatum": ["03.11.2025"],
            "Referenz/Zuordnung": ["7001"],
            "Text": ["Erst.: 10/2025 A + 11/2025 B"],
        }
    )
    source_df.attrs["excel_column_mapping"] = {
        "A": "Belegkopftext",
        "B": "Betrag",
        "D": "Rechnungsdatum",
        "F": "Referenz/Zuordnung",
        "G": "Text",
    }

    result_df = processor.transform_data(source_df)

    assert result_df["Buchungsperiode"].tolist() == ["", ""]
    assert result_df["Referenz"].tolist() == ["7001", "7001"]


def test_transform_data_derives_geschaeftsjahr_from_effective_buchungsdatum() -> None:
    """Geschäftsjahr folgt dem je Zeile wirksamen Buchungsdatum."""
    processor = DataProcessor(create_default_config(), reference_date=date(2026, 1, 10))
    source_df = pd.DataFrame(
        {
            "Belegkopftext": ["Vergütung", "Monatliche Besoldung"],
            "Betrag": [123.45, 234.56],
            "Rechnungsdatum": ["10.01.2026", "10.01.2026"],
            "Referenz/Zuordnung": ["7001", "7002"],
            "Text": ["Restzahlung", "Besoldung"],
        }
    )
    source_df.attrs["excel_column_mapping"] = {
        "A": "Belegkopftext",
        "B": "Betrag",
        "D": "Rechnungsdatum",
        "F": "Referenz/Zuordnung",
        "G": "Text",
    }

    result_df = processor.transform_data(source_df)

    assert result_df["Geschäftsjahr"].tolist() == ["2025", "2025", "2026", "2026"]
