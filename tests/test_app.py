import pytest

from data5580_hw.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.test_client() as c:
        with app.app_context():
            from data5580_hw.services.database.database_client import db
            db.create_all()
        yield c


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json == {"message": "Hello, Flask!"}


# --- User Story 1 & 6: Create user ---
def test_create_user(client):
    response = client.post(
        "/users",
        json={"name": "john", "email": "john@example.com"},
    )
    assert response.status_code == 200
    data = response.json
    assert data["name"] == "john"
    assert data["email"] == "john@example.com"
    assert "id" in data and len(data["id"]) > 0


def test_create_user_duplicate_email(client):
    client.post("/users", json={"name": "john", "email": "john@example.com"})
    response = client.post(
        "/users",
        json={"name": "jane", "email": "john@example.com"},
    )
    assert response.status_code == 400
    assert response.json.get("error") == "email is already in use"


def test_create_user_missing_email(client):
    response = client.post("/users", json={"name": "john"})
    assert response.status_code == 400
    assert "error" in response.json


def test_create_user_invalid_email(client):
    response = client.post(
        "/users",
        json={"name": "john", "email": "not-an-email"},
    )
    assert response.status_code == 400
    assert "error" in response.json


# --- User Story 2: Get user by id ---
def test_get_user_by_id(client):
    create = client.post(
        "/users",
        json={"name": "john", "email": "john@example.com"},
    )
    user_id = create.json["id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json["name"] == "john"
    assert response.json["email"] == "john@example.com"
    assert response.json["id"] == user_id


def test_get_user_not_found(client):
    response = client.get("/users/nonexistent-id")
    assert response.status_code == 404
    assert response.json.get("error") == "User not found"


# --- User Story 5: List all users ---
def test_list_users(client):
    client.post("/users", json={"name": "a", "email": "a@example.com"})
    client.post("/users", json={"name": "b", "email": "b@example.com"})
    response = client.get("/users")
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) == 2


def test_list_users_empty(client):
    response = client.get("/users")
    assert response.status_code == 200
    assert response.json == []


# --- User Story 3 & 7 & 8: Update user ---
def test_update_user(client):
    create = client.post(
        "/users",
        json={"name": "john", "email": "john@example.com"},
    )
    user_id = create.json["id"]
    response = client.patch(
        f"/users/{user_id}",
        json={"name": "John Doe", "email": "john.doe@example.com"},
    )
    assert response.status_code == 200
    data = response.json
    assert data.get("message") == "User details updated successfully."
    assert data["user"]["name"] == "John Doe"
    assert data["user"]["email"] == "john.doe@example.com"
    assert data["user"]["id"] == user_id


def test_update_user_partial(client):
    create = client.post(
        "/users",
        json={"name": "john", "email": "john@example.com"},
    )
    user_id = create.json["id"]
    response = client.patch(f"/users/{user_id}", json={"name": "Johnny"})
    assert response.status_code == 200
    assert response.json["user"]["name"] == "Johnny"
    assert response.json["user"]["email"] == "john@example.com"


def test_update_user_not_found(client):
    response = client.patch(
        "/users/nonexistent-id",
        json={"name": "x", "email": "x@example.com"},
    )
    assert response.status_code == 404
    assert response.json.get("error") == "User not found"


def test_update_user_missing_fields(client):
    create = client.post(
        "/users",
        json={"name": "john", "email": "john@example.com"},
    )
    user_id = create.json["id"]
    response = client.patch(f"/users/{user_id}", json={})
    assert response.status_code == 400
    assert "error" in response.json


def test_update_user_duplicate_email(client):
    client.post("/users", json={"name": "a", "email": "a@example.com"})
    create_b = client.post("/users", json={"name": "b", "email": "b@example.com"})
    user_id_b = create_b.json["id"]
    response = client.patch(
        f"/users/{user_id_b}",
        json={"email": "a@example.com"},
    )
    assert response.status_code == 400
    assert response.json.get("error") == "email is already in use"


# --- User Story 4: Delete user ---
def test_delete_user(client):
    create = client.post(
        "/users",
        json={"name": "john", "email": "john@example.com"},
    )
    user_id = create.json["id"]
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json.get("message") == "User deleted successfully."
    get_resp = client.get(f"/users/{user_id}")
    assert get_resp.status_code == 404


def test_delete_user_not_found(client):
    response = client.delete("/users/nonexistent-id")
    assert response.status_code == 404
    assert response.json.get("error") == "User not found"
