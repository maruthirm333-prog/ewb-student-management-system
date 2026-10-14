"""Optional Ollama integration. Database queries are executed by Python, not by the LLM."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import requests

from app.database import connect, resolve_database_path


@dataclass
class RetrievedContext:
    """Safe, pre-retrieved database information supplied to the local model."""

    description: str
    records: list[dict[str, Any]]
    total_count: int | None = None


def retrieve_student_context(question: str, database_path: str | None = None) -> RetrievedContext:
    """Use a few safe question patterns to retrieve database information.

    The model never receives database access or permission to run SQL. For questions
    that match a supported pattern, Python runs fixed parameterized SQL. Other
    questions receive a bounded list of records as context.
    """
    normalized = question.lower()
    path = resolve_database_path(database_path)

    year_match = re.search(r"(?:born|birth|date of birth)\s+(?:in|after|before)\s+(19\d{2}|20\d{2})", normalized)
    # Also support common wording such as "students after 2005".
    if year_match is None:
        year_match = re.search(r"\bafter\s+(19\d{2}|20\d{2})\b", normalized)
    year = int(year_match.group(1)) if year_match else None

    asks_after = year is not None and ("after" in normalized or "older than" in normalized)
    asks_before = year is not None and "before" in normalized
    asks_count = any(term in normalized for term in ("how many", "count", "number of students", "total students"))
    asks_list = any(term in normalized for term in ("list", "show", "display", "which students", "who are"))

    with connect(path) as connection:
        if year is not None and (asks_after or asks_before):
            comparison = ">" if asks_after else "<"
            boundary = f"{year}-12-31" if asks_after else f"{year}-01-01"
            label = f"students born {'after' if asks_after else 'before'} {year}"
            if asks_count:
                total = connection.execute(
                    f"SELECT COUNT(*) FROM students WHERE date_of_birth {comparison} ?", (boundary,)
                ).fetchone()[0]
                return RetrievedContext(
                    description=f"Filtered database count: {total} student(s) were born {'after' if asks_after else 'before'} {year}.",
                    records=[],
                    total_count=int(total),
                )
            sql = f"SELECT * FROM students WHERE date_of_birth {comparison} ? ORDER BY id LIMIT 100"
            rows = connection.execute(sql, (boundary,)).fetchall()
            records = [dict(row) for row in rows]
            return RetrievedContext(
                description=f"Filtered result: {label}. Rows returned: {len(records)}. Maximum 100 rows.",
                records=records,
                total_count=len(records),
            )

        if asks_count:
            total = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            return RetrievedContext(
                description=f"Database count query result: there are {total} student record(s).",
                records=[],
                total_count=int(total),
            )

        # For other questions, provide only a bounded, read-only context.
        rows = connection.execute("SELECT * FROM students ORDER BY id LIMIT 100").fetchall()
        records = [dict(row) for row in rows]
        if asks_list:
            description = f"Student list retrieved from the database. Records returned: {len(records)}. Maximum 100 records."
        else:
            description = f"Relevant context available: up to {len(records)} student records, ordered by ID. Maximum 100 records."
        return RetrievedContext(description=description, records=records, total_count=len(records))


def ask_ollama(question: str, database_path: str | None = None) -> dict[str, Any]:
    """Ask a local Ollama model using backend-retrieved records as context."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    context = retrieve_student_context(question, database_path)
    safe_context = {
        "retrieval_description": context.description,
        "total_count": context.total_count,
        "student_records": context.records,
    }

    prompt = (
        "You are a helpful assistant answering questions about a student database.\n"
        "Use only the database context below. Do not invent student records or facts.\n"
        "If the context does not contain the answer, say that the available records do not show it.\n"
        "Do not write or execute SQL. Do not request unrestricted database access.\n\n"
        f"Database context (JSON):\n{json.dumps(safe_context, default=str, ensure_ascii=False)}\n\n"
        f"User question: {question}\n\n"
        "Give a brief, clear answer in simple English."
    )

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=(5, 120),
        )
        response.raise_for_status()
        body = response.json()
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Install and start Ollama, then download the model "
            f"'{model}'. The core CRUD application works without this optional feature."
        ) from exc
    except requests.Timeout as exc:
        raise RuntimeError("Ollama took too long to respond. Try again or use a smaller model.") from exc
    except requests.HTTPError as exc:
        detail = "Ollama returned an error. Check that Ollama is running and the selected model is installed."
        try:
            detail = response.json().get("error", detail)
        except Exception:
            pass
        raise RuntimeError(detail) from exc
    except (ValueError, requests.RequestException) as exc:
        raise RuntimeError("Could not read a valid response from Ollama.") from exc

    answer = body.get("response", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty answer. Please try again.")
    return {
        "answer": answer,
        "model": model,
        "records_used": len(context.records),
        "note": "The backend retrieved database context first; the AI did not execute SQL.",
    }
