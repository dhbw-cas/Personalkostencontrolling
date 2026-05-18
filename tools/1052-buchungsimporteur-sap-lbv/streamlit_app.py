from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import streamlit as st
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists():
    # Ensure src layout is importable when running as a script.
    import sys

    sys.path.insert(0, str(SRC))

from buchungsimporteur.config.schema import (  # noqa: E402
    TransformationConfig,
    create_default_config,
)
from buchungsimporteur.excel.reader import ExcelReader  # noqa: E402
from buchungsimporteur.transform.processor import (  # noqa: E402
    DataProcessor,
    ProcessorError,
)


def _load_config(uploaded: Any | None) -> TransformationConfig | None:
    if uploaded is None:
        return None

    try:
        config_text = uploaded.getvalue().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Die Konfigurationsdatei muss UTF-8 kodiert sein.") from exc

    try:
        config_data = json.loads(config_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Die Konfigurationsdatei ist kein gültiges JSON.") from exc

    try:
        return TransformationConfig(**config_data)
    except ValidationError as exc:
        raise ValueError(f"Konfigurationsvalidierung fehlgeschlagen: {exc}") from exc


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


def _run_validation(input_path: Path, config: TransformationConfig | None) -> dict[str, Any]:
    reader = ExcelReader(input_path)
    df = reader.read_data()
    processor = DataProcessor(config)
    required_columns = processor._get_required_source_columns()
    reader.validate_required_columns(df, required_columns)
    mapping = df.attrs.get("excel_column_mapping", {})
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "mapping": mapping,
        "preview": df.head(20),
    }


def _run_transform(
    input_path: Path,
    output_name: str,
    config: TransformationConfig | None,
) -> bytes:
    processor = DataProcessor(config)
    output_path = input_path.parent / output_name
    processor.process_file(input_path, output_path)
    return output_path.read_bytes()


