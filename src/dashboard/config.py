from __future__ import annotations

import os

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class DatabaseConfigError(RuntimeError):
    """Die Datenbankkonfiguration fehlt oder ist ungueltig."""


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise DatabaseConfigError(
            "DATABASE_URL ist nicht gesetzt. Bitte die PostgreSQL-Verbindung "
            "als Umgebungsvariable konfigurieren."
        )

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif not database_url.startswith("postgresql+psycopg://"):
        raise DatabaseConfigError(
            "DATABASE_URL muss eine PostgreSQL-Verbindung mit psycopg enthalten."
        )

    try:
        parsed_url = make_url(database_url)
        _ = parsed_url.port
    except (ArgumentError, ValueError) as exc:
        raise DatabaseConfigError("DATABASE_URL ist ungueltig.") from exc
    if not parsed_url.host or not parsed_url.database:
        raise DatabaseConfigError(
            "DATABASE_URL muss Host und Datenbanknamen enthalten."
        )
    return database_url


def get_app_version() -> str | None:
    value = os.environ.get("APP_VERSION") or os.environ.get("SLIPLANE_COMMIT_HASH")
    return value.strip() if value and value.strip() else None
