from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from numbers import Integral, Real
from typing import Any

import pandas as pd

from .contracts import DataContractError, validate_1049_dataframe_contract

MAX_NUMERIC_18_2_ABS = Decimal("10000000000000000")


@dataclass(slots=True, frozen=True)
class Lbv1049Record:
    row_number: int
    position: str
    betrag: Decimal
    standort: str
    datum_anschreiben: date | None
    quelldatei: str
    abrechnungsstelle: str
    verwendungszweck: str
    buchungsperiode: int | None


def map_1049_dataframe(dataframe: pd.DataFrame) -> list[Lbv1049Record]:
    validate_1049_dataframe_contract(dataframe)
    records: list[Lbv1049Record] = []
    for row_number, row in enumerate(dataframe.to_dict(orient="records"), start=1):
        records.append(
            Lbv1049Record(
                row_number=row_number,
                position=_text(row["Position"], "Position", required=True),
                betrag=_amount(row["Betrag (€)"]),
                standort=_text(row["Standort"], "Standort"),
                datum_anschreiben=_date(row["Datum des Anschreibens"]),
                quelldatei=_text(row["Quelldatei"], "Quelldatei", required=True),
                abrechnungsstelle=_text(row["Abrechnungsstelle"], "Abrechnungsstelle"),
                verwendungszweck=_text(row["Verwendungszweck"], "Verwendungszweck"),
                buchungsperiode=_month(row["Buchungsperiode"]),
            )
        )
    return records


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    result = pd.isna(value)
    try:
        return bool(result)
    except ValueError:
        return False


def _text(value: Any, field_name: str, *, required: bool = False) -> str:
    text = "" if _is_missing(value) else str(value).strip()
    if required and not text:
        raise DataContractError(f"{field_name} darf nicht leer sein.")
    return text


def _amount(value: Any) -> Decimal:
    if _is_missing(value) or isinstance(value, bool):
        raise DataContractError("Betrag (€) muss eine gueltige Zahl sein.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DataContractError("Betrag (€) muss eine gueltige Zahl sein.") from exc
    exponent = amount.as_tuple().exponent
    if not amount.is_finite() or not isinstance(exponent, int) or exponent < -2:
        raise DataContractError("Betrag (€) darf maximal zwei Nachkommastellen haben.")
    if abs(amount) >= MAX_NUMERIC_18_2_ABS:
        raise DataContractError("Betrag (€) ist zu gross fuer NUMERIC(18,2).")
    try:
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise DataContractError("Betrag (€) ist ungueltig.") from exc


def _date(value: Any) -> date | None:
    if _is_missing(value) or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%d.%m.%Y").date()
    except ValueError as exc:
        raise DataContractError(
            "Datum des Anschreibens muss im Format TT.MM.JJJJ vorliegen."
        ) from exc


def _month(value: Any) -> int | None:
    if _is_missing(value) or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        raise DataContractError("Buchungsperiode muss ein Monat von 1 bis 12 sein.")
    if isinstance(value, Integral):
        month = int(value)
    elif isinstance(value, Real) and float(value).is_integer():
        month = int(float(value))
    else:
        raise DataContractError("Buchungsperiode muss ein Monat von 1 bis 12 sein.")
    if not 1 <= month <= 12:
        raise DataContractError("Buchungsperiode muss ein Monat von 1 bis 12 sein.")
    return month
