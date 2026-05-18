"""Tests für Buchungsdatum-Logik in der Streamlit-App."""

from datetime import date

from buchungsimporteur.config.schema import create_default_config
from streamlit_app import (
    _build_runtime_config_with_dates,
    _compute_buchungsdatum_defaults,
)


def test_compute_buchungsdatum_defaults_is_deterministic_for_reference_date() -> None:
    """Default-Werte folgen der bestehenden Besoldung/Rest-Regel."""
    besoldung, rest = _compute_buchungsdatum_defaults(
        config=None,
        reference_date=date(2025, 11, 3),
    )

    assert besoldung == date(2025, 11, 1)
    assert rest == date(2025, 10, 31)


def test_build_runtime_config_with_dates_sets_column_h_overrides() -> None:
    """Runtime-Config erhält beide Overrides im erwarteten Stringformat."""
    config = _build_runtime_config_with_dates(
        base_config=None,
        besoldung_date=date(2025, 11, 1),
        rest_date=date(2025, 10, 31),
    )

    assert config.columns["h"].besoldung_date == "01.11.2025"
    assert config.columns["h"].default_date == "31.10.2025"


def test_build_runtime_config_with_dates_does_not_mutate_input_config() -> None:
    """Die übergebene Basiskonfiguration bleibt unverändert."""
    base = create_default_config()
    base.columns["h"].besoldung_date = None
    base.columns["h"].default_date = None

    _ = _build_runtime_config_with_dates(
        base_config=base,
        besoldung_date=date(2025, 11, 1),
        rest_date=date(2025, 10, 31),
    )

    assert base.columns["h"].besoldung_date is None
    assert base.columns["h"].default_date is None
