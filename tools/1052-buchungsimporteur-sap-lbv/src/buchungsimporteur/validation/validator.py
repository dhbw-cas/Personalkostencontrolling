"""Validierung von Quelldaten und Transformationsergebnissen."""

import logging
import re
from decimal import Decimal, InvalidOperation

import pandas as pd

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Fehler bei der Datenvalidierung."""


class ValidationResult:
    """Ergebnis einer Validierung."""

    def __init__(self) -> None:
        self.is_valid = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def add_error(self, message: str) -> None:
        """Fügt einen Validierungsfehler hinzu."""
        self.errors.append(message)
        self.is_valid = False
        logger.error(f"Validation Error: {message}")

    def add_warning(self, message: str) -> None:
        """Fügt eine Validierungswarnung hinzu."""
        self.warnings.append(message)
        logger.warning(f"Validation Warning: {message}")

    def add_info(self, message: str) -> None:
        """Fügt eine Validierungsinfo hinzu."""
        self.info.append(message)
        logger.info(f"Validation Info: {message}")

    def get_summary(self) -> str:
        """Gibt eine Zusammenfassung der Validierung zurück."""
        status = "✅ GÜLTIG" if self.is_valid else "❌ UNGÜLTIG"
        summary = f"Validierung: {status}\n"

        if self.errors:
            summary += f"Fehler ({len(self.errors)}):\n"
            for error in self.errors:
                summary += f"  - {error}\n"

        if self.warnings:
            summary += f"Warnungen ({len(self.warnings)}):\n"
            for warning in self.warnings:
                summary += f"  - {warning}\n"

        if self.info:
            summary += f"Informationen ({len(self.info)}):\n"
            for info in self.info:
                summary += f"  - {info}\n"

        return summary


class DataValidator:
    """Validiert Quelldaten und Transformationsergebnisse."""

    def validate_source_data(self, df: pd.DataFrame) -> ValidationResult:
        """Validiert Quelldaten auf Vollständigkeit und Format.

        Args:
            df: DataFrame mit Quelldaten (mit Excel-Spalten-Mapping)

        Returns:
            ValidationResult mit Ergebnissen
        """
        result = ValidationResult()

        # Grundlegende Struktur-Validierung
        if df.empty:
            result.add_error("Quelldaten sind leer")
            return result

        result.add_info(f"Quelldaten: {len(df)} Zeilen, {len(df.columns)} Spalten")

        # Excel-Spalten-Mapping prüfen
        if "excel_column_mapping" not in df.attrs:
            result.add_error("Excel-Spalten-Mapping fehlt")
            return result

        mapping = df.attrs["excel_column_mapping"]
        result.add_info(f"Excel-Spalten verfügbar: {sorted(mapping.keys())}")

        # Validiere spezifische Spalten
        self._validate_column_a_belegkopftext(df, mapping, result)
        self._validate_column_b_betrag(df, mapping, result)
        self._validate_column_c_datum(df, mapping, result)
        self._validate_column_f_referenz(df, mapping, result)
        self._validate_column_g_text(df, mapping, result)

        return result

    def _validate_column_a_belegkopftext(
        self, df: pd.DataFrame, mapping: dict[str, str], result: ValidationResult
    ) -> None:
        """Validiert Spalte A (Belegkopftext)."""
        if "A" not in mapping:
            result.add_warning("Spalte A (Belegkopftext) nicht gefunden")
            return

        column_name = mapping["A"]
        series = df[column_name]

        # Prüfe auf leere Werte
        empty_count = series.isna().sum() + (series == "").sum()
        if empty_count > 0:
            result.add_warning(f"Spalte A: {empty_count} leere Werte gefunden")

        # Prüfe Länge (SAP-Felder haben oft Längenbeschränkungen)
        max_length = series.astype(str).str.len().max()
        if max_length > 100:  # Angenommene SAP-Grenze
            result.add_warning(
                f"Spalte A: Längster Text hat {max_length} Zeichen (>100)"
            )

    def _validate_column_b_betrag(
        self, df: pd.DataFrame, mapping: dict[str, str], result: ValidationResult
    ) -> None:
        """Validiert Spalte B (Betrag)."""
        if "B" not in mapping:
            result.add_error("Spalte B (Betrag) ist erforderlich, aber nicht gefunden")
            return

        column_name = mapping["B"]
        series = df[column_name]

        # Prüfe auf leere Werte
        empty_count = series.isna().sum() + (series == "").sum()
        if empty_count > 0:
            result.add_error(f"Spalte B: {empty_count} leere Beträge gefunden")

        # Validiere Betragsformat
        invalid_amounts = 0
        zero_amounts = 0

        for idx, value in series.items():
            if pd.isna(value) or value == "":
                continue

            try:
                # Versuche Betrag zu parsen
                clean_value = str(value).replace(",", ".").replace(" ", "")
                clean_value = clean_value.replace("€", "").replace("EUR", "").strip()

                if not clean_value:
                    invalid_amounts += 1
                    continue

                amount = Decimal(clean_value)

                if amount == 0:
                    zero_amounts += 1

            except (ValueError, InvalidOperation):
                invalid_amounts += 1

        if invalid_amounts > 0:
            result.add_error(f"Spalte B: {invalid_amounts} ungültige Beträge gefunden")

        if zero_amounts > 0:
            result.add_warning(f"Spalte B: {zero_amounts} Null-Beträge gefunden")

    def _validate_column_c_datum(
        self, df: pd.DataFrame, mapping: dict[str, str], result: ValidationResult
    ) -> None:
        """Validiert Spalte C (Rechnungsdatum)."""
        if "C" not in mapping:
            result.add_error(
                "Spalte C (Rechnungsdatum) ist erforderlich, aber nicht gefunden"
            )
            return

        column_name = mapping["C"]
        series = df[column_name]

        # Prüfe auf leere Werte
        empty_count = series.isna().sum() + (series == "").sum()
        if empty_count > 0:
            result.add_warning(f"Spalte C: {empty_count} leere Datumsfelder gefunden")

        # Validiere Datumsformat
        invalid_dates = 0

        for idx, value in series.items():
            if pd.isna(value) or value == "":
                continue

            try:
                # Versuche Datum zu parsen
                pd.to_datetime(value, dayfirst=True)
            except (ValueError, TypeError):
                # Versuche häufige Datumsformate
                date_str = str(value).strip()
                if not self._is_valid_date_format(date_str):
                    invalid_dates += 1

        if invalid_dates > 0:
            result.add_error(
                f"Spalte C: {invalid_dates} ungültige Datumsformate gefunden"
            )

    def _validate_column_f_referenz(
        self, df: pd.DataFrame, mapping: dict[str, str], result: ValidationResult
    ) -> None:
        """Validiert Spalte F (Referenz/Zuordnung)."""
        if "F" not in mapping:
            result.add_warning("Spalte F (Referenz) nicht gefunden")
            return

        column_name = mapping["F"]
        series = df[column_name]

        # Prüfe auf leere Werte
        empty_count = series.isna().sum() + (series == "").sum()
        if empty_count > 0:
            result.add_info(
                f"Spalte F: {empty_count} leere Referenzen (kann normal sein)"
            )

        # Prüfe Länge
        max_length = series.astype(str).str.len().max()
        if max_length > 50:  # Angenommene SAP-Grenze für Referenzen
            result.add_warning(
                f"Spalte F: Längste Referenz hat {max_length} Zeichen (>50)"
            )

    def _validate_column_g_text(
        self, df: pd.DataFrame, mapping: dict[str, str], result: ValidationResult
    ) -> None:
        """Validiert Spalte G (Text)."""
        if "G" not in mapping:
            result.add_warning("Spalte G (Text) nicht gefunden")
            return

        column_name = mapping["G"]
        series = df[column_name]

        # Prüfe auf leere Werte
        empty_count = series.isna().sum() + (series == "").sum()
        if empty_count > 0:
            result.add_info(f"Spalte G: {empty_count} leere Textfelder")

    def _is_valid_date_format(self, date_str: str) -> bool:
        """Prüft ob ein String ein gültiges Datumsformat hat."""
        # Häufige deutsche Datumsformate
        date_patterns = [
            r"^\d{2}\.\d{2}\.\d{4}$",  # DD.MM.YYYY
            r"^\d{1,2}\.\d{1,2}\.\d{4}$",  # D.M.YYYY oder DD.M.YYYY etc.
            r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
            r"^\d{2}/\d{2}/\d{4}$",  # DD/MM/YYYY
        ]

        for pattern in date_patterns:
            if re.match(pattern, date_str):
                return True

        return False

    def validate_target_data(
        self, df: pd.DataFrame, expected_columns: list[str]
    ) -> ValidationResult:
        """Validiert transformierte Zieldaten.

        Args:
            df: DataFrame mit transformierten Daten
            expected_columns: Liste der erwarteten Spalten

        Returns:
            ValidationResult mit Ergebnissen
        """
        result = ValidationResult()

        if df.empty:
            result.add_error("Zieldaten sind leer")
            return result

        result.add_info(f"Zieldaten: {len(df)} Zeilen, {len(df.columns)} Spalten")

        # Prüfe Spaltenstruktur
        missing_columns = set(expected_columns) - set(df.columns)
        if missing_columns:
            result.add_error(f"Fehlende Spalten: {sorted(missing_columns)}")

        extra_columns = set(df.columns) - set(expected_columns)
        if extra_columns:
            result.add_warning(f"Zusätzliche Spalten: {sorted(extra_columns)}")

        # Validiere K/S-Paarung
        self._validate_k_s_pairing(df, result)

        # Validiere Pflichtfelder
        self._validate_required_target_fields(df, result)

        return result

    def _validate_k_s_pairing(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Validiert dass K- und S-Zeilen korrekt gepaart sind."""
        if "Zeileart" not in df.columns:
            result.add_error("Spalte 'Zeileart' nicht gefunden")
            return

        k_count = (df["Zeileart"] == "K").sum()
        s_count = (df["Zeileart"] == "S").sum()

        if k_count != s_count:
            result.add_error(
                f"K/S-Paarung ungültig: {k_count} K-Zeilen, {s_count} S-Zeilen"
            )
        else:
            result.add_info(f"K/S-Paarung korrekt: {k_count} Paare")

    def _validate_required_target_fields(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> None:
        """Validiert Pflichtfelder in den Zieldaten."""
        required_fields = [
            "Geschäftsjahr",
            "Buchungskreis",
            "Belegart",
            "Zeileart",
            "Position",
            "Buchungsdatum",
            "Betrag Hausw",
            "Hauptbuch",
        ]

        for field in required_fields:
            if field not in df.columns:
                continue

            empty_count = df[field].isna().sum() + (df[field] == "").sum()
            if empty_count > 0:
                result.add_error(f"Pflichtfeld '{field}': {empty_count} leere Werte")
