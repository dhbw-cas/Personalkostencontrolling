"""Geschäftsregeln für die Transformation der Buchungsdaten."""

import logging
import re
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from ..config.schema import SollHabenRule, ZeilenartPair

logger = logging.getLogger(__name__)


class TransformationRulesError(Exception):
    """Fehler bei der Anwendung von Transformationsregeln."""


class TransformationRules:
    """Implementiert die Geschäftslogik für die Datentransformation."""

    def __init__(
        self,
        zeilenart_config: ZeilenartPair,
        reference_date: date | None = None,
    ) -> None:
        """Initialisiert die Transformationsregeln.

        Args:
            zeilenart_config: Konfiguration für K/S-Zeilenpaare
            reference_date: Referenzdatum für Buchungslogik
        """
        self.zeilenart_config = zeilenart_config
        self.reference_date = reference_date or date.today()
        self._sonstiges_pattern = re.compile(r"(?i)^sonstiges[\W_]?", re.UNICODE)
        self._daily_payday_pattern = re.compile(
            r"(?i)\bsonstiges\b.*\btäglicher\s+zahl(?:tag)?\b",
            re.UNICODE,
        )

    def create_k_s_pairs(
        self, source_row: pd.Series, row_number: int
    ) -> list[dict[str, Any]]:
        """Erstellt K- und S-Zeilenpaar aus einer Quelldatenzeile.

        Args:
            source_row: Zeile aus den Quelldaten
            row_number: Fortlaufende Zeilennummer für die Zieldatei

        Returns:
            Liste mit zwei Dictionaries (K-Zeile und S-Zeile)
        """
        # Basis-Zeile für beide K und S
        base_row = {"source_data": source_row, "target_row_number": row_number}

        # K-Zeile (Habenbuchung - erste Zeile)
        k_row = base_row.copy()
        k_row.update(
            {
                "zeileart": self.zeilenart_config.k_value,
                "position": str(self.zeilenart_config.k_position),
                "hauptbuch": self.zeilenart_config.k_hauptbuch,
                "is_k_line": True,
                "soll_haben": "H",  # Erste Zeile = Habenbuchung
            }
        )

        # S-Zeile (Sollbuchung - zweite Zeile)
        s_row = base_row.copy()
        s_row.update(
            {
                "zeileart": self.zeilenart_config.s_value,
                "position": str(self.zeilenart_config.s_position),
                "hauptbuch": self.zeilenart_config.s_hauptbuch,
                "is_k_line": False,
                "soll_haben": "S",  # Zweite Zeile = Sollbuchung
            }
        )

        return [k_row, s_row]

    def should_skip_row(self, beleg_value: Any) -> bool:
        """Prüft, ob eine Zeile aufgrund des Belegtexts ignoriert werden soll."""
        if pd.isna(beleg_value) or beleg_value == "":
            return False

        text = str(beleg_value).lower()
        return "verbleibender betrag" in text

    def is_sonstiges_belegkopftext(self, values: Any) -> Any:
        """Bestimmt, ob ein Belegkopftext zur 'Sonstiges'-Kategorie gehört."""
        if isinstance(values, pd.Series):
            return (
                values.fillna("")
                .astype(str)
                .str.strip()
                .str.match(self._sonstiges_pattern)
            )

        text = str(values or "").strip()
        return bool(self._sonstiges_pattern.match(text))

    def is_daily_payday_belegkopftext(self, values: Any) -> Any:
        """Bestimmt, ob ein Belegkopftext 'Sonstiges ... Täglicher Zahltag' ist."""
        if isinstance(values, pd.Series):
            return (
                values.fillna("")
                .astype(str)
                .str.strip()
                .str.contains(self._daily_payday_pattern)
            )

        text = str(values or "").strip()
        return bool(self._daily_payday_pattern.search(text))

    def calculate_soll_haben(self, betrag: Any, rule: SollHabenRule) -> str:
        """Berechnet Soll/Haben basierend auf Betrag und Regel.

        Args:
            betrag: Betrag aus Quelldaten
            rule: Regel für Soll/Haben-Bestimmung

        Returns:
            'S' für Soll, 'H' für Haben

        Raises:
            TransformationRulesError: Bei ungültigen Beträgen oder Regeln
        """
        if rule == SollHabenRule.CONSTANT_H:
            return "H"
        elif rule == SollHabenRule.CONSTANT_S:
            return "S"
        elif rule == SollHabenRule.NEGATIVE_AMOUNT_SOLL:
            try:
                # Konvertiere zu Decimal für präzise Vergleiche
                if pd.isna(betrag) or betrag == "":
                    logger.warning("Leerer oder NaN Betrag gefunden, verwende H")
                    return "H"

                # Versuche verschiedene Formate
                if isinstance(betrag, str):
                    # Entferne Tausendertrennzeichen und ersetze Komma durch Punkt
                    clean_betrag = str(betrag).replace(",", ".").replace(" ", "")
                    # Entferne mögliche Währungssymbole
                    clean_betrag = (
                        clean_betrag.replace("€", "").replace("EUR", "").strip()
                    )

                    if not clean_betrag:
                        return "H"

                    betrag_decimal = Decimal(clean_betrag)
                else:
                    betrag_decimal = Decimal(str(betrag))

                # Negative Beträge -> Soll (S), sonst Haben (H)
                return "S" if betrag_decimal < 0 else "H"

            except (ValueError, TypeError, InvalidOperation) as e:
                raise TransformationRulesError(f"Ungültiger Betrag '{betrag}': {e}")
        else:
            raise TransformationRulesError(f"Unbekannte Soll/Haben-Regel: {rule}")

    def format_amount(self, betrag: Any) -> str:
        """Formatiert Beträge für SAP-Export.

        Args:
            betrag: Roher Betrag aus Quelldaten

        Returns:
            Formatierter Betrag als String
        """
        if pd.isna(betrag) or betrag == "":
            return "0.00"

        try:
            # Konvertiere zu Decimal
            if isinstance(betrag, str):
                clean_betrag = str(betrag).replace(",", ".").replace(" ", "")
                clean_betrag = clean_betrag.replace("€", "").replace("EUR", "").strip()
                betrag_decimal = Decimal(clean_betrag)
            else:
                betrag_decimal = Decimal(str(betrag))

            # Formatiere mit 2 Dezimalstellen, absolute Werte für SAP
            return f"{abs(betrag_decimal):.2f}"

        except (ValueError, TypeError, InvalidOperation):
            logger.warning(f"Konnte Betrag '{betrag}' nicht formatieren, verwende 0.00")
            return "0.00"

    def format_date(self, date_value: Any) -> str:
        """Formatiert Datumswerte für SAP-Export.

        Args:
            date_value: Roher Datumswert aus Quelldaten

        Returns:
            Formatiertes Datum als DD.MM.YYYY String
        """
        if pd.isna(date_value) or date_value == "":
            return ""

        try:
            # Versuche pandas Datum-Parsing
            parsed_date = pd.to_datetime(date_value, dayfirst=True)
            return parsed_date.strftime("%d.%m.%Y")

        except (ValueError, TypeError):
            # Fallback: Versuche String-Behandlung
            date_str = str(date_value).strip()

            # Bereits im korrekten Format?
            if len(date_str) == 10 and date_str.count(".") == 2:
                parts = date_str.split(".")
                if len(parts) == 3 and all(part.isdigit() for part in parts):
                    return date_str

            logger.warning(f"Konnte Datum '{date_value}' nicht formatieren")
            return str(date_value)

    def validate_required_source_columns(
        self, df: pd.DataFrame, required_excel_columns: list[str]
    ) -> None:
        """Validiert dass alle benötigten Quelldaten-Spalten vorhanden sind.

        Args:
            df: DataFrame mit Excel-Spalten-Mapping
            required_excel_columns: Benötigte Excel-Spalten (z.B. ["A", "B", "C"])

        Raises:
            TransformationRulesError: Bei fehlenden Spalten
        """
        if "excel_column_mapping" not in df.attrs:
            raise TransformationRulesError("DataFrame hat kein Excel-Spalten-Mapping")

        mapping = df.attrs["excel_column_mapping"]
        available_columns = set(mapping.keys())
        required_columns = set(required_excel_columns)

        missing_columns = required_columns - available_columns

        if missing_columns:
            raise TransformationRulesError(
                f"Benötigte Quelldaten-Spalten fehlen: {sorted(missing_columns)}. "
                f"Verfügbare Spalten: {sorted(available_columns)}"
            )

    def extract_source_value(
        self, df: pd.DataFrame, row_idx: int, excel_column: str
    ) -> Any:
        """Extrahiert einen Wert aus den Quelldaten anhand Excel-Spaltenbezeichnung.

        Args:
            df: DataFrame mit Excel-Spalten-Mapping
            row_idx: Zeilenindex (0-basiert)
            excel_column: Excel-Spalte (A, B, C, ...)

        Returns:
            Wert aus der angegebenen Spalte und Zeile

        Raises:
            TransformationRulesError: Bei Fehlern beim Datenzugriff
        """
        try:
            if "excel_column_mapping" not in df.attrs:
                raise TransformationRulesError(
                    "DataFrame hat kein Excel-Spalten-Mapping"
                )

            mapping = df.attrs["excel_column_mapping"]

            if excel_column not in mapping:
                raise TransformationRulesError(
                    f"Excel-Spalte '{excel_column}' nicht gefunden"
                )

            original_column_name = mapping[excel_column]
            return df.iloc[row_idx][original_column_name]

        except IndexError:
            raise TransformationRulesError(f"Zeile {row_idx} nicht gefunden")
        except KeyError as e:
            raise TransformationRulesError(f"Spalte nicht gefunden: {e}")

    def generate_sequence_number(self, current_count: int, start_value: int = 1) -> str:
        """Generiert fortlaufende Sequenznummern.

        Args:
            current_count: Aktueller Zählerstand (0-basiert)
            start_value: Startwert für die Sequenz

        Returns:
            Sequenznummer als String
        """
        return str(start_value + current_count)

    def truncate_string(self, value: Any, max_length: int) -> str:
        """Begrenzt String-Länge nach SAP-Anforderungen.

        Args:
            value: Zu begrenzender Wert
            max_length: Maximale Länge

        Returns:
            Begrenzter String
        """
        if pd.isna(value) or value == "":
            return ""

        text = str(value).strip()
        if len(text) > max_length:
            logger.warning(
                f"Text '{text}' gekürzt von {len(text)} auf {max_length} Zeichen"
            )
            return text[:max_length]

        return text

    def apply_buchungsdatum_by_belegart(
        self,
        belegart_value: Any,
        default_date: str | None = None,
        besoldung_date: str | None = None,
    ) -> str:
        """Bestimmt Buchungsdatum basierend auf Belegart-Text.

        Args:
            belegart_value: Wert aus der Belegspalte (z.B. Excel-Spalte A)
            default_date: Standard-Buchungsdatum
            besoldung_date: Buchungsdatum für Besoldung

        Returns:
            Buchungsdatum als String
        """
        try:
            belegart = str(belegart_value or "").strip().lower()
            if "besoldung" in belegart:
                if besoldung_date:
                    return besoldung_date
                return self._first_day_current_month()

            if default_date:
                return default_date
            return self._last_day_previous_month()
        except Exception as e:
            logger.warning(f"Fehler bei Buchungsdatum-Bestimmung: {e}")
            if default_date:
                return default_date
            return self._last_day_previous_month()

    def apply_geschaeftsjahr_by_belegart(
        self,
        belegart_value: Any,
        default_date: str | None = None,
        besoldung_date: str | None = None,
    ) -> str:
        """Leitet das Geschäftsjahr aus dem wirksamen Buchungsdatum ab."""
        buchungsdatum = self.apply_buchungsdatum_by_belegart(
            belegart_value,
            default_date=default_date,
            besoldung_date=besoldung_date,
        )

        try:
            return str(pd.to_datetime(buchungsdatum, dayfirst=True).year)
        except (ValueError, TypeError):
            logger.warning(
                "Konnte Geschäftsjahr aus Buchungsdatum '%s' nicht ableiten, "
                "verwende Referenzjahr %s",
                buchungsdatum,
                self.reference_date.year,
            )
            return str(self.reference_date.year)

    def apply_text_with_k_prefix(
        self, source_text: str, is_k_line: bool, max_length: int = 50
    ) -> str:
        """Fügt Stern-Präfix für K-Zeilen hinzu.

        Args:
            source_text: Ursprungstext aus Quelldaten
            is_k_line: True wenn K-Zeile, False wenn S-Zeile
            max_length: Maximale Textlänge

        Returns:
            Text mit oder ohne Stern-Präfix
        """
        if pd.isna(source_text) or source_text == "":
            return ""

        text = str(source_text).strip()

        # Füge "*" für K-Zeilen hinzu
        if is_k_line:
            text = "*" + text

        # Begrenze auf maximale Länge
        return self.truncate_string(text, max_length)

    def apply_soll_haben_by_zeileart(
        self, is_k_line: bool, k_value: str = "H", s_value: str = "S"
    ) -> str:
        """Bestimmt Soll/Haben basierend auf Zeileart.

        Args:
            is_k_line: True wenn K-Zeile, False wenn S-Zeile
            k_value: Soll/Haben-Wert für K-Zeilen
            s_value: Soll/Haben-Wert für S-Zeilen

        Returns:
            Soll/Haben-Wert
        """
        return k_value if is_k_line else s_value

    def apply_group_id_by_source_row(
        self, source_row_index: int, start_value: int = 1
    ) -> str:
        """Generiert Gruppen-ID basierend auf Quelldatenzeile.

        Args:
            source_row_index: Index der Quelldatenzeile (0-basiert)
            start_value: Startwert für Gruppen-ID

        Returns:
            Gruppen-ID als String
        """
        # Jede Quelldatenzeile erhält eine eindeutige Gruppen-ID
        # K- und S-Zeile aus derselben Quelldatenzeile haben dieselbe GrpId
        return str(start_value + source_row_index)

    def _first_day_current_month(self) -> str:
        """Gibt den ersten Tag des Referenzmonats zurück."""
        ref = self.reference_date
        first_day = ref.replace(day=1)
        return first_day.strftime("%d.%m.%Y")

    def _last_day_previous_month(self) -> str:
        """Berechnet den letzten Tag des Vormonats basierend auf dem Referenzdatum."""
        ref = self.reference_date
        year = ref.year
        month = ref.month - 1
        if month == 0:
            month = 12
            year -= 1
        day = monthrange(year, month)[1]
        prev_month_last_day = date(year, month, day)
        return prev_month_last_day.strftime("%d.%m.%Y")