def _to_ddmmyyyy(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _parse_ddmmyyyy(value: str) -> date:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError(f"Ungültiges Datumsformat: {value}") from exc


def _compute_buchungsdatum_defaults(
    config: TransformationConfig | None,
    reference_date: date | None = None,
) -> tuple[date, date]:
    processor = DataProcessor(config, reference_date=reference_date)
    besoldung_value = processor.rules.apply_buchungsdatum_by_belegart("Besoldung")
    rest_value = processor.rules.apply_buchungsdatum_by_belegart("")
    return _parse_ddmmyyyy(besoldung_value), _parse_ddmmyyyy(rest_value)


def _build_runtime_config_with_dates(
    base_config: TransformationConfig | None,
    besoldung_date: date,
    rest_date: date,
) -> TransformationConfig:
    config = (base_config or create_default_config()).model_copy(deep=True)
    buchungsdatum_column = config.columns["h"]
    buchungsdatum_column.besoldung_date = _to_ddmmyyyy(besoldung_date)
    buchungsdatum_column.default_date = _to_ddmmyyyy(rest_date)
    return config


def _default_config_payload() -> bytes:
    config = create_default_config()
    data = json.dumps(config.model_dump(), indent=2, ensure_ascii=False)
    return data.encode("utf-8")


def _get_required_columns(config: TransformationConfig | None) -> list[str]:
    processor = DataProcessor(config)
    return processor._get_required_source_columns()


def main() -> None:
    st.set_page_config(
        page_title="SAP LBV Buchungsimporteur",
        page_icon="📄",
        layout="wide",
    )

    st.title("SAP LBV Buchungsimporteur")
    st.write(
        "Transformiert Excel-Eingabedateien in das SAP-LBV-Zielformat, optional mit"
        " JSON-Konfiguration."
    )

    left, right = st.columns([0.52, 0.48])

    with left:
        st.subheader("Eingaben")
        input_file = st.file_uploader("Eingabe-Excel", type=["xlsx", "xls"])

        # st.subheader("Konfiguration (optional)")
        # config_upload = st.file_uploader("JSON-Konfiguration", type=["json"])
        # st.download_button(
        #     "Standard-Konfiguration herunterladen",
        #     data=_default_config_payload(),
        #     file_name="config.json",
        #     mime="application/json",
        # )

        if input_file is None:
            st.info("Bitte eine Excel-Datei hochladen, um zu starten.")
            return

        input_payload = input_file.getvalue()
        upload_signature = (
            input_file.name,
            len(input_payload),
            hashlib.sha256(input_payload).hexdigest(),
        )

        if st.session_state.get("uploaded_file_signature") != upload_signature:
            default_besoldung, default_rest = _compute_buchungsdatum_defaults(config=None)
            st.session_state["uploaded_file_signature"] = upload_signature
            st.session_state["buchungsdatum_besoldung"] = default_besoldung
            st.session_state["buchungsdatum_rest"] = default_rest
            st.session_state.pop("validation_details", None)
            st.session_state.pop("validation_error", None)
            st.session_state.pop("output_bytes", None)
            st.session_state.pop("output_name", None)
            st.session_state.pop("transform_error", None)

        today_str = date.today().strftime("%Y-%m-%d")
        default_output = f"SAP_LBV_Import_{today_str}.xlsx"

        config = None

        required_columns = _get_required_columns(config)
        default_labels = create_default_config().source_columns
        label_map = (config or create_default_config()).source_columns
        with st.expander("Pflichtspalten (Excel)", expanded=True):
            st.write(
                "Die folgenden Excel-Spalten werden für die Transformation benötigt:"
            )
            for col in required_columns:
                label = label_map.get(col) or default_labels.get(col, "")
                if label:
                    st.write(f"- {col} ({label})")
                else:
                    st.write(f"- {col}")

        if st.button("Eingabe prüfen", use_container_width=True):
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                input_path = _write_temp_file(tmp_path, input_file.name, input_payload)
                try:
                    details = _run_validation(input_path, config)
                except Exception as exc:
                    st.session_state["validation_error"] = str(exc)
                    st.session_state.pop("validation_details", None)
                else:
                    st.session_state["validation_details"] = details
                    st.session_state.pop("validation_error", None)

        if validation_error := st.session_state.get("validation_error"):
            st.error(f"Validierung fehlgeschlagen: {validation_error}")

        validation_details = st.session_state.get("validation_details")
        if validation_details:
            st.success("Validierung erfolgreich")
            st.write(
                f"Zeilen: {validation_details['rows']} | Spalten: {validation_details['columns']}"
            )
            with st.expander("Details zur Eingabeprüfung", expanded=False):
                if validation_details["mapping"]:
                    st.write("Erkannte Excel-Spalten:")
                    st.json(validation_details["mapping"])
                st.dataframe(validation_details["preview"], use_container_width=True)

    with right:
        st.subheader("Ergebnis")
        checked = "ja" if st.session_state.get("validation_details") else "nein"
        ready = "ja" if st.session_state.get("output_bytes") else "nein"
        st.caption(f"Status: Upload ja | Geprüft {checked} | Transformiert {ready}")

        with st.form("transform_form", border=True):
            st.subheader("Buchungsdaten")
            cols = st.columns(2)
            with cols[0]:
                st.date_input(
                    "Buchungsdatum Besoldung",
                    key="buchungsdatum_besoldung",
                    format="DD.MM.YYYY",
                )
            with cols[1]:
                st.date_input(
                    "Buchungsdatum Rest",
                    key="buchungsdatum_rest",
                    format="DD.MM.YYYY",
                )
            st.caption(
                "Aktuell wirksam: "
                f"Besoldung {_to_ddmmyyyy(st.session_state['buchungsdatum_besoldung'])}, "
                f"Rest {_to_ddmmyyyy(st.session_state['buchungsdatum_rest'])}"
            )

            st.subheader("Ausgabename")
            output_name = st.text_input("Ausgabedateiname", value=default_output)

            st.subheader("Transformation")
            submit_transform = st.form_submit_button(
                "Transformation starten", use_container_width=True
            )

        if submit_transform:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                input_path = _write_temp_file(tmp_path, input_file.name, input_payload)
                try:
                    runtime_config = _build_runtime_config_with_dates(
                        config,
                        st.session_state["buchungsdatum_besoldung"],
                        st.session_state["buchungsdatum_rest"],
                    )
                    safe_output_name = _sanitize_filename(output_name, default_output)
                    output_bytes = _run_transform(
                        input_path, safe_output_name, runtime_config
                    )
                except ProcessorError as exc:
                    st.session_state["transform_error"] = f"Transformation fehlgeschlagen: {exc}"
                    st.session_state.pop("output_bytes", None)
                    st.session_state.pop("output_name", None)
                except Exception as exc:
                    st.session_state["transform_error"] = f"Unerwarteter Fehler: {exc}"
                    st.session_state.pop("output_bytes", None)
                    st.session_state.pop("output_name", None)
                else:
                    st.session_state["output_bytes"] = output_bytes
                    st.session_state["output_name"] = safe_output_name
                    st.session_state.pop("transform_error", None)

        if transform_error := st.session_state.get("transform_error"):
            st.error(transform_error)

        if st.session_state.get("output_bytes") and st.session_state.get("output_name"):
            st.success("Transformation abgeschlossen")
            st.download_button(
                "Ausgabe herunterladen",
                data=st.session_state["output_bytes"],
                file_name=st.session_state["output_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
