"""Create import metadata and 1049 rows.

Revision ID: 20260820_0001
Revises:
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260820_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPE_CHECK = "source_type IN ('lbv_1049', 'rele_1067', 'sap_1052')"


def upgrade() -> None:
    op.create_table(
        "import_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("imported_by", sa.String(length=320), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("app_version", sa.String(length=100), nullable=True),
        sa.CheckConstraint(SOURCE_TYPE_CHECK, name="ck_import_runs_source_type"),
        sa.CheckConstraint("row_count >= 0", name="ck_import_runs_row_count"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_runs_created_at", "import_runs", ["created_at"], unique=False
    )

    op.create_table(
        "import_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(SOURCE_TYPE_CHECK, name="ck_import_files_source_type"),
        sa.CheckConstraint("file_size >= 0", name="ck_import_files_file_size"),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["import_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "sha256", name="uq_import_files_source_sha256"
        ),
    )
    op.create_index(
        "ix_import_files_import_run_id",
        "import_files",
        ["import_run_id"],
        unique=False,
    )

    op.create_table(
        "lbv_1049_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("position", sa.Text(), nullable=False),
        sa.Column("betrag", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("standort", sa.Text(), nullable=False),
        sa.Column("datum_anschreiben", sa.Date(), nullable=True),
        sa.Column("quelldatei", sa.Text(), nullable=False),
        sa.Column("abrechnungsstelle", sa.Text(), nullable=False),
        sa.Column("verwendungszweck", sa.Text(), nullable=False),
        sa.Column("buchungsperiode", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "buchungsperiode IS NULL OR buchungsperiode BETWEEN 1 AND 12",
            name="ck_lbv_1049_rows_buchungsperiode",
        ),
        sa.CheckConstraint("row_number > 0", name="ck_lbv_1049_rows_row_number"),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["import_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_run_id",
            "row_number",
            name="uq_lbv_1049_rows_run_row_number",
        ),
    )
    op.create_index(
        "ix_lbv_1049_rows_import_run_id",
        "lbv_1049_rows",
        ["import_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_lbv_1049_rows_import_run_id", table_name="lbv_1049_rows")
    op.drop_table("lbv_1049_rows")
    op.drop_index("ix_import_files_import_run_id", table_name="import_files")
    op.drop_table("import_files")
    op.drop_index("ix_import_runs_created_at", table_name="import_runs")
    op.drop_table("import_runs")
