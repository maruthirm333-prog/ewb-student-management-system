from fastapi.testclient import TestClient

from app.main import create_app
from app.ai_extension import retrieve_student_context


def sample_student(name, dob, email):
    return {
        "name": name,
        "date_of_birth": dob,
        "email": email,
        "course": "ECE",
    }


def test_ai_context_filters_students_born_after_year(tmp_path):
    db = tmp_path / "ai_context.db"
    client = TestClient(create_app(db))
    client.post("/students", json=sample_student("Older Student", "2004-10-10", "older@example.com"))
    client.post("/students", json=sample_student("Newer Student", "2006-03-10", "newer@example.com"))

    context = retrieve_student_context("List students born after 2005", str(db))
    assert context.total_count == 1
    assert context.records[0]["name"] == "Newer Student"


def test_ai_context_counts_students(tmp_path):
    db = tmp_path / "ai_count.db"
    client = TestClient(create_app(db))
    client.post("/students", json=sample_student("Student One", "2004-10-10", "one@example.com"))
    client.post("/students", json=sample_student("Student Two", "2006-03-10", "two@example.com"))

    context = retrieve_student_context("How many students are there?", str(db))
    assert context.total_count == 2
    assert context.records == []
    assert "there are 2" in context.description


def test_optional_ai_endpoint_reports_clear_error_when_ollama_not_running(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")
    client = TestClient(create_app(tmp_path / "missing_ollama.db"))
    response = client.post("/students/ask", json={"question": "How many students are there?"})
    assert response.status_code == 503
    assert "Cannot connect to Ollama" in response.json()["detail"]


def test_ai_context_counts_only_matching_birth_years(tmp_path):
    db = tmp_path / "ai_filtered_count.db"
    client = TestClient(create_app(db))
    client.post("/students", json=sample_student("Older Student", "2004-10-10", "older@example.com"))
    client.post("/students", json=sample_student("Newer Student", "2006-03-10", "newer@example.com"))

    context = retrieve_student_context("How many students were born after 2005?", str(db))
    assert context.total_count == 1
    assert "1 student" in context.description
