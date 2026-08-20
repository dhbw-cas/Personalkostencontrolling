from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from dashboard.imports.contracts import EXPECTED_1049_COLUMNS, DataContractError
from dashboard.imports.mapper_1049 import map_1049_dataframe


def _dataframe(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "Position": "Verguetung",
        "Betrag (€)": 1234.5,
        "Standort": "Stuttgart",
        "Datum des Anschreibens": "20.08.2026",
        "Quelldatei": "7002 08-2026A+09-2026B.pdf",
        "Abrechnungsstelle": "7002",
        "Verwendungszweck": "Referenz",
        "Buchungsperiode": 8.0,
    }
    row.update(overrides)
    return pd.DataFrame([row], columns=EXPECTED_1049_COLUMNS)


def test_map_1049_dataframe_normalizes_types() -> None:
    record = map_1049_dataframe(_dataframe())[0]

    assert record.row_number == 1
    assert record.betrag == Decimal("1234.50")
    assert record.datum_anschreiben == date(2026, 8, 20)
    assert record.buchungsperiode == 8


def test_map_1049_dataframe_accepts_missing_optional_values() -> None:
    record = map_1049_dataframe(
        _dataframe(
            **{
                "Datum des Anschreibens": None,
                "Standort": None,
                "Buchungsperiode": None,
            }
        )
    )[0]

    assert record.datum_anschreiben is None
    assert record.standort == ""
    assert record.buchungsperiode is None


@pytest.mark.parametrize(
    "amount",
    [None, float("nan"), 1.234, "ungueltig", "123456789012345678901234567890"],
)
def test_map_1049_dataframe_rejects_invalid_amount(amount: object) -> None:
    with pytest.raises(DataContractError, match="Betrag"):
        map_1049_dataframe(_dataframe(**{"Betrag (€)": amount}))


@pytest.mark.parametrize("month", [0, 13, 1.5, "8"])
def test_map_1049_dataframe_rejects_invalid_month(month: object) -> None:
    with pytest.raises(DataContractError, match="Buchungsperiode"):
        map_1049_dataframe(_dataframe(Buchungsperiode=month))


def test_map_1049_dataframe_rejects_invalid_date() -> None:
    with pytest.raises(DataContractError, match="TT.MM.JJJJ"):
        map_1049_dataframe(_dataframe(**{"Datum des Anschreibens": "31.02.2026"}))
