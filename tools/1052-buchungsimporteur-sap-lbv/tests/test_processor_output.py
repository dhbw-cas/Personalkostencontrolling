"""Tests fuer die Aufbereitung der Excel-Ausgabeblaetter."""

import pandas as pd

from buchungsimporteur.config.schema import create_default_config
from buchungsimporteur.transform.processor import DataProcessor


def test_build_output_sheets_keeps_daily_payday_in_main_sheet() -> None:
    """Sonderfall 'Taeglicher Zahltag' bleibt im Hauptblatt."""
    processor = DataProcessor(create_default_config())
    target_df = pd.DataFrame(
        {
            "Belegkopftext": [
                "Sonstiges: Täglicher Zahltag",
                "Sonstiges: Täglicher Zahltag",
                "Sonstiges: Irgendein Fall",
                "Sonstiges: Irgendein Fall",
                "Vergütung",
                "Vergütung",
            ],
            "Belegnummer": ["X1", "X2", "X3", "X4", "X5", "X6"],
            "GrpId": ["99", "99", "98", "98", "97", "97"],
            "Zeile": ["10", "11", "12", "13", "14", "15"],
        }
    )

    main_df, extra_sheets = processor._build_output_sheets(target_df)

    assert "Sonstiges" in extra_sheets
    sonstiges_df = extra_sheets["Sonstiges"]

    assert main_df["Belegkopftext"].tolist() == [
        "Sonstiges: Täglicher Zahltag",
        "Sonstiges: Täglicher Zahltag",
        "Vergütung",
        "Vergütung",
    ]
    assert sonstiges_df["Belegkopftext"].tolist() == [
        "Sonstiges: Irgendein Fall",
        "Sonstiges: Irgendein Fall",
    ]


def test_prepare_sheet_dataframe_resets_numbering_per_sheet() -> None:
    """Pro Blatt starten Belegnummer/GrpId/Zeile neu."""
    processor = DataProcessor(create_default_config())
    df = pd.DataFrame(
        {
            "Belegnummer": ["A", "B", "C", "D"],
            "GrpId": ["5", "5", "6", "6"],
            "Zeile": ["9", "10", "11", "12"],
        }
    )

    prepared = processor._prepare_sheet_dataframe(df)

    assert prepared["Belegnummer"].tolist() == ["", "", "", ""]
    assert prepared["GrpId"].tolist() == ["1", "1", "2", "2"]
    assert prepared["Zeile"].tolist() == ["1", "2", "3", "4"]


def test_build_output_sheets_handles_truncated_daily_payday_text() -> None:
    """Gekuerzter Belegkopftext fuer taeglichen Zahltag bleibt im Hauptblatt."""
    processor = DataProcessor(create_default_config())
    target_df = pd.DataFrame(
        {
            "Belegkopftext": [
                "Sonstiges. Täglicher Zahl",
                "Sonstiges. Täglicher Zahl",
                "Sonstiges: Sonstiger Fall",
                "Sonstiges: Sonstiger Fall",
            ],
            "Belegnummer": ["A", "B", "C", "D"],
            "GrpId": ["1", "1", "2", "2"],
            "Zeile": ["1", "2", "3", "4"],
        }
    )

    main_df, extra_sheets = processor._build_output_sheets(target_df)

    assert main_df["Belegkopftext"].tolist() == [
        "Sonstiges. Täglicher Zahl",
        "Sonstiges. Täglicher Zahl",
    ]
    assert extra_sheets["Sonstiges"]["Belegkopftext"].tolist() == [
        "Sonstiges: Sonstiger Fall",
        "Sonstiges: Sonstiger Fall",
    ]
