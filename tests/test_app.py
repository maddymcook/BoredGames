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


def test_create_user(client):
    response = client.post("/user", json={"email": "test@example.com", "name": "test"})
    assert response.status_code == 200



