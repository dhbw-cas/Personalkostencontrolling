from decimal import Decimal

from relelisten_extraktor.models import PageContext
from relelisten_extraktor.parser import _parse_besoldung_rows, _parse_verguetung_rows


def test_parse_besoldung_rows_extracts_required_fields() -> None:
    text = """
Buchungsstelle 7001 /BEIHIL/0701/28/ / /125310
Abrechnungsmonat 11/2025
64878956/322B GEISEL ALFRED P 24.03.65 8523,97 8523,97 93350,58 93350,58
63207349/346D ZENDER CHRISTOP 21.02.65 -22,00 -22,00 -242,00 -242,00
S U M M E -44,00 -44,00 -484,00 -484,00
"""
    context = PageContext(buchungsstelle="7001", abrechnungsmonat_jahr="11-2025")

    rows = _parse_besoldung_rows(text, context, "test_besoldung.pdf", 4)

    assert len(rows) == 2
    assert rows[0].personalnummer == "64878956/322B"
    assert rows[0].name == "GEISEL ALFRED P"
    assert rows[0].geburtsdatum == "24.03.65"
    assert rows[0].im_abrechnungsmonat_brutto == Decimal("8523.97")
    assert rows[0].im_abrechnungsmonat_summe_monat == Decimal("8523.97")
    assert rows[0].aufgelaufene_betraege_brutto == Decimal("93350.58")
    assert rows[0].aufgelaufene_betraege_summe_jahr == Decimal("93350.58")
    assert rows[0].seite == 4


def test_parse_verguetung_rows_extracts_required_fields() -> None:
    text = (
        "BUCHUNGSSTELLE : 7001 / 1010\n"
        "ABRECHNUNGSMONAT 10.25 AM 21.10.25\n"
        "*51237803/426R*GRILL JOACHIM PROF.DR. * 8120.52 1457.89 "
        "451.64 10030.05 * 81712.81 14578.90 4493.09 100784.80 *\n"
        "*50841237/436U*KOFFLER MATTHIAS PROF.DR* 8922.64 1457.89 "
        "418.70 10799.23 * 42634.86 7289.45 2093.50 52017.81 *\n"
        "* / *S U M M E * 17043.16 2915.78 870.34 20829.28 * "
        "124347.67 21868.35 6586.59 152802.61 *\n"
    )
    context = PageContext(buchungsstelle="7001", abrechnungsmonat_jahr="10-2025")

    rows = _parse_verguetung_rows(text, context, "test_verguetung.pdf", 7)

    assert len(rows) == 2
    assert rows[0].personalnummer == "51237803/426R"
    assert rows[0].name == "GRILL JOACHIM PROF.DR."
    assert rows[0].geburtsdatum == ""
    assert rows[0].im_abrechnungsmonat_brutto == Decimal("8120.52")
    assert rows[0].im_abrechnungsmonat_summe_monat == Decimal("10030.05")
    assert rows[0].aufgelaufene_betraege_brutto == Decimal("81712.81")
    assert rows[0].aufgelaufene_betraege_summe_jahr == Decimal("100784.80")
    assert rows[0].seite == 7


def test_parse_besoldung_rows_maps_two_values_to_year_columns() -> None:
    text = """
Buchungsstelle 7003 /1010 /0703/31/ / /320021
Abrechnungsmonat 10/2025
61684239/343A SAUER CLAUDIA 16.05.68 24456,65 24456,65
"""
    context = PageContext(buchungsstelle="7003", abrechnungsmonat_jahr="10-2025")

    rows = _parse_besoldung_rows(text, context, "test_besoldung.pdf", 1)

    assert len(rows) == 1
    assert rows[0].personalnummer == "61684239/343A"
    assert rows[0].im_abrechnungsmonat_brutto is None
    assert rows[0].im_abrechnungsmonat_summe_monat is None
    assert rows[0].aufgelaufene_betraege_brutto == Decimal("24456.65")
    assert rows[0].aufgelaufene_betraege_summe_jahr == Decimal("24456.65")
