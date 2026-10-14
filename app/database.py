"""SQLite database helpers for the Student Management System."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "students.db"


def resolve_database_path(path: str | Path | None = None) -> Path:
    """Resolve a database path from an explicit path or environment setting."""
    if path is not None:
        return Path(path).expanduser().resolve()
    configured_path = os.getenv("STUDENT_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATABASE_PATH.resolve()


@contextmanager
def connect(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a database connection and safely commit or roll back a transaction."""
    path = resolve_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: str | Path | None = None) -> None:
    """Create the student table if it does not already exist."""
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                date_of_birth TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (email IS NOT NULL OR phone IS NOT NULL)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_students_course ON students(course)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_students_date_of_birth ON students(date_of_birth)"
        )


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """Convert one SQLite row to a regular dictionary."""
    return dict(row) if row is not None else None
