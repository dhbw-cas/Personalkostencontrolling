from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pandas as pd

from relelisten_extraktor.export import (
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    rows_to_dataframe,
)
from relelisten_extraktor.models import PayrollRow


def _sample_row() -> PayrollRow:
    return PayrollRow(
        buchungsstelle="7001",
        abrechnungsmonat_jahr="10-2025",
        personalnummer="51237803/426R",
        name="GRILL JOACHIM PROF.DR.",
        geburtsdatum="",
        im_abrechnungsmonat_brutto=Decimal("8120.52"),
        im_abrechnungsmonat_summe_monat=Decimal("10030.05"),
        aufgelaufene_betraege_brutto=Decimal("81712.81"),
        aufgelaufene_betraege_summe_jahr=Decimal("100784.80"),
        aus_dokument="test_verguetung.pdf",
        seite=1,
    )


def test_csv_export_keeps_combined_month_year_column() -> None:
    dataframe = rows_to_dataframe([_sample_row()])

    csv_content = dataframe_to_csv_bytes(dataframe).decode("utf-8")

    assert "Abrechnungsmonat/Jahr" in csv_content.splitlines()[0]


def test_excel_export_splits_month_and_year_columns() -> None:
    dataframe = rows_to_dataframe([_sample_row()])

    excel_content = dataframe_to_excel_bytes(dataframe)
    exported = pd.read_excel(BytesIO(excel_content), sheet_name="RELE-Daten")

    assert "Abrechnungsmonat/Jahr" not in exported.columns
    assert "Abrechnungsmonat" in exported.columns
    assert "Abrechnungsjahr" in exported.columns
    assert str(exported.loc[0, "Abrechnungsmonat"]) == "10"
    assert str(exported.loc[0, "Abrechnungsjahr"]) == "2025"
