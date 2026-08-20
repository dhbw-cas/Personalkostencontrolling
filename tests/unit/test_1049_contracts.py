from __future__ import annotations

import pandas as pd
import pytest

from dashboard.imports.contracts import (
    EXPECTED_1049_COLUMNS,
    DataContractError,
    ImportFileMetadata,
    validate_1049_dataframe_contract,
)


def test_file_metadata_uses_original_payload() -> None:
    metadata = ImportFileMetadata.from_payload(" rechnung.zip ", b"payload")

    assert metadata.original_filename == "rechnung.zip"
    assert metadata.file_size == 7
    assert metadata.sha256 == (
        "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"
    )


def test_1049_contract_accepts_exact_columns() -> None:
    dataframe = pd.DataFrame(
        [["Position", 12.34, "Ort", "01.08.2026", "a.pdf", "7002", "", 8]],
        columns=EXPECTED_1049_COLUMNS,
    )

    validate_1049_dataframe_contract(dataframe)


def test_1049_contract_rejects_changed_column_order() -> None:
    dataframe = pd.DataFrame(
        [[12.34, "Position", "Ort", "01.08.2026", "a.pdf", "7002", "", 8]],
        columns=(EXPECTED_1049_COLUMNS[1], EXPECTED_1049_COLUMNS[0])
        + EXPECTED_1049_COLUMNS[2:],
    )

    with pytest.raises(DataContractError, match="Unerwartete 1049-Spalten"):
        validate_1049_dataframe_contract(dataframe)


def test_1049_contract_rejects_empty_dataframe() -> None:
    dataframe = pd.DataFrame(columns=EXPECTED_1049_COLUMNS)

    with pytest.raises(DataContractError, match="keine Positionen"):
        validate_1049_dataframe_contract(dataframe)
