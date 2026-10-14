from datetime import date

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    database_path = tmp_path / "test_students.db"
    app = create_app(database_path)
    return TestClient(app), database_path


def sample_student(**overrides):
    data = {
        "name": "Asha Kumar",
        "date_of_birth": "2005-04-12",
        "email": "asha@example.com",
        "phone": "9000000001",
        "course": "ECE",
        "address": "Hassan, Karnataka",
        "enrollment_date": "2024-08-01",
    }
    data.update(overrides)
    return data


def test_health_endpoint(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


def test_create_and_read_student(tmp_path):
    client, _ = make_client(tmp_path)
    created = client.post("/students", json=sample_student())
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["name"] == "Asha Kumar"
    assert body["date_of_birth"] == "2005-04-12"

    fetched = client.get("/students/1")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "asha@example.com"


def test_list_and_filters(tmp_path):
    client, _ = make_client(tmp_path)
    client.post("/students", json=sample_student())
    client.post("/students", json=sample_student(name="Ravi Shetty", date_of_birth="2006-09-24", email=None, phone="9000000002", course="CSE"))

    assert len(client.get("/students").json()) == 2
    assert len(client.get("/students", params={"course": "ECE"}).json()) == 1
    assert len(client.get("/students", params={"name": "ravi"}).json()) == 1
    assert len(client.get("/students", params={"born_after_year": 2005}).json()) == 1


def test_patch_preserves_unmodified_values(tmp_path):
    client, _ = make_client(tmp_path)
    client.post("/students", json=sample_student())
    response = client.patch("/students/1", json={"phone": "9111111111"})
    assert response.status_code == 200
    assert response.json()["phone"] == "9111111111"
    assert response.json()["name"] == "Asha Kumar"


def test_put_replaces_student_details(tmp_path):
    client, _ = make_client(tmp_path)
    client.post("/students", json=sample_student())
    response = client.put(
        "/students/1",
        json=sample_student(name="Asha Updated", email="updated@example.com", phone=None),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Asha Updated"
    assert response.json()["phone"] is None


def test_delete_student(tmp_path):
    client, _ = make_client(tmp_path)
    client.post("/students", json=sample_student())
    response = client.delete("/students/1")
    assert response.status_code == 204
    assert client.get("/students/1").status_code == 404


def test_validation_requires_contact_and_valid_email(tmp_path):
    client, _ = make_client(tmp_path)
    no_contact = sample_student(email=None, phone=None)
    response = client.post("/students", json=no_contact)
    assert response.status_code == 422

    bad_email = sample_student(email="not-an-email")
    response = client.post("/students", json=bad_email)
    assert response.status_code == 422


def test_missing_student_returns_404(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/students/999").status_code == 404
    assert client.patch("/students/999", json={"name": "Nobody"}).status_code == 404
    assert client.delete("/students/999").status_code == 404


def test_data_persists_between_app_instances(tmp_path):
    database_path = tmp_path / "persistent.db"
    client_one = TestClient(create_app(database_path))
    client_one.post("/students", json=sample_student())

    client_two = TestClient(create_app(database_path))
    response = client_two.get("/students/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Asha Kumar"


def test_patch_rejects_null_required_fields(tmp_path):
    client, _ = make_client(tmp_path)
    client.post("/students", json=sample_student())
    assert client.patch("/students/1", json={"name": None}).status_code == 422
    assert client.patch("/students/1", json={"date_of_birth": None}).status_code == 422


def test_patch_cannot_remove_last_contact_method(tmp_path):
    client, _ = make_client(tmp_path)
    client.post("/students", json=sample_student(phone=None))
    response = client.patch("/students/1", json={"email": None})
    assert response.status_code == 422
    assert client.get("/students/1").json()["email"] == "asha@example.com"
