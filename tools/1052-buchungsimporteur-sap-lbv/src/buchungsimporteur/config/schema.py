"""Pydantic-Modelle für die JSON-Konfiguration der Spaltenmappings."""

from enum import Enum

from pydantic import BaseModel, Field


class ColumnType(str, Enum):
    """Typ der Spaltenwerte."""

    CONSTANT = "constant"
    SOURCE_MAPPING = "source_mapping"
    CALCULATED = "calculated"
    EMPTY = "empty"
    SEQUENCE = "sequence"


class SollHabenRule(str, Enum):
    """Regeln für Soll/Haben Bestimmung."""

    NEGATIVE_AMOUNT_SOLL = "negative_amount_soll"  # Minusbetrag -> S, sonst H
    CONSTANT_H = "constant_h"
    CONSTANT_S = "constant_s"


class ZeilenartPair(BaseModel):
    """Konfiguration für K/S-Zeilenpaar."""

    k_value: str = "K"
    s_value: str = "S"
    k_position: int = 1
    s_position: int = 2
    k_hauptbuch: str = "440000"
    s_hauptbuch: str = "48500199"


class ColumnConfig(BaseModel):
    """Konfiguration für eine Zielspalte."""

    title: str
    column_type: ColumnType
    max_length: int | None = None

    # Für CONSTANT
    constant_value: str | None = None

    # Für SOURCE_MAPPING
    source_column: str | None = None  # z.B. "A", "B", "C"

    # Für CALCULATED
    calculation_rule: str | None = None
    soll_haben_rule: SollHabenRule | None = None

    # Für SEQUENCE
    start_value: int | None = None
    default_date: str | None = None
    besoldung_date: str | None = None

    # Spezielle Logik für positionsabhängige Werte
    k_value: str | None = None  # Wert wenn Zeileart = K
    s_value: str | None = None  # Wert wenn Zeileart = S


class TransformationConfig(BaseModel):
    """Hauptkonfiguration für die Transformation."""

    # Metadaten
    name: str = "SAP LBV Buchungsimport"
    version: str = "1.0"
    description: str | None = None

    # Zeilenpaar-Konfiguration
    zeilenart_config: ZeilenartPair = ZeilenartPair()

    # Spaltenkonfigurationen (a-ak)
    columns: dict[str, ColumnConfig] = Field(default_factory=dict)

    # Quelldaten-Spalten Info
    source_columns: dict[str, str] = Field(
        default_factory=lambda: {
            "A": "Belegkopftext",
            "B": "Betrag",
            "D": "Rechnungsdatum",
            "F": "Referenz/Zuordnung",
            "G": "Text",
        }
    )


