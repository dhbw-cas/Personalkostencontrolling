from __future__ import annotations

from typing import Any

KEY_1049_DATAFRAME = "tool_1049_dataframe"
KEY_1049_EXPORT_BYTES = "tool_1049_export_bytes"
KEY_1049_EXPORT_NAME = "tool_1049_export_name"
KEY_1049_FILE_METADATA = "tool_1049_file_metadata"
KEY_1049_IMPORT_ID = "tool_1049_import_id"
KEY_1049_UPLOAD_SIGNATURE = "tool_1049_upload_signature"

KEY_1067_DATAFRAME = "tool_1067_dataframe"
KEY_1067_CSV_BYTES = "tool_1067_csv_bytes"
KEY_1067_XLSX_BYTES = "tool_1067_xlsx_bytes"
KEY_1067_CSV_NAME = "tool_1067_csv_name"
KEY_1067_XLSX_NAME = "tool_1067_xlsx_name"

KEY_1052_UPLOAD_SIGNATURE = "tool_1052_upload_signature"
KEY_1052_VALIDATION = "tool_1052_validation"
KEY_1052_VALIDATION_ERROR = "tool_1052_validation_error"
KEY_1052_TRANSFORM_ERROR = "tool_1052_transform_error"
KEY_1052_OUTPUT_BYTES = "tool_1052_output_bytes"
KEY_1052_OUTPUT_NAME = "tool_1052_output_name"
KEY_1052_BESOLDUNG_DATE = "tool_1052_besoldung_date"
KEY_1052_REST_DATE = "tool_1052_rest_date"

_DEFAULTS: dict[str, Any] = {
    KEY_1049_DATAFRAME: None,
    KEY_1049_EXPORT_BYTES: None,
    KEY_1049_EXPORT_NAME: None,
    KEY_1049_FILE_METADATA: None,
    KEY_1049_IMPORT_ID: None,
    KEY_1049_UPLOAD_SIGNATURE: None,
    KEY_1067_DATAFRAME: None,
    KEY_1067_CSV_BYTES: None,
    KEY_1067_XLSX_BYTES: None,
    KEY_1067_CSV_NAME: None,
    KEY_1067_XLSX_NAME: None,
    KEY_1052_UPLOAD_SIGNATURE: None,
    KEY_1052_VALIDATION: None,
    KEY_1052_VALIDATION_ERROR: None,
    KEY_1052_TRANSFORM_ERROR: None,
    KEY_1052_OUTPUT_BYTES: None,
    KEY_1052_OUTPUT_NAME: None,
    KEY_1052_BESOLDUNG_DATE: None,
    KEY_1052_REST_DATE: None,
}


def init_state(store: Any) -> None:
    for key, default_value in _DEFAULTS.items():
        store.setdefault(key, default_value)


def clear_1049_result(store: Any) -> None:
    for key in (
        KEY_1049_DATAFRAME,
        KEY_1049_EXPORT_BYTES,
        KEY_1049_EXPORT_NAME,
        KEY_1049_FILE_METADATA,
        KEY_1049_IMPORT_ID,
        KEY_1049_UPLOAD_SIGNATURE,
    ):
        store[key] = None
