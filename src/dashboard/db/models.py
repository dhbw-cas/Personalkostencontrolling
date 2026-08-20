from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

SOURCE_TYPES = ("lbv_1049", "rele_1067", "sap_1052")
SOURCE_TYPE_CHECK = "source_type IN ('lbv_1049', 'rele_1067', 'sap_1052')"
JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class ImportRun(Base):
    __tablename__ = "import_runs"
    __table_args__ = (
        CheckConstraint(SOURCE_TYPE_CHECK, name="ck_import_runs_source_type"),
        CheckConstraint("row_count >= 0", name="ck_import_runs_row_count"),
        Index("ix_import_runs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    imported_by: Mapped[str | None] = mapped_column(String(320))
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    app_version: Mapped[str | None] = mapped_column(String(100))

    files: Mapped[list[ImportFile]] = relationship(
        back_populates="import_run", cascade="all, delete-orphan"
    )
    rows_1049: Mapped[list[Lbv1049Row]] = relationship(
        back_populates="import_run", cascade="all, delete-orphan"
    )


class ImportFile(Base):
    __tablename__ = "import_files"
    __table_args__ = (
        CheckConstraint(SOURCE_TYPE_CHECK, name="ck_import_files_source_type"),
        CheckConstraint("file_size >= 0", name="ck_import_files_file_size"),
        UniqueConstraint("source_type", "sha256", name="uq_import_files_source_sha256"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    import_run: Mapped[ImportRun] = relationship(back_populates="files")


class Lbv1049Row(Base):
    __tablename__ = "lbv_1049_rows"
    __table_args__ = (
        CheckConstraint("row_number > 0", name="ck_lbv_1049_rows_row_number"),
        CheckConstraint(
            "buchungsperiode IS NULL OR buchungsperiode BETWEEN 1 AND 12",
            name="ck_lbv_1049_rows_buchungsperiode",
        ),
        UniqueConstraint(
            "import_run_id", "row_number", name="uq_lbv_1049_rows_run_row_number"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    betrag: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    standort: Mapped[str] = mapped_column(Text, nullable=False)
    datum_anschreiben: Mapped[date | None] = mapped_column(Date)
    quelldatei: Mapped[str] = mapped_column(Text, nullable=False)
    abrechnungsstelle: Mapped[str] = mapped_column(Text, nullable=False)
    verwendungszweck: Mapped[str] = mapped_column(Text, nullable=False)
    buchungsperiode: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    import_run: Mapped[ImportRun] = relationship(back_populates="rows_1049")
