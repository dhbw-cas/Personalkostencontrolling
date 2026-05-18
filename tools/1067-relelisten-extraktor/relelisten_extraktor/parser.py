from __future__ import annotations

import io
import re
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from pypdf import PdfReader

from relelisten_extraktor.io_utils import PdfDocument
from relelisten_extraktor.models import PageContext, PayrollRow


class DocumentType(StrEnum):
    BESOLDUNG = "besoldung"
    VERGUETUNG = "verguetung"


_BUCHUNGSSTELLE_PATTERN = re.compile(
    r"\bBuchungsstelle\s*:?\s*(\d{4})\b", re.IGNORECASE
)
_MONAT_BESOLDUNG_PATTERN = re.compile(
    r"\bAbrechnungsmonat\s+(\d{1,2})/(\d{4})\b", re.IGNORECASE
)
_MONAT_VERGUETUNG_PATTERN = re.compile(
    r"\bABRECHNUNGSMONAT\s+(\d{1,2})\.(\d{2,4})\b", re.IGNORECASE
)
_PERSONALNUMMER_PREFIX_PATTERN = re.compile(r"\b(\d{8}/[0-9A-Z]{3,4})\b")

_BESOLDUNG_ROW_PATTERN = re.compile(
    r"(?m)^\s*(\d{8}/[0-9A-Z]{3,4})\s+"
    r"([A-ZÄÖÜa-zäöüß0-9 .\-/]+?)\s+"
    r"(\d{2}\.\d{2}\.\d{2})\s+"
    r"(-?\d[\d.,]*)\s+"
    r"(-?\d[\d.,]*)"
    r"(?:\s+(-?\d[\d.,]*)\s+(-?\d[\d.,]*))?\s*$"
)

_VERGUETUNG_ROW_PATTERN = re.compile(
    r"\*(\d{8}/[0-9A-Z]{3,4})\*([^*]+)\*"
    r"\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+\*"
    r"\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+\*"
)


def parse_documents(documents: list[PdfDocument]) -> list[PayrollRow]:
    rows: list[PayrollRow] = []
    for document in documents:
        rows.extend(parse_document(document))
    return rows


def parse_document(document: PdfDocument) -> list[PayrollRow]:
    reader = PdfReader(io.BytesIO(document.content))
    document_type = _detect_document_type(document)
    rows: list[PayrollRow] = []
    last_context: PageContext | None = None

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue

        context = _extract_page_context(text, document_type) or last_context
        if context is None:
            continue

        if document_type == DocumentType.BESOLDUNG:
            parsed_rows = _parse_besoldung_rows(
                text, context, document.name, page_number
            )
        else:
            parsed_rows = _parse_verguetung_rows(
                text, context, document.name, page_number
            )

        if parsed_rows:
            rows.extend(parsed_rows)
            last_context = context

    return rows


def _detect_document_type(document: PdfDocument) -> DocumentType:
    lowered_name = document.name.lower()
    if "verguet" in lowered_name or "verg\u00fct" in lowered_name:
        return DocumentType.VERGUETUNG
    if "besold" in lowered_name:
        return DocumentType.BESOLDUNG

    reader = PdfReader(io.BytesIO(document.content))
    first_page_text = (reader.pages[0].extract_text() or "") if reader.pages else ""
    if "BEREICH ENTGELT" in first_page_text or "BUCHUNGSSTELLE :" in first_page_text:
        return DocumentType.VERGUETUNG
    return DocumentType.BESOLDUNG


def _extract_page_context(text: str, document_type: DocumentType) -> PageContext | None:
    buchungsstelle_match = _BUCHUNGSSTELLE_PATTERN.search(text)
    buchungsstelle = buchungsstelle_match.group(1) if buchungsstelle_match else ""

    monat_pattern = (
        _MONAT_BESOLDUNG_PATTERN
        if document_type == DocumentType.BESOLDUNG
        else _MONAT_VERGUETUNG_PATTERN
    )
    monat_match = monat_pattern.search(text)
    if monat_match:
        month, year = monat_match.group(1), monat_match.group(2)
        abrechnungsmonat_jahr = _normalize_month_year(month, year)
    else:
        abrechnungsmonat_jahr = ""

    if not buchungsstelle or not abrechnungsmonat_jahr:
        return None
    return PageContext(
        buchungsstelle=buchungsstelle,
        abrechnungsmonat_jahr=abrechnungsmonat_jahr,
    )


def _parse_besoldung_rows(
    text: str,
    context: PageContext,
    document_name: str,
    page_number: int,
) -> list[PayrollRow]:
    rows: list[PayrollRow] = []
    for match in _BESOLDUNG_ROW_PATTERN.finditer(text):
        (
            personalnummer,
            name,
            geburtsdatum,
            brutto,
            summe_monat,
            jahr_brutto,
            summe_jahr,
        ) = match.groups()
        if not _PERSONALNUMMER_PREFIX_PATTERN.match(personalnummer):
            continue

        rows.append(
            PayrollRow(
                buchungsstelle=context.buchungsstelle,
                abrechnungsmonat_jahr=context.abrechnungsmonat_jahr,
                personalnummer=personalnummer,
                name=_normalize_name(name),
                geburtsdatum=geburtsdatum,
                im_abrechnungsmonat_brutto=_parse_decimal(brutto),
                im_abrechnungsmonat_summe_monat=_parse_decimal(summe_monat),
                aufgelaufene_betraege_brutto=_parse_decimal(jahr_brutto),
                aufgelaufene_betraege_summe_jahr=_parse_decimal(summe_jahr),
                aus_dokument=document_name,
                seite=page_number,
            )
        )
    return rows


def _parse_verguetung_rows(
    text: str,
    context: PageContext,
    document_name: str,
    page_number: int,
) -> list[PayrollRow]:
    rows: list[PayrollRow] = []
    for match in _VERGUETUNG_ROW_PATTERN.finditer(text):
        (
            personalnummer,
            raw_name,
            brutto_monat,
            _ag_anteil_monat,
            _zus_vers_monat,
            summe_monat,
            brutto_jahr,
            _ag_anteil_jahr,
            _zus_vers_jahr,
            summe_jahr,
        ) = match.groups()

        rows.append(
            PayrollRow(
                buchungsstelle=context.buchungsstelle,
                abrechnungsmonat_jahr=context.abrechnungsmonat_jahr,
                personalnummer=personalnummer,
                name=_normalize_name(raw_name),
                geburtsdatum="",
                im_abrechnungsmonat_brutto=_parse_decimal(brutto_monat),
                im_abrechnungsmonat_summe_monat=_parse_decimal(summe_monat),
                aufgelaufene_betraege_brutto=_parse_decimal(brutto_jahr),
                aufgelaufene_betraege_summe_jahr=_parse_decimal(summe_jahr),
                aus_dokument=document_name,
                seite=page_number,
            )
        )
    return rows


def _normalize_month_year(month: str, year: str) -> str:
    month_normalized = f"{int(month):02d}"
    if len(year) == 2:
        year_normalized = f"20{year}"
    else:
        year_normalized = year
    return f"{month_normalized}-{year_normalized}"


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None

    normalized = value.strip().replace(" ", "")
    if not normalized:
        return None

    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None
