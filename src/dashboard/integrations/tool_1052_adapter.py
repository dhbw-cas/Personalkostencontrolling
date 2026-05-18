from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from .base import (
    BinaryArtifact,
    ToolIntegrationError,
    ToolKey,
    register_tool_import_paths,
)


@dataclass(slots=True)
class ValidationDetails:
    rows: int
    columns: int
    mapping: dict[str, str]
    preview: pd.DataFrame


def compute_default_booking_dates(
    reference_date: date | None = None,
) -> tuple[date, date]:
    register_tool_import_paths(ToolKey.IMPORT_1052)

    try:
        from buchungsimporteur.transform.processor import DataProcessor  # type: ignore
    except Exception as exc:
        raise ToolIntegrationError(
            "1052-Toolmodul konnte nicht importiert werden."
        ) from exc

    processor = DataProcessor(reference_date=reference_date)
    besoldung = processor.rules.apply_buchungsdatum_by_belegart("Besoldung")
    rest = processor.rules.apply_buchungsdatum_by_belegart("")
    return _parse_ddmmyyyy(besoldung), _parse_ddmmyyyy(rest)


def get_required_source_columns() -> list[str]:
    register_tool_import_paths(ToolKey.IMPORT_1052)

    try:
        from buchungsimporteur.transform.processor import DataProcessor  # type: ignore
    except Exception as exc:
        raise ToolIntegrationError(
            "1052-Toolmodul konnte nicht importiert werden."
        ) from exc

    processor = DataProcessor()
    return processor._get_required_source_columns()


def validate_input_excel(upload_name: str, payload: bytes) -> ValidationDetails:
    register_tool_import_paths(ToolKey.IMPORT_1052)

    try:
        from buchungsimporteur.excel.reader import ExcelReader  # type: ignore
        from buchungsimporteur.transform.processor import DataProcessor  # type: ignore
    except Exception as exc:
        raise ToolIntegrationError(
            "1052-Validierung konnte nicht geladen werden."
        ) from exc

    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        input_path = _write_temp_file(temp_root, upload_name, payload)

        try:
            reader = ExcelReader(input_path)
            dataframe = reader.read_data()
            processor = DataProcessor()
            required = processor._get_required_source_columns()
            reader.validate_required_columns(dataframe, required)
        except Exception as exc:
            raise ToolIntegrationError(f"Validierung fehlgeschlagen: {exc}") from exc

    mapping = dataframe.attrs.get("excel_column_mapping", {})
    return ValidationDetails(
        rows=len(dataframe),
        columns=len(dataframe.columns),
        mapping=mapping,
        preview=dataframe.head(20),
    )


def transform_input_excel(
    upload_name: str,
    payload: bytes,
    output_name: str,
    besoldung_date: date,
    rest_date: date,
) -> BinaryArtifact:
    register_tool_import_paths(ToolKey.IMPORT_1052)

    try:
        from buchungsimporteur.config.schema import create_default_config  # type: ignore  # noqa: I001
        from buchungsimporteur.transform.processor import DataProcessor  # type: ignore
        from buchungsimporteur.transform.processor import ProcessorError  # type: ignore
    except Exception as exc:
        raise ToolIntegrationError(
            "1052-Transformation konnte nicht geladen werden."
        ) from exc

    config = create_default_config().model_copy(deep=True)
    buchungsdatum_column = config.columns["h"]
    buchungsdatum_column.besoldung_date = _to_ddmmyyyy(besoldung_date)
    buchungsdatum_column.default_date = _to_ddmmyyyy(rest_date)
    safe_output_name = _sanitize_filename(
        output_name,
        fallback=f"SAP_LBV_Import_{date.today().strftime('%Y-%m-%d')}.xlsx",
    )

    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        input_path = _write_temp_file(temp_root, upload_name, payload)
        output_path = temp_root / safe_output_name
        processor = DataProcessor(config)
        try:
            processor.process_file(input_path, output_path)
        except ProcessorError as exc:
            raise ToolIntegrationError(f"Transformation fehlgeschlagen: {exc}") from exc
        except Exception as exc:
            raise ToolIntegrationError(f"Unerwarteter Fehler: {exc}") from exc

        output_payload = output_path.read_bytes()

    return BinaryArtifact(
        file_name=safe_output_name,
        payload=output_payload,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _write_temp_file(tmp_dir: Path, name: str, payload: bytes) -> Path:
    safe_name = "".join(c for c in name if c.isalnum() or c in {".", "_", "-"})
    if not safe_name:
        safe_name = "input.xlsx"
    target = tmp_dir / safe_name
    target.write_bytes(payload)
    return target


def _sanitize_filename(name: str, fallback: str) -> str:
    safe_name = "".join(c for c in name if c.isalnum() or c in {".", "_", "-"})
    if not safe_name:
        safe_name = fallback
    if not safe_name.lower().endswith((".xlsx", ".xls")):
        safe_name = f"{safe_name}.xlsx"
    return safe_name


def _to_ddmmyyyy(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _parse_ddmmyyyy(value: str) -> date:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ToolIntegrationError(f"Ungültiges Datumsformat: {value}") from exc
