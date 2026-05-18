from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PayrollRow:
    buchungsstelle: str
    abrechnungsmonat_jahr: str
    personalnummer: str
    name: str
    geburtsdatum: str
    im_abrechnungsmonat_brutto: Decimal | None
    im_abrechnungsmonat_summe_monat: Decimal | None
    aufgelaufene_betraege_brutto: Decimal | None
    aufgelaufene_betraege_summe_jahr: Decimal | None
    aus_dokument: str
    seite: int


@dataclass(frozen=True)
class PageContext:
    buchungsstelle: str
    abrechnungsmonat_jahr: str
