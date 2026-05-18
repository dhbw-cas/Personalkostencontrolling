"""Tests fuer numerische Excel-Ausgabeformate."""

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from buchungsimporteur.excel.writer import ExcelWriter


def test_writer_exports_amount_cells_as_numeric_values(tmp_path: Path) -> None:
    """Betragsspalten werden als echte Zahlenzellen gespeichert."""
    output_path = tmp_path / "export.xlsx"
    writer = ExcelWriter(output_path)
    df = pd.DataFrame(
        {
            "Betrag Hausw": ["1.234,50"],
            "Steuerbetrag": [""],
            "Position": ["1"],
            "Zeile": ["2"],
        }
    )

    writer.write_data(df)

    workbook = load_workbook(output_path)
    worksheet = workbook["Buchungsdaten"]

    assert worksheet["A2"].data_type == "n"
    assert worksheet["A2"].value == 1234.5
    assert worksheet["A2"].number_format == "#,##0.00"
    assert worksheet["C2"].data_type == "n"
    assert worksheet["C2"].value == 1
    assert worksheet["D2"].data_type == "n"
    assert worksheet["D2"].value == 2
