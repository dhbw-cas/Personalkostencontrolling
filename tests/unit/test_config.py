from __future__ import annotations

import pytest
from pytest import MonkeyPatch

from dashboard.config import DatabaseConfigError, get_database_url


def test_database_url_normalizes_sliplane_uri(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://user:password@db.example/test?sslmode=verify-full",
    )

    assert get_database_url() == (
        "postgresql+psycopg://user:password@db.example/test?sslmode=verify-full"
    )


def test_database_url_rejects_missing_value(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(DatabaseConfigError, match="nicht gesetzt"):
        get_database_url()


def test_database_url_rejects_other_databases(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.sqlite")

    with pytest.raises(DatabaseConfigError, match="PostgreSQL"):
        get_database_url()


def test_database_url_rejects_invalid_port(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", "postgres://user:password@db.example:ungueltig/test"
    )

    with pytest.raises(DatabaseConfigError, match="ungueltig"):
        get_database_url()
