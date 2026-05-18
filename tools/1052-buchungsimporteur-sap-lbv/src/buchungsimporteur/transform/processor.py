"""Hauptprozessor für die Datentransformation von Excel zu Excel."""

import logging
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ..config.schema import ColumnType, TransformationConfig, create_default_config
from ..excel.reader import ExcelReader
from ..excel.writer import ExcelWriter, create_sap_template_columns
from .rules import TransformationRules

logger = logging.getLogger(__name__)
LEGACY_STATIC_GESCHAEFTSJAHR = "2025"


class ProcessorError(Exception):
    """Fehler bei der Datenverarbeitung."""


class DataProcessor:
    """Hauptklasse für die Transformation von Quelldaten zu SAP-Format."""

    def __init__(
        self,
        config: TransformationConfig | None = None,
        reference_date: date | None = None,
    ) -> None:
        """Initialisiert den Processor.

        Args:
            config: Transformationskonfiguration, falls None wird Standard verwendet
            reference_date: Referenzdatum für Buchungslogik (optional)
        """
        self.config = (
            config.model_copy(deep=True) if config else create_default_config()
        )
        self._upgrade_legacy_geschaeftsjahr_config()
        self.reference_date = reference_date or date.today()
        self.rules = TransformationRules(
            self.config.zeilenart_config, reference_date=self.reference_date
        )

        logger.info(
            f"Processor initialisiert: {self.config.name} v{self.config.version}"
        )

    def _upgrade_legacy_geschaeftsjahr_config(self) -> None:
        """Migriert alte Default-Konfigurationen mit hart codiertem Geschäftsjahr."""
        geschaeftsjahr = self.config.columns.get("b")
        if geschaeftsjahr is None:
            return

        if (
            geschaeftsjahr.title == "Geschäftsjahr"
            and geschaeftsjahr.column_type == ColumnType.CONSTANT
            and geschaeftsjahr.constant_value == LEGACY_STATIC_GESCHAEFTSJAHR
        ):
            geschaeftsjahr.column_type = ColumnType.CALCULATED
            geschaeftsjahr.calculation_rule = "geschaeftsjahr_by_belegart"
            geschaeftsjahr.source_column = "A"
            geschaeftsjahr.constant_value = None

    def process_file(self, input_path: Path, output_path: Path) -> None:
        """Verarbeitet eine Excel-Datei komplett von Eingabe zu Ausgabe.

        Args:
            input_path: Pfad zur Quell-Excel-Datei
            output_path: Pfad für die Ziel-Excel-Datei

        Raises:
            ProcessorError: Bei Fehlern in der Verarbeitung
        """
        try:
            # 1. Einlesen der Quelldaten
            logger.info("Lade Quelldaten...")
            reader = ExcelReader(input_path)
            source_df = reader.read_data()

            logger.info(f"Quelldaten geladen: {len(source_df)} Zeilen")

            # 2. Validierung der benötigten Spalten
            required_columns = self._get_required_source_columns()
            self.rules.validate_required_source_columns(source_df, required_columns)

            # 3. Transformation durchführen
            logger.info("Starte Datentransformation...")
            target_df = self.transform_data(source_df)

            logger.info(
                f"Transformation abgeschlossen: {len(target_df)} Zielzeilen erstellt"
            )

            # 4. Ausgabe schreiben
            logger.info("Schreibe Zieldatei...")
            writer = ExcelWriter(output_path)
            expected_columns = create_sap_template_columns()
            main_df, extra_sheets = self._build_output_sheets(target_df)

            writer.write_with_template_check(
                main_df,
                expected_columns,
                sheet_name="Buchungsdaten",
                extra_sheets=extra_sheets,
            )

            logger.info(f"Verarbeitung erfolgreich abgeschlossen: {output_path}")

        except Exception as e:
            if isinstance(e, ProcessorError):
                raise
            raise ProcessorError(f"Fehler bei der Dateiverarbeitung: {e}")

    def _build_output_sheets(
        self, target_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
        """Bereitet Haupt- und Zusatzblätter für die Excel-Ausgabe auf.

        Regeln:
            - "Sonstiges: Täglicher Zahltag" bleibt im Hauptblatt.
            - Alle übrigen "Sonstiges..."-Belege landen im Blatt "Sonstiges".
            - Pro Blatt werden Belegnummer, GrpId und Zeile neu gesetzt.
        """
        if "Belegkopftext" not in target_df.columns:
            raise ProcessorError("Spalte 'Belegkopftext' fehlt in den Zieldaten")

        belegkopf_values = target_df["Belegkopftext"].fillna("").astype(str).str.strip()
        sonstiges_mask = self.rules.is_sonstiges_belegkopftext(belegkopf_values)

        is_daily_payday = self.rules.is_daily_payday_belegkopftext(belegkopf_values)

        sonstiges_sheet_mask = sonstiges_mask & ~is_daily_payday
        main_df = self._prepare_sheet_dataframe(
            target_df[~sonstiges_sheet_mask].reset_index(drop=True)
        )

        extra_sheets: dict[str, pd.DataFrame] = {}
        if sonstiges_sheet_mask.any():
            extra_sheets["Sonstiges"] = self._prepare_sheet_dataframe(
                target_df[sonstiges_sheet_mask].reset_index(drop=True)
            )

        return main_df, extra_sheets

    def _prepare_sheet_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Setzt blattlokale Nummernkreise und leere Belegnummern."""
        prepared_df = df.copy()

        if "Belegnummer" in prepared_df.columns:
            prepared_df["Belegnummer"] = ""

        row_count = len(prepared_df)
        if "Zeile" in prepared_df.columns:
            prepared_df["Zeile"] = [str(i + 1) for i in range(row_count)]

        if "GrpId" in prepared_df.columns:
            prepared_df["GrpId"] = [str((i // 2) + 1) for i in range(row_count)]

        return prepared_df

    def transform_data(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transformiert Quelldaten zu SAP-Zielformat.

        Args:
            source_df: DataFrame mit Quelldaten (mit Excel-Spalten-Mapping)

        Returns:
            DataFrame mit transformierten Daten im Zielformat

        Raises:
            ProcessorError: Bei Transformationsfehlern
        """
        try:
            target_rows = []
            sequence_counter = 0
            excel_mapping = source_df.attrs.get("excel_column_mapping", {})
            belegkopf_column = excel_mapping.get("A")

            # Verarbeite jede Quellzeile
            for source_idx, source_row in source_df.iterrows():
                if belegkopf_column:
                    beleg_value = source_row.get(belegkopf_column, "")
                    if self.rules.should_skip_row(beleg_value):
                        logger.info(
                            "Überspringe Zeile %s aufgrund 'verbleibender Betrag'",
                            source_idx,
                        )
                        continue

                # Erstelle K/S-Zeilenpaar für diese Quellzeile
                k_s_pairs = self.rules.create_k_s_pairs(source_row, sequence_counter)

                # Transformiere beide Zeilen (K und S)
                for pair_data in k_s_pairs:
                    # Füge die Quellzeilen-basierte GrpId hinzu
                    pair_data["source_row_index"] = source_idx
                    target_row = self._transform_single_row(
                        source_df, source_idx, pair_data, sequence_counter
                    )
                    target_rows.append(target_row)
                    sequence_counter += 1

            # Erstelle DataFrame aus transformierten Zeilen
            if not target_rows:
                raise ProcessorError("Keine Daten zum Transformieren gefunden")

            target_df = pd.DataFrame(target_rows)

            logger.info(
                f"Transformation erfolgreich: {len(source_df)} → {len(target_df)} Zeilen"
            )

            return target_df

        except Exception as e:
            if isinstance(e, ProcessorError):
                raise
            raise ProcessorError(f"Fehler bei der Datentransformation: {e}")

    def _transform_single_row(
        self,
        source_df: pd.DataFrame,
        source_idx: int,
        pair_data: dict[str, Any],
        sequence_counter: int,
    ) -> dict[str, Any]:
        """Transformiert eine einzelne Zeile basierend auf der Konfiguration.

        Args:
            source_df: DataFrame mit allen Quelldaten
            source_idx: Index der aktuellen Quellzeile
            pair_data: Daten für K/S-Zeilenpaar
            sequence_counter: Aktueller Sequenzzähler

        Returns:
            Dictionary mit transformierter Zeile
        """
        target_row = {}

        # Verarbeite jede Zielspalte gemäß Konfiguration
        for column_key, column_config in self.config.columns.items():
            try:
                value = self._calculate_column_value(
                    source_df, source_idx, column_config, pair_data, sequence_counter
                )
                target_row[column_config.title] = value

            except Exception as e:
                logger.error(
                    f"Fehler bei Spalte {column_key} ({column_config.title}): {e}"
                )
                target_row[column_config.title] = ""  # Fallback zu leerem Wert

        return target_row

    def _calculate_column_value(
        self,
        source_df: pd.DataFrame,
        source_idx: int,
        column_config: Any,
        pair_data: dict[str, Any],
        sequence_counter: int,
    ) -> str:
        """Berechnet den Wert für eine Spalte basierend auf ihrer Konfiguration.

        Args:
            source_df: DataFrame mit Quelldaten
            source_idx: Index der Quellzeile
            column_config: Konfiguration der Zielspalte
            pair_data: K/S-Zeilenpaar-Daten
            sequence_counter: Sequenzzähler

        Returns:
            Berechneter Spaltenwert als String
        """
        column_type = column_config.column_type

        # Konstante Werte
        if column_type == ColumnType.CONSTANT:
            return column_config.constant_value or ""

        # Leere Spalten
        elif column_type == ColumnType.EMPTY:
            return ""

        # Sequenznummern
        elif column_type == ColumnType.SEQUENCE:
            return self.rules.generate_sequence_number(
                sequence_counter, column_config.start_value or 1
            )

        # Quelldaten-Mapping
        elif column_type == ColumnType.SOURCE_MAPPING:
            if not column_config.source_column:
                return ""

            raw_value = self.rules.extract_source_value(
                source_df, source_idx, column_config.source_column
            )

            # Spezielle Formatierung je nach Spaltentyp
            if column_config.title in ["Rechnungsdatum", "Buchungsdatum"]:
                value = self.rules.format_date(raw_value)
            elif column_config.title in ["Betrag Hausw", "Steuerbetrag"]:
                value = self.rules.format_amount(raw_value)
            else:
                value = str(raw_value) if raw_value is not None else ""

            if column_config.max_length is not None:
                return self.rules.truncate_string(value, column_config.max_length)
            return value

        # Berechnete Werte
        elif column_type == ColumnType.CALCULATED:
            return self._calculate_computed_value(
                source_df, source_idx, column_config, pair_data
            )

        else:
            logger.warning(f"Unbekannter Spaltentyp: {column_type}")
            return ""

    def _calculate_computed_value(
        self,
        source_df: pd.DataFrame,
        source_idx: int,
        column_config: Any,
        pair_data: dict[str, Any],
    ) -> str:
        """Berechnet Werte für berechnete Spalten.

        Args:
            source_df: DataFrame mit Quelldaten
            source_idx: Index der Quellzeile
            column_config: Spaltenkonfiguration
            pair_data: K/S-Zeilenpaar-Daten

        Returns:
            Berechneter Wert als String
        """
        rule = column_config.calculation_rule

        # Zeileart (K/S)
        if rule == "zeileart_k_s":
            return pair_data["zeileart"]

        # Position basierend auf Zeileart
        elif rule == "position_by_zeileart":
            if pair_data["is_k_line"]:
                return column_config.k_value or "1"
            else:
                return column_config.s_value or "2"

        # Hauptbuch basierend auf Zeileart (alte Logik)
        elif rule == "hauptbuch_by_zeileart":
            if pair_data["is_k_line"]:
                return column_config.k_value or "440000"
            else:
                return column_config.s_value or "48500199"

        # Hauptbuch basierend auf Soll/Haben (neue Logik)
        elif rule == "hauptbuch_by_soll_haben":
            soll_haben = pair_data["soll_haben"]  # H oder S
            if soll_haben == "H":
                return column_config.k_value or "440000"  # Haben -> 440000
            else:
                return column_config.s_value or "48500199"  # Soll -> 48500199

        # Soll/Haben basierend auf Position (neue Logik)
        elif rule == "soll_haben_by_position":
            return pair_data["soll_haben"]  # Direkt aus K/S-Paar

        # Soll/Haben basierend auf Betrag (alte Logik)
        elif rule == "soll_haben_by_amount":
            # Hole Betrag aus Spalte B
            betrag = self.rules.extract_source_value(source_df, source_idx, "B")
            return self.rules.calculate_soll_haben(
                betrag, column_config.soll_haben_rule
            )

        # GrpId basierend auf Quellzeile (K/S-Paare haben dieselbe Nummer)
        elif rule == "group_id_by_source_row":
            # Verwende den Quellzeilen-Index + 1 als GrpId
            source_row_idx = pair_data.get("source_row_index", 0)
            start_value = getattr(column_config, "start_value", 1) or 1
            return self.rules.apply_group_id_by_source_row(source_row_idx, start_value)

        # Buchungsdatum basierend auf Belegart
        elif rule == "buchungsdatum_by_belegart":
            belegart_value = None
            if column_config.source_column:
                belegart_value = self.rules.extract_source_value(
                    source_df, source_idx, column_config.source_column
                )
            default_date = column_config.default_date
            besoldung_date = column_config.besoldung_date
            return self.rules.apply_buchungsdatum_by_belegart(
                belegart_value, default_date, besoldung_date
            )

        elif rule == "geschaeftsjahr_by_belegart":
            belegart_value = None
            if column_config.source_column:
                belegart_value = self.rules.extract_source_value(
                    source_df, source_idx, column_config.source_column
                )
            return self.rules.apply_geschaeftsjahr_by_belegart(
                belegart_value,
                column_config.default_date,
                column_config.besoldung_date,
            )

        # Text mit K-Präfix
        elif rule == "text_with_k_prefix":
            source_text = self.rules.extract_source_value(
                source_df, source_idx, column_config.source_column
            )
            is_k_line = pair_data["is_k_line"]
            max_length = column_config.max_length or 50
            return self.rules.apply_text_with_k_prefix(
                source_text, is_k_line, max_length
            )

        # Soll/Haben basierend auf Zeileart
        elif rule == "soll_haben_by_zeileart":
            is_k_line = pair_data["is_k_line"]
            k_value = column_config.k_value or "H"
            s_value = column_config.s_value or "S"
            return self.rules.apply_soll_haben_by_zeileart(is_k_line, k_value, s_value)

        else:
            logger.warning(f"Unbekannte Berechnungsregel: {rule}")
            return ""

    def _get_required_source_columns(self) -> list[str]:
        """Ermittelt alle benötigten Quelldaten-Spalten aus der Konfiguration.

        Returns:
            Liste der benötigten Excel-Spaltenbezeichnungen
        """
        required_columns = set()

        for column_config in self.config.columns.values():
            if column_config.source_column:
                required_columns.add(column_config.source_column)

            if (
                column_config.column_type == ColumnType.CALCULATED
                and column_config.calculation_rule == "soll_haben_by_amount"
            ):
                required_columns.add("B")

        return sorted(required_columns)
