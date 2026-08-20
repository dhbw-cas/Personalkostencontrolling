from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from dashboard.db.base import Base
from dashboard.db.models import ImportRun, Lbv1049Row
from dashboard.imports.contracts import (
    EXPECTED_1049_COLUMNS,
    DataContractError,
    ImportFileMetadata,
)
from dashboard.imports.service import (
    DuplicateImportError,
    ImportService,
    _is_duplicate_constraint,
)


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'imports.sqlite'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _dataframe(*, invalid_second_row: bool = False) -> pd.DataFrame:
    rows = [
        ["Position A", 12.34, "Ort", "20.08.2026", "a.pdf", "7002", "", 8],
        [
            None if invalid_second_row else "Position B",
            -5.67,
            "Ort",
            None,
            "b.pdf",
            "7002",
            "",
            9,
        ],
    ]
    return pd.DataFrame(rows, columns=EXPECTED_1049_COLUMNS)


def _metadata() -> ImportFileMetadata:
    return ImportFileMetadata.from_payload("abrechnungen.zip", b"zip-payload")


def test_save_1049_import_is_visible_in_history(
    session_factory: sessionmaker[Session],
) -> None:
    service = ImportService(session_factory)

    saved = service.save_1049_import(_dataframe(), _metadata())
    history = service.list_1049_imports()
    rows = service.list_1049_rows(saved.id)

    assert saved.row_count == 2
    assert len(history) == 1
    assert history[0].filenames == ("abrechnungen.zip",)
    assert [row.row_number for row in rows] == [1, 2]


def test_save_1049_import_rejects_duplicate_file(
    session_factory: sessionmaker[Session],
) -> None:
    service = ImportService(session_factory)
    service.save_1049_import(_dataframe(), _metadata())

    with pytest.raises(DuplicateImportError, match="bereits importiert"):
        service.save_1049_import(_dataframe(), _metadata())

    with session_factory() as session:
        count = session.scalar(select(func.count()).select_from(ImportRun))
    assert count == 1


def test_invalid_row_creates_no_partial_import(
    session_factory: sessionmaker[Session],
) -> None:
    service = ImportService(session_factory)

    with pytest.raises(DataContractError, match="Position"):
        service.save_1049_import(
            _dataframe(invalid_second_row=True),
            _metadata(),
        )

    with session_factory() as session:
        run_count = session.scalar(select(func.count()).select_from(ImportRun))
        row_count = session.scalar(select(func.count()).select_from(Lbv1049Row))
    assert run_count == 0
    assert row_count == 0


def test_postgresql_duplicate_constraint_is_classified() -> None:
    class Diagnostic:
        constraint_name = "uq_import_files_source_sha256"

    class DatabaseError(Exception):
        diag = Diagnostic()

    error = IntegrityError("INSERT", {}, DatabaseError())

    assert _is_duplicate_constraint(error) is True
