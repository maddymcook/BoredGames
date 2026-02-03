import pytest

from data5580_hw.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json == {"message": "Hello, Flask!"}


# def test_add_success(client):
#     response = client.post("/add", json={"a": 2, "b": 3})
#     assert response.status_code == 200
#     assert response.json["result"] == 5


# def test_add_missing_values(client):
#     response = client.post("/add", json={"a": 2})
#     assert response.status_code == 400
#     assert "error" in response.json

def test_create_user(client):
    response = client.post(
        "/user",
        json={"name": "john", "email": "john@example.com"}
    )
    assert response.status_code == 200
    assert response.json["name"] == "john"
    assert response.json["email"] == "john@example.com"


# def test_add_invalid_datatype(client):
#     response = client.post("/add", json={"a": "two", "b": 3})
#     assert response.status_code == 400
#     assert "error" in response.json

def test_missing_attribute(client):
    response = client.post("/user", json={"name": "3"})
    assert response.status_code == 400
    assert "error" in response.json

