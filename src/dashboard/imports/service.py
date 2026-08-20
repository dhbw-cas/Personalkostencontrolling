from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from dashboard.db.models import ImportFile, ImportRun, Lbv1049Row
from dashboard.db.repositories import (
    ImportRunSummary,
    Lbv1049RowView,
    find_duplicate_import,
    list_1049_rows,
    list_import_runs,
)

from .contracts import SOURCE_TYPE_1049, ImportFileMetadata
from .mapper_1049 import map_1049_dataframe


class DuplicateImportError(RuntimeError):
    """Die Upload-Datei wurde fuer diese Quelle bereits importiert."""


class ImportPersistenceError(RuntimeError):
    """Der Import konnte nicht vollstaendig gespeichert oder gelesen werden."""


@dataclass(slots=True, frozen=True)
class SavedImport:
    id: UUID
    created_at: datetime
    row_count: int


class ImportService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_1049_import(
        self,
        dataframe: pd.DataFrame,
        file_metadata: ImportFileMetadata,
        *,
        imported_by: str | None = None,
        parameters: dict[str, Any] | None = None,
        app_version: str | None = None,
    ) -> SavedImport:
        records = map_1049_dataframe(dataframe)
        try:
            with self._session_factory.begin() as session:
                duplicate = find_duplicate_import(
                    session, SOURCE_TYPE_1049, file_metadata.sha256
                )
                if duplicate is not None:
                    raise DuplicateImportError(
                        "Diese ZIP-Datei wurde bereits importiert. "
                        f"Import-ID: {duplicate.id}"
                    )

                import_run = ImportRun(
                    source_type=SOURCE_TYPE_1049,
                    imported_by=imported_by,
                    row_count=len(records),
                    status="completed",
                    parameters=dict(parameters or {}),
                    app_version=app_version,
                )
                import_run.files.append(
                    ImportFile(
                        source_type=SOURCE_TYPE_1049,
                        original_filename=file_metadata.original_filename,
                        sha256=file_metadata.sha256,
                        file_size=file_metadata.file_size,
                    )
                )
                import_run.rows_1049.extend(
                    Lbv1049Row(
                        row_number=record.row_number,
                        position=record.position,
                        betrag=record.betrag,
                        standort=record.standort,
                        datum_anschreiben=record.datum_anschreiben,
                        quelldatei=record.quelldatei,
                        abrechnungsstelle=record.abrechnungsstelle,
                        verwendungszweck=record.verwendungszweck,
                        buchungsperiode=record.buchungsperiode,
                    )
                    for record in records
                )
                session.add(import_run)
                session.flush()
                saved_import = SavedImport(
                    id=import_run.id,
                    created_at=import_run.created_at,
                    row_count=import_run.row_count,
                )
        except DuplicateImportError:
            raise
        except IntegrityError as exc:
            if _is_duplicate_constraint(exc):
                raise DuplicateImportError(
                    "Diese ZIP-Datei wurde bereits importiert."
                ) from exc
            raise ImportPersistenceError(
                "Der Import verletzt eine Datenbankregel und wurde verworfen."
            ) from exc
        except SQLAlchemyError as exc:
            raise ImportPersistenceError(
                "Der Import konnte nicht gespeichert werden."
            ) from exc

        return saved_import

    def list_1049_imports(self, limit: int = 100) -> list[ImportRunSummary]:
        try:
            with self._session_factory() as session:
                return list_import_runs(session, SOURCE_TYPE_1049, limit=limit)
        except SQLAlchemyError as exc:
            raise ImportPersistenceError(
                "Die Importhistorie konnte nicht geladen werden."
            ) from exc

    def list_1049_rows(
        self, import_run_id: UUID, limit: int = 1_000
    ) -> list[Lbv1049RowView]:
        try:
            with self._session_factory() as session:
                return list_1049_rows(session, import_run_id, limit=limit)
        except SQLAlchemyError as exc:
            raise ImportPersistenceError(
                "Die gespeicherten Positionen konnten nicht geladen werden."
            ) from exc


def _is_duplicate_constraint(exc: IntegrityError) -> bool:
    constraint_name = "uq_import_files_source_sha256"
    diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
    if getattr(diagnostic, "constraint_name", None) == constraint_name:
        return True
    return constraint_name in str(exc)
