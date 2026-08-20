from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import ImportFile, ImportRun, Lbv1049Row


@dataclass(slots=True, frozen=True)
class ImportRunSummary:
    id: UUID
    created_at: datetime
    imported_by: str | None
    row_count: int
    filenames: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class Lbv1049RowView:
    row_number: int
    position: str
    betrag: Decimal
    standort: str
    datum_anschreiben: date | None
    quelldatei: str
    abrechnungsstelle: str
    verwendungszweck: str
    buchungsperiode: int | None


def find_duplicate_import(
    session: Session, source_type: str, sha256: str
) -> ImportRun | None:
    statement = (
        select(ImportRun)
        .join(ImportFile)
        .where(
            ImportFile.source_type == source_type,
            ImportFile.sha256 == sha256,
        )
    )
    return session.scalar(statement)


def list_import_runs(
    session: Session, source_type: str, limit: int = 100
) -> list[ImportRunSummary]:
    statement = (
        select(ImportRun)
        .options(selectinload(ImportRun.files))
        .where(ImportRun.source_type == source_type)
        .order_by(ImportRun.created_at.desc())
        .limit(limit)
    )
    runs = session.scalars(statement).unique().all()
    return [
        ImportRunSummary(
            id=run.id,
            created_at=run.created_at,
            imported_by=run.imported_by,
            row_count=run.row_count,
            filenames=tuple(file.original_filename for file in run.files),
        )
        for run in runs
    ]


def list_1049_rows(
    session: Session, import_run_id: UUID, limit: int = 1_000
) -> list[Lbv1049RowView]:
    statement = (
        select(Lbv1049Row)
        .where(Lbv1049Row.import_run_id == import_run_id)
        .order_by(Lbv1049Row.row_number)
        .limit(limit)
    )
    rows = session.scalars(statement).all()
    return [
        Lbv1049RowView(
            row_number=row.row_number,
            position=row.position,
            betrag=row.betrag,
            standort=row.standort,
            datum_anschreiben=row.datum_anschreiben,
            quelldatei=row.quelldatei,
            abrechnungsstelle=row.abrechnungsstelle,
            verwendungszweck=row.verwendungszweck,
            buchungsperiode=row.buchungsperiode,
        )
        for row in rows
    ]
