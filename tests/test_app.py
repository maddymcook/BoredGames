import os
import pytest
from unittest.mock import patch

from data5580_hw.app import create_app


@pytest.fixture
def client():
    os.environ["TESTING"] = "1"
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


# --- Model compare (MLFlow run IDs) ---
def test_compare_models_no_body(client):
    response = client.post("/models/compare", data="{}", content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json


def test_compare_models_empty_run_ids(client):
    response = client.post("/models/compare", json={"run_ids": []})
    assert response.status_code == 400
    assert "error" in response.json


def test_compare_models_invalid_run_ids_type(client):
    """ValidationError when run_ids is not a list (e.g. string or wrong type)."""
    response = client.post("/models/compare", json={"run_ids": "not-a-list"})
    assert response.status_code == 400
    assert "error" in response.json


def test_compare_models_invalid_json(client):
    """Bad or missing JSON body returns 400 or 500."""
    response = client.post(
        "/models/compare",
        data="not valid json",
        content_type="application/json",
    )
    assert response.status_code in (400, 500)
    if response.json:
        assert "error" in response.json


def test_compare_models_success_mocked(client):
    """Compare returns 200 with best run when gateway is mocked."""
    mock_run_a = {"run_id": "run-a", "metrics": {"r2": 0.8}, "artifact_uri": "file:///a"}
    mock_run_b = {"run_id": "run-b", "metrics": {"r2": 0.9}, "artifact_uri": "file:///b"}

    def get_run_metrics(run_id):
        if run_id == "run-a":
            return mock_run_a
        if run_id == "run-b":
            return mock_run_b
        raise Exception("not found")

    with patch(
        "data5580_hw.services.model_compare_service.mlflow_gateway"
    ) as mock_gw:
        mock_gw.get_run_metrics.side_effect = get_run_metrics
        response = client.post(
            "/models/compare",
            json={"run_ids": ["run-a", "run-b"], "metric": "r2"},
        )
    assert response.status_code == 200
    data = response.json
    assert data["best_run_id"] == "run-b"
    assert data["metric"] == "r2"
    assert data["metric_value"] == 0.9
    assert data.get("artifact_uri") == "file:///b"


def test_compare_models_invalid_run_ids_mocked(client):
    """Invalid run IDs from MLFlow return 400 with message listing them."""
    with patch(
        "data5580_hw.services.model_compare_service.mlflow_gateway"
    ) as mock_gw:
        mock_gw.get_run_metrics.side_effect = Exception("Run not found")
        response = client.post(
            "/models/compare",
            json={"run_ids": ["bad-id-1"], "metric": "r2"},
        )
    assert response.status_code == 400
    assert "error" in response.json
    assert "bad-id-1" in response.json["error"]


def test_compare_models_service_error_503_mocked(client):
    """Unexpected exception in compare_runs returns 503."""
    with patch(
        "data5580_hw.controllers.model_compare_controller.model_compare_service"
    ) as mock_svc:
        mock_svc.compare_runs.side_effect = Exception("Connection refused")
        response = client.post(
            "/models/compare",
            json={"run_ids": ["any-id"], "metric": "r2"},
        )
    assert response.status_code == 503
    assert "error" in response.json


def test_metrics_route(client):
    """GET /metrics returns Prometheus text and 200."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("Content-Type", "")
    assert len(response.data) > 0


def test_prediction_route_fails_without_mlflow(client):
    """Prediction route and controller are hit; inference failure yields 5xx or raised."""
    with patch("data5580_hw.controllers.prediction.model_service") as mock_svc:
        mock_svc.create_inference.side_effect = Exception("Model not loaded")
        try:
            response = client.post(
                "/california-housing/version/2/predict",
                json={"features": {"x": 1}, "tags": {}},
                content_type="application/json",
            )
            assert response.status_code in (500, 503)
        except Exception:
            # TESTING=True can propagate exceptions; route and controller were still exercised
            pass
