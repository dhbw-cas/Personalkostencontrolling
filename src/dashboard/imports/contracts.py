from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd

SOURCE_TYPE_1049 = "lbv_1049"

EXPECTED_1049_COLUMNS = (
    "Position",
    "Betrag (€)",
    "Standort",
    "Datum des Anschreibens",
    "Quelldatei",
    "Abrechnungsstelle",
    "Verwendungszweck",
    "Buchungsperiode",
)


class DataContractError(ValueError):
    """Die strukturierten Importdaten entsprechen nicht dem Datenvertrag."""


@dataclass(slots=True, frozen=True)
class ImportFileMetadata:
    original_filename: str
    sha256: str
    file_size: int

    @classmethod
    def from_payload(cls, original_filename: str, payload: bytes) -> ImportFileMetadata:
        filename = original_filename.strip()
        if not filename:
            raise DataContractError("Der Originaldateiname fehlt.")
        return cls(
            original_filename=filename,
            sha256=hashlib.sha256(payload).hexdigest(),
            file_size=len(payload),
        )


def validate_1049_dataframe_contract(dataframe: pd.DataFrame) -> None:
    actual_columns = tuple(str(column) for column in dataframe.columns)
    if actual_columns != EXPECTED_1049_COLUMNS:
        expected = ", ".join(EXPECTED_1049_COLUMNS)
        actual = ", ".join(actual_columns) or "keine"
        raise DataContractError(
            f"Unerwartete 1049-Spalten. Erwartet: {expected}. Vorhanden: {actual}."
        )
    if dataframe.empty:
        raise DataContractError("Der 1049-Import enthaelt keine Positionen.")
