from __future__ import annotations

from dashboard.state import (
    KEY_1049_DATAFRAME,
    KEY_1049_EXPORT_BYTES,
    KEY_1049_EXPORT_NAME,
    KEY_1049_FILE_METADATA,
    KEY_1049_IMPORT_ID,
    KEY_1049_UPLOAD_SIGNATURE,
    KEY_1052_BESOLDUNG_DATE,
    KEY_1052_OUTPUT_BYTES,
    KEY_1052_OUTPUT_NAME,
    KEY_1052_REST_DATE,
    KEY_1052_TRANSFORM_ERROR,
    KEY_1052_UPLOAD_SIGNATURE,
    KEY_1052_VALIDATION,
    KEY_1052_VALIDATION_ERROR,
    KEY_1067_CSV_BYTES,
    KEY_1067_CSV_NAME,
    KEY_1067_DATAFRAME,
    KEY_1067_XLSX_BYTES,
    KEY_1067_XLSX_NAME,
    clear_1049_result,
    init_state,
)

STATE_KEYS = [
    KEY_1049_DATAFRAME,
    KEY_1049_EXPORT_BYTES,
    KEY_1049_EXPORT_NAME,
    KEY_1049_FILE_METADATA,
    KEY_1049_IMPORT_ID,
    KEY_1049_UPLOAD_SIGNATURE,
    KEY_1067_DATAFRAME,
    KEY_1067_CSV_BYTES,
    KEY_1067_XLSX_BYTES,
    KEY_1067_CSV_NAME,
    KEY_1067_XLSX_NAME,
    KEY_1052_UPLOAD_SIGNATURE,
    KEY_1052_VALIDATION,
    KEY_1052_VALIDATION_ERROR,
    KEY_1052_TRANSFORM_ERROR,
    KEY_1052_OUTPUT_BYTES,
    KEY_1052_OUTPUT_NAME,
    KEY_1052_BESOLDUNG_DATE,
    KEY_1052_REST_DATE,
]


def test_init_state_sets_defaults() -> None:
    store: dict[str, object] = {}

    init_state(store)

    for state_key in STATE_KEYS:
        assert state_key in store
        assert store[state_key] is None


def test_init_state_preserves_existing_values() -> None:
    store: dict[str, object] = {KEY_1049_EXPORT_NAME: "test.xlsx"}

    init_state(store)

    assert store[KEY_1049_EXPORT_NAME] == "test.xlsx"


def test_clear_1049_result_preserves_other_tools() -> None:
    store: dict[str, object] = {
        KEY_1049_DATAFRAME: "data",
        KEY_1049_IMPORT_ID: "id",
        KEY_1067_DATAFRAME: "rele-data",
    }

    clear_1049_result(store)

    assert store[KEY_1049_DATAFRAME] is None
    assert store[KEY_1049_IMPORT_ID] is None
    assert store[KEY_1067_DATAFRAME] == "rele-data"
