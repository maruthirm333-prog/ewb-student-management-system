"""FastAPI application for the EWB Student Management System assignment."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.ai_extension import ask_ollama
from app.database import connect, initialize_database, resolve_database_path, row_to_dict
from app.schemas import (
    AskQuestionRequest,
    AskQuestionResponse,
    StudentCreate,
    StudentRead,
    StudentUpdate,
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_student_read(record: dict[str, Any]) -> StudentRead:
    """Validate and serialize database records through the response schema."""
    return StudentRead.model_validate(record)


def create_app(database_path: str | Path | None = None) -> FastAPI:
    """Create an app; accepting a database path makes tests isolated and repeatable."""
    resolved_path = resolve_database_path(database_path)
    initialize_database(resolved_path)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # The database is initialized when create_app is called; kept as a place
        # for future startup/shutdown resources if the project grows.
        yield

    app = FastAPI(
        title="Student Management System API",
        version="1.0.0",
        description=(
            "A beginner-friendly student CRUD API built with Python, FastAPI and SQLite. "
            "The local Ollama question-answering endpoint is optional."
        ),
        lifespan=lifespan,
    )
    app.state.database_path = str(resolved_path)

    # Safe default for local development. In production, restrict allowed origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.get("/", tags=["General"])
    def root() -> dict[str, str]:
        return {
            "message": "Welcome to the Student Management System API",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", tags=["General"])
    def health() -> dict[str, str]:
        with connect(app.state.database_path) as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "healthy", "database": "connected"}

    @app.post(
        "/students",
        response_model=StudentRead,
        status_code=status.HTTP_201_CREATED,
        tags=["Students"],
        summary="Create a student",
    )
    def create_student(payload: StudentCreate) -> StudentRead:
        values = payload.model_dump(mode="json")
        now = _now_utc()
        with connect(app.state.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO students
                    (name, date_of_birth, email, phone, course, address, enrollment_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["name"],
                    values["date_of_birth"],
                    values["email"],
                    values["phone"],
                    values["course"],
                    values["address"],
                    values["enrollment_date"],
                    now,
                    now,
                ),
            )
            record = row_to_dict(
                connection.execute("SELECT * FROM students WHERE id = ?", (cursor.lastrowid,)).fetchone()
            )
        return _as_student_read(record or {})

    @app.get("/students", response_model=list[StudentRead], tags=["Students"], summary="List and filter students")
    def list_students(
        name: str | None = Query(default=None, min_length=1, max_length=100, description="Partial name match"),
        course: str | None = Query(default=None, min_length=1, max_length=100),
        born_after_year: int | None = Query(default=None, ge=1900, le=2100),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[StudentRead]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if name:
            conditions.append("LOWER(name) LIKE LOWER(?)")
            parameters.append(f"%{name.strip()}%")
        if course:
            conditions.append("LOWER(course) = LOWER(?)")
            parameters.append(course.strip())
        if born_after_year is not None:
            conditions.append("date_of_birth > ?")
            parameters.append(f"{born_after_year}-12-31")
        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        parameters.extend([limit, offset])
        with connect(app.state.database_path) as connection:
            rows = connection.execute(
                f"SELECT * FROM students{where_clause} ORDER BY id LIMIT ? OFFSET ?", parameters
            ).fetchall()
        return [_as_student_read(dict(row)) for row in rows]

    @app.get(
        "/students/{student_id}",
        response_model=StudentRead,
        tags=["Students"],
        summary="Get one student",
    )
    def get_student(student_id: int) -> StudentRead:
        with connect(app.state.database_path) as connection:
            record = row_to_dict(
                connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            )
        if record is None:
            raise HTTPException(status_code=404, detail=f"Student with ID {student_id} was not found")
        return _as_student_read(record)

    @app.put(
        "/students/{student_id}",
        response_model=StudentRead,
        tags=["Students"],
        summary="Replace a student's details",
    )
    def replace_student(student_id: int, payload: StudentCreate) -> StudentRead:
        values = payload.model_dump(mode="json")
        with connect(app.state.database_path) as connection:
            exists = connection.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
            if exists is None:
                raise HTTPException(status_code=404, detail=f"Student with ID {student_id} was not found")
            connection.execute(
                """
                UPDATE students
                SET name = ?, date_of_birth = ?, email = ?, phone = ?, course = ?, address = ?,
                    enrollment_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values["name"], values["date_of_birth"], values["email"], values["phone"],
                    values["course"], values["address"], values["enrollment_date"], _now_utc(), student_id,
                ),
            )
            record = row_to_dict(
                connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            )
        return _as_student_read(record or {})

    @app.patch(
        "/students/{student_id}",
        response_model=StudentRead,
        tags=["Students"],
        summary="Update selected student fields",
    )
    def patch_student(student_id: int, payload: StudentUpdate) -> StudentRead:
        updates = payload.model_dump(mode="json", exclude_unset=True)
        with connect(app.state.database_path) as connection:
            existing_row = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            if existing_row is None:
                raise HTTPException(status_code=404, detail=f"Student with ID {student_id} was not found")
            current = dict(existing_row)
            merged = {**current, **updates}
            if not merged.get("email") and not merged.get("phone"):
                raise HTTPException(status_code=422, detail="A student must have an email address or phone number")
            if "date_of_birth" in merged and isinstance(merged["date_of_birth"], date):
                merged["date_of_birth"] = merged["date_of_birth"].isoformat()
            if merged.get("enrollment_date") and isinstance(merged["enrollment_date"], date):
                merged["enrollment_date"] = merged["enrollment_date"].isoformat()
            connection.execute(
                """
                UPDATE students
                SET name = ?, date_of_birth = ?, email = ?, phone = ?, course = ?, address = ?,
                    enrollment_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    merged["name"], merged["date_of_birth"], merged.get("email"), merged.get("phone"),
                    merged.get("course"), merged.get("address"), merged.get("enrollment_date"), _now_utc(), student_id,
                ),
            )
            record = row_to_dict(
                connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            )
        return _as_student_read(record or {})

    @app.delete(
        "/students/{student_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        tags=["Students"],
        summary="Delete a student",
    )
    def delete_student(student_id: int) -> Response:
        with connect(app.state.database_path) as connection:
            cursor = connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Student with ID {student_id} was not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/students/ask",
        response_model=AskQuestionResponse,
        tags=["Optional AI"],
        summary="Ask a natural-language question about student records using local Ollama",
    )
    def ask_about_students(payload: AskQuestionRequest) -> AskQuestionResponse:
        try:
            result = ask_ollama(payload.question, app.state.database_path)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return AskQuestionResponse(**result)

    return app


app = create_app()
