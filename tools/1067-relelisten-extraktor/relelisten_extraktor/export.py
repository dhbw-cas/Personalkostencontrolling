from __future__ import annotations

import io
from decimal import Decimal

import pandas as pd

from relelisten_extraktor.models import PayrollRow

EXPORT_COLUMNS = [
    "Buchungsstelle",
    "Abrechnungsmonat/Jahr",
    "Personalnummer",
    "Name",
    "Geburtsdatum",
    "Im Abrechnungsmonat Brutto",
    "Im Abrechnungsmonat Summe Monat",
    "Aufgelaufene Beträge Brutto",
    "Aufgelaufene Beträge Summe Jahr",
    "aus Dokument",
    "Seite",
]

EXCEL_EXPORT_COLUMNS = [
    "Buchungsstelle",
    "Abrechnungsmonat",
    "Abrechnungsjahr",
    "Personalnummer",
    "Name",
    "Geburtsdatum",
    "Im Abrechnungsmonat Brutto",
    "Im Abrechnungsmonat Summe Monat",
    "Aufgelaufene Beträge Brutto",
    "Aufgelaufene Beträge Summe Jahr",
    "aus Dokument",
    "Seite",
]


def rows_to_dataframe(rows: list[PayrollRow]) -> pd.DataFrame:
    records = [
        {
            "Buchungsstelle": row.buchungsstelle,
            "Abrechnungsmonat/Jahr": row.abrechnungsmonat_jahr,
            "Personalnummer": row.personalnummer,
            "Name": row.name,
            "Geburtsdatum": row.geburtsdatum,
            "Im Abrechnungsmonat Brutto": _to_float_or_none(
                row.im_abrechnungsmonat_brutto
            ),
            "Im Abrechnungsmonat Summe Monat": _to_float_or_none(
                row.im_abrechnungsmonat_summe_monat
            ),
            "Aufgelaufene Beträge Brutto": _to_float_or_none(
                row.aufgelaufene_betraege_brutto
            ),
            "Aufgelaufene Beträge Summe Jahr": _to_float_or_none(
                row.aufgelaufene_betraege_summe_jahr
            ),
            "aus Dokument": row.aus_dokument,
            "Seite": row.seite,
        }
        for row in rows
    ]
    return pd.DataFrame(records, columns=EXPORT_COLUMNS)


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    return dataframe.to_csv(index=False, sep=";").encode("utf-8")


def dataframe_to_excel_bytes(dataframe: pd.DataFrame) -> bytes:
    excel_dataframe = _prepare_excel_dataframe(dataframe)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        excel_dataframe.to_excel(writer, index=False, sheet_name="RELE-Daten")
    buffer.seek(0)
    return buffer.getvalue()


def _to_float_or_none(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _prepare_excel_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    excel_dataframe = dataframe.copy()
    month_values: list[str] = []
    year_values: list[str] = []

    for value in excel_dataframe["Abrechnungsmonat/Jahr"].fillna("").astype(str):
        month, year = _split_month_year(value)
        month_values.append(month)
        year_values.append(year)

    excel_dataframe = excel_dataframe.drop(columns=["Abrechnungsmonat/Jahr"])
    excel_dataframe.insert(1, "Abrechnungsmonat", month_values)
    excel_dataframe.insert(2, "Abrechnungsjahr", year_values)
    return excel_dataframe.reindex(columns=EXCEL_EXPORT_COLUMNS)


def _split_month_year(value: str) -> tuple[str, str]:
    normalized = value.strip()
    if not normalized or "-" not in normalized:
        return "", ""

    month, year = normalized.split("-", maxsplit=1)
    return month.strip(), year.strip()