def create_default_config() -> TransformationConfig:
    """Erstellt die Standard-Konfiguration basierend auf PLAN.md."""

    columns = {
        # Spalte A - Belegnummer (aus Spalte A, max 10 Zeichen)
        "a": ColumnConfig(
            title="Belegnummer",
            column_type=ColumnType.SOURCE_MAPPING,
            source_column="A",
            max_length=10,
        ),
        # Spalte B - Geschäftsjahr
        "b": ColumnConfig(
            title="Geschäftsjahr",
            column_type=ColumnType.CALCULATED,
            calculation_rule="geschaeftsjahr_by_belegart",
            source_column="A",
        ),
        # Spalte C - Zeileart
        "c": ColumnConfig(
            title="Zeileart",
            column_type=ColumnType.CALCULATED,
            calculation_rule="zeileart_k_s",
        ),
        # Spalte D - Buchungskreis
        "d": ColumnConfig(
            title="Buchungskreis",
            column_type=ColumnType.CONSTANT,
            constant_value="3400",
        ),
        # Spalte E - Belegart
        "e": ColumnConfig(
            title="Belegart", column_type=ColumnType.CONSTANT, constant_value="KN"
        ),
        # Spalte F - Position
        "f": ColumnConfig(
            title="Position",
            column_type=ColumnType.CALCULATED,
            calculation_rule="position_by_zeileart",
            k_value="1",
            s_value="2",
        ),
        # Spalte G - Rechnungsdatum
        "g": ColumnConfig(
            title="Rechnungsdatum",
            column_type=ColumnType.SOURCE_MAPPING,
            source_column="D",
        ),
        # Spalte H - Buchungsdatum
        "h": ColumnConfig(
            title="Buchungsdatum",
            column_type=ColumnType.CALCULATED,
            calculation_rule="buchungsdatum_by_belegart",
            source_column="A",
        ),
        # Spalte I - Buchungsperiode (leer)
        "i": ColumnConfig(
            title="Buchungsperiode",
            column_type=ColumnType.EMPTY,
        ),
        # Spalte J - Referenz
        "j": ColumnConfig(
            title="Referenz",
            column_type=ColumnType.SOURCE_MAPPING,
            source_column="F",
            max_length=16,
        ),
        # Spalte K - Belegkopftext
        "k": ColumnConfig(
            title="Belegkopftext",
            column_type=ColumnType.SOURCE_MAPPING,
            source_column="A",
            max_length=25,
        ),
        # Spalte L - Debitor (leer)
        "l": ColumnConfig(title="Debitor", column_type=ColumnType.EMPTY),
        # Spalte M - Kreditor
        "m": ColumnConfig(
            title="Kreditor", column_type=ColumnType.CONSTANT, constant_value="103657"
        ),
        # Spalte N - Text
        "n": ColumnConfig(
            title="Text",
            column_type=ColumnType.CALCULATED,
            calculation_rule="text_with_k_prefix",
            source_column="G",
            max_length=50,
        ),
        # Spalte O - Zuordnung
        "o": ColumnConfig(
            title="Zuordnung",
            column_type=ColumnType.SOURCE_MAPPING,
            source_column="F",
            max_length=18,
        ),
        # Spalte P - Zahlweg
        "p": ColumnConfig(
            title="Zahlweg", column_type=ColumnType.CONSTANT, constant_value="U"
        ),
        # Spalte Q - Zahlungsbed
        "q": ColumnConfig(
            title="Zahlungsbed", column_type=ColumnType.CONSTANT, constant_value="0000"
        ),
        # Spalte R - Mahnbereich (leer)
        "r": ColumnConfig(title="Mahnbereich", column_type=ColumnType.EMPTY),
        # Spalte S - GeschBereich
        "s": ColumnConfig(
            title="GeschBereich", column_type=ColumnType.CONSTANT, constant_value="3400"
        ),
        # Spalte T - Steuerkennz
        "t": ColumnConfig(
            title="Steuerkennz.", column_type=ColumnType.CONSTANT, constant_value="N0"
        ),
        # Spalte U - Soll/Haben (H für K-Zeile, S für S-Zeile)
        "u": ColumnConfig(
            title="Soll/Haben",
            column_type=ColumnType.CALCULATED,
            calculation_rule="soll_haben_by_position",
        ),
        # Spalte V - Betrag Hausw
        "v": ColumnConfig(
            title="Betrag Hausw",
            column_type=ColumnType.SOURCE_MAPPING,
            source_column="B",
        ),
        # Spalte W - Steuerbetrag (leer)
        "w": ColumnConfig(title="Steuerbetrag", column_type=ColumnType.EMPTY),
        # Spalte X - Hauptbuch (H->440000, S->48500199)
        "x": ColumnConfig(
            title="Hauptbuch",
            column_type=ColumnType.CALCULATED,
            calculation_rule="hauptbuch_by_soll_haben",
            k_value="44000000",
            s_value="48500199",
        ),
        # Spalten Y-AD (alle leer)
        "y": ColumnConfig(title="Kostenstelle", column_type=ColumnType.EMPTY),
        "z": ColumnConfig(title="Auftrag", column_type=ColumnType.EMPTY),
        "aa": ColumnConfig(title="PSP-Element", column_type=ColumnType.EMPTY),
        "ab": ColumnConfig(title="Fonds", column_type=ColumnType.EMPTY),
        "ac": ColumnConfig(title="Währung", column_type=ColumnType.EMPTY),
        "ad": ColumnConfig(title="Referenzschl 1", column_type=ColumnType.EMPTY),
        # Spalte AE - GrpId (K/S-Paare aus einer Quellzeile haben dieselbe Nummer)
        "ae": ColumnConfig(
            title="GrpId",
            column_type=ColumnType.CALCULATED,
            calculation_rule="group_id_by_source_row",
        ),
        # Spalten AF-AH (leer)
        "af": ColumnConfig(title="Status", column_type=ColumnType.EMPTY),
        "ag": ColumnConfig(title="Icon", column_type=ColumnType.EMPTY),
        "ah": ColumnConfig(title="Ergebnis", column_type=ColumnType.EMPTY),
        # Spalte AI - Zeile (Sequenz)
        "ai": ColumnConfig(
            title="Zeile", column_type=ColumnType.SEQUENCE, start_value=1
        ),
        # Spalten AJ-AL (leer)
        "aj": ColumnConfig(title="Fehler", column_type=ColumnType.EMPTY),
        "ak": ColumnConfig(title="Warnungen", column_type=ColumnType.EMPTY),
        "al": ColumnConfig(title="Informationen", column_type=ColumnType.EMPTY),
    }

    return TransformationConfig(columns=columns)
