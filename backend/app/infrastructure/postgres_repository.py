"""PostgreSQL repository bootstrap.

The application remains repository-driven: production deployments can point the
same domain contracts at PostgreSQL without coupling the domain to SQL.
"""
from __future__ import annotations

import os


class PostgresUnavailable(RuntimeError):
    pass


class PostgresRepositoryFactory:
    """Lazy PostgreSQL factory; keeps psycopg optional for SQLite-only installs."""

    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("AICF_POSTGRES_DSN", "")

    @property
    def configured(self) -> bool:
        return bool(self.dsn.strip())

    def connect(self):
        if not self.configured:
            raise PostgresUnavailable("AICF_POSTGRES_DSN is not configured")
        try:
            import psycopg
        except ImportError as exc:
            raise PostgresUnavailable("Install psycopg to enable PostgreSQL runtime") from exc
        return psycopg.connect(self.dsn)
