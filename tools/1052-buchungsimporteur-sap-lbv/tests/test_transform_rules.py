"""Tests für Transformationsregeln."""

from datetime import date

import pandas as pd
import pytest

from buchungsimporteur.config.schema import SollHabenRule, ZeilenartPair
from buchungsimporteur.transform.rules import (
    TransformationRules,
    TransformationRulesError,
)


class TestTransformationRules:
    """Tests für die TransformationRules-Klasse."""

    def test_create_k_s_pairs(self) -> None:
        """Test der K/S-Paar-Erstellung."""
        config = ZeilenartPair()
        rules = TransformationRules(config)

        # Mock source row
        source_row = pd.Series({"A": "Test", "B": "100.00", "C": "01.01.2025"})

        pairs = rules.create_k_s_pairs(source_row, 1)

        assert len(pairs) == 2

        k_row, s_row = pairs

        # K-Zeile prüfen
        assert k_row["zeileart"] == "K"
        assert k_row["position"] == "1"
        assert k_row["hauptbuch"] == "440000"
        assert k_row["is_k_line"] is True
        assert k_row["target_row_number"] == 1

        # S-Zeile prüfen
        assert s_row["zeileart"] == "S"
        assert s_row["position"] == "2"
        assert s_row["hauptbuch"] == "48500199"
        assert s_row["is_k_line"] is False
        assert s_row["target_row_number"] == 1

    def test_calculate_soll_haben_negative_amount(self) -> None:
        """Test Soll/Haben bei negativen Beträgen."""
        rules = TransformationRules(ZeilenartPair())

        # Negative Beträge -> Soll (S)
        assert (
            rules.calculate_soll_haben(-100.50, SollHabenRule.NEGATIVE_AMOUNT_SOLL)
            == "S"
        )
        assert (
            rules.calculate_soll_haben("-100,50", SollHabenRule.NEGATIVE_AMOUNT_SOLL)
            == "S"
        )
        assert (
            rules.calculate_soll_haben("-100.50 €", SollHabenRule.NEGATIVE_AMOUNT_SOLL)
            == "S"
        )

        # Positive Beträge -> Haben (H)
        assert (
            rules.calculate_soll_haben(100.50, SollHabenRule.NEGATIVE_AMOUNT_SOLL)
            == "H"
        )
        assert (
            rules.calculate_soll_haben("100,50", SollHabenRule.NEGATIVE_AMOUNT_SOLL)
            == "H"
        )
        assert (
            rules.calculate_soll_haben("100.50 EUR", SollHabenRule.NEGATIVE_AMOUNT_SOLL)
            == "H"
        )

        # Null -> Haben (H)
        assert rules.calculate_soll_haben(0, SollHabenRule.NEGATIVE_AMOUNT_SOLL) == "H"
        assert (
            rules.calculate_soll_haben("0", SollHabenRule.NEGATIVE_AMOUNT_SOLL) == "H"
        )

    def test_calculate_soll_haben_constants(self) -> None:
        """Test konstante Soll/Haben-Werte."""
        rules = TransformationRules(ZeilenartPair())

        assert rules.calculate_soll_haben(100, SollHabenRule.CONSTANT_H) == "H"
        assert rules.calculate_soll_haben(-100, SollHabenRule.CONSTANT_H) == "H"

        assert rules.calculate_soll_haben(100, SollHabenRule.CONSTANT_S) == "S"
        assert rules.calculate_soll_haben(-100, SollHabenRule.CONSTANT_S) == "S"

    def test_calculate_soll_haben_invalid_amount(self) -> None:
        """Test ungültige Beträge."""
        rules = TransformationRules(ZeilenartPair())

        with pytest.raises(TransformationRulesError):
            rules.calculate_soll_haben("invalid", SollHabenRule.NEGATIVE_AMOUNT_SOLL)

        with pytest.raises(TransformationRulesError):
            rules.calculate_soll_haben("abc€", SollHabenRule.NEGATIVE_AMOUNT_SOLL)

    def test_format_amount(self) -> None:
        """Test Betragsformatierung."""
        rules = TransformationRules(ZeilenartPair())

        # Normale Beträge
        assert rules.format_amount(100.5) == "100.50"
        assert rules.format_amount(-100.5) == "100.50"  # Absolutwert für SAP
        assert rules.format_amount("100,50") == "100.50"
        assert rules.format_amount("-100,50 €") == "100.50"

        # Leere/ungültige Werte
        assert rules.format_amount(None) == "0.00"
        assert rules.format_amount("") == "0.00"
        assert rules.format_amount(pd.NA) == "0.00"

        # Ungültige Werte -> Fallback
        assert rules.format_amount("invalid") == "0.00"

    def test_format_date(self) -> None:
        """Test Datumsformatierung."""
        rules = TransformationRules(ZeilenartPair())

        # Verschiedene Eingabeformate
        assert rules.format_date("2025-01-01") == "01.01.2025"
        assert rules.format_date("01.01.2025") == "01.01.2025"
        assert rules.format_date("1.1.2025") == "01.01.2025"

        # Leere Werte
        assert rules.format_date(None) == ""
        assert rules.format_date("") == ""
        assert rules.format_date(pd.NA) == ""

    def test_generate_sequence_number(self) -> None:
        """Test Sequenznummer-Generierung."""
        rules = TransformationRules(ZeilenartPair())

        assert rules.generate_sequence_number(0, 1) == "1"
        assert rules.generate_sequence_number(1, 1) == "2"
        assert rules.generate_sequence_number(0, 10) == "10"
        assert rules.generate_sequence_number(5, 1) == "6"

    def test_extract_source_value(self) -> None:
        """Test Extraktion von Quelldaten-Werten."""
        rules = TransformationRules(ZeilenartPair())

        # Mock DataFrame mit Excel-Mapping
        df = pd.DataFrame(
            {"Column1": ["A1", "A2"], "Column2": ["B1", "B2"], "Column3": ["C1", "C2"]}
        )
        df.attrs["excel_column_mapping"] = {
            "A": "Column1",
            "B": "Column2",
            "C": "Column3",
        }

        # Test Extraktion
        assert rules.extract_source_value(df, 0, "A") == "A1"
        assert rules.extract_source_value(df, 1, "B") == "B2"
        assert rules.extract_source_value(df, 0, "C") == "C1"

        # Test Fehlerbehandlung
        with pytest.raises(TransformationRulesError):
            rules.extract_source_value(df, 0, "D")  # Spalte existiert nicht

        with pytest.raises(TransformationRulesError):
            rules.extract_source_value(df, 10, "A")  # Zeile existiert nicht

    def test_apply_buchungsdatum_by_belegart(self) -> None:
        """Buchungsdatum wechselt bei Besoldung."""
        rules = TransformationRules(
            ZeilenartPair(), reference_date=date(2025, 7, 5)
        )

        assert (
            rules.apply_buchungsdatum_by_belegart("Vergütung") == "30.06.2025"
        )
        assert (
            rules.apply_buchungsdatum_by_belegart("Monatliche Besoldung")
            == "01.07.2025"
        )

    def test_apply_text_with_k_prefix(self) -> None:
        """K-Zeilen erhalten Stern und werden gekürzt."""
        rules = TransformationRules(ZeilenartPair())
        value = rules.apply_text_with_k_prefix("Lang" * 20, True, max_length=10)
        assert value.startswith("*")
        assert len(value) == 10
        assert rules.apply_text_with_k_prefix("Text", False, max_length=10) == "Text"

    def test_should_skip_row(self) -> None:
        """Zeilen mit 'verbleibender Betrag' werden übersprungen."""
        rules = TransformationRules(ZeilenartPair())
        assert rules.should_skip_row("verbleibender Betrag XYZ")
        assert not rules.should_skip_row("Vergütung")

    def test_is_sonstiges_belegkopftext_series(self) -> None:
        """Regex erkennt Sonstiges-Belege."""
        rules = TransformationRules(ZeilenartPair())
        series = pd.Series(["Sonstiges", "Sonstiges: A", "Vergütung"])
        mask = rules.is_sonstiges_belegkopftext(series)
        assert mask.tolist() == [True, True, False]

    def test_is_daily_payday_belegkopftext_series(self) -> None:
        """Regex erkennt taeglichen Zahltag auch bei Punkt und gekuerztem Text."""
        rules = TransformationRules(ZeilenartPair())
        series = pd.Series(
            [
                "Sonstiges: Täglicher Zahltag",
                "Sonstiges. Täglicher Zahl",
                "SONSTIGES - täglicher Zahltag",
                "Sonstiges: Sonstiger Fall",
            ]
        )
        mask = rules.is_daily_payday_belegkopftext(series)
        assert mask.tolist() == [True, True, True, False]
