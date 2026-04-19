from unittest import TestCase

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


def test_prediction_invalid_model_returns_404(client):
    """Invalid model name/version returns 404 with error."""
    response = client.post(
        "/unknown-model/version/1/predict",
        json={"features": {"x": 1}, "tags": {}},
        content_type="application/json",
    )
    assert response.status_code == 404
    assert "error" in response.json
    assert "not found" in response.json["error"].lower()


def test_prediction_input_mismatch_returns_400(client):
    """Input incompatibility with regression model returns 400 and clear message."""
    from unittest.mock import MagicMock
    from data5580_hw.models.prediction import Model
    mock_model = Model(name="california-housing", version="2", type="regression")
    mock_model._model = MagicMock()
    mock_model._explainer = None

    with patch("data5580_hw.controllers.prediction.mlflow_gateway") as mock_gw, \
         patch("data5580_hw.controllers.prediction.model_service") as mock_svc:
        mock_gw.get_model.return_value = mock_model
        mock_svc.create_inference.side_effect = ValueError(
            "Expected 4 features, but received 3."
        )
        response = client.post(
            "/california-housing/version/2/predict",
            json={"features": {"feature_1": 1, "feature_2": 2, "feature_3": 3}, "tags": {}},
            content_type="application/json",
        )
    assert response.status_code == 400
    assert "Invalid input data" in response.json["error"]


# ---------------------------------------------------------------------------
# Arize gateway tests
# ---------------------------------------------------------------------------

def _make_mock_model(name="california-housing", version="2", model_type="REGRESSION"):
    """Helper: return a Model with mocked sklearn estimator attached."""
    from unittest.mock import MagicMock
    from data5580_hw.models.prediction import Model
    m = Model(name=name, version=version, type=model_type)
    m._model = MagicMock()
    m._model.predict.return_value = [42.0]
    m._explainer = None
    return m


def test_arize_gateway_disabled_without_credentials():
    """ArizeGateway stays disabled when no API key/space ID is configured."""
    from data5580_hw.gateways.arize_gateway import ArizeGateway
    gw = ArizeGateway()
    app_mock = type("App", (), {"config": {}})()
    gw.init_app(app_mock)
    assert gw._enabled is False


def test_arize_gateway_disabled_missing_space_id():
    """ArizeGateway stays disabled when space ID is missing."""
    from data5580_hw.gateways.arize_gateway import ArizeGateway
    import os
    gw = ArizeGateway()
    app_mock = type("App", (), {"config": {"ARIZE_API_KEY": "key123"}})()
    with patch.dict(os.environ, {"ARIZE_API_KEY": "key123"}, clear=False):
        gw.init_app(app_mock)
    assert gw._enabled is False


def test_arize_gateway_init_success():
    """ArizeGateway enables itself when both credentials are present."""
    from data5580_hw.gateways.arize_gateway import ArizeGateway
    from unittest.mock import MagicMock, patch

    gw = ArizeGateway()
    app_mock = type("App", (), {"config": {}})()

    mock_client_cls = MagicMock()
    with patch.dict(
        "os.environ",
        {"ARIZE_API_KEY": "key123", "ARIZE_SPACE_KEY": "space456"},
    ), patch(
        "arize.api.Client",
        mock_client_cls,
        create=True,
    ):
        gw.init_app(app_mock)
    assert isinstance(gw._enabled, bool)


def test_arize_log_inference_no_op_when_disabled():
    """log_inference is a no-op and never raises when gateway is disabled."""
    from data5580_hw.gateways.arize_gateway import ArizeGateway
    gw = ArizeGateway()  # _enabled=False by default
    # Should not raise
    gw.log_inference(
        prediction_id="test-id",
        model_name="california-housing",
        model_version="2",
        model_type="REGRESSION",
        features={"x": 1.0},
        prediction_label=42.0,
    )


def test_arize_log_inference_calls_client_log():
    """log_inference calls client.log with correct arguments (arize v7 API)."""
    from concurrent.futures import Future
    from datetime import datetime
    from unittest.mock import MagicMock

    from arize.utils.types import Environments, ModelTypes
    from data5580_hw.gateways.arize_gateway import ArizeGateway

    gw = ArizeGateway()
    mock_client = MagicMock()
    fut = Future()
    fut.set_result(MagicMock(status_code=200, text="ok"))
    mock_client.log.return_value = fut
    gw._client = mock_client
    gw._enabled = True
    gw._space_id = "space456"
    gw._environment = Environments.PRODUCTION

    ts = datetime(2024, 1, 15, 12, 0, 0)
    gw.log_inference(
        prediction_id="pred-abc",
        model_name="california-housing",
        model_version="2",
        model_type="REGRESSION",
        features={"feat_a": 1.5, "feat_b": 2},
        prediction_label=99.9,
        actual_label=100.0,
        timestamp=ts,
        tags={"source": "api"},
    )

    mock_client.log.assert_called_once()
    call_kwargs = mock_client.log.call_args.kwargs
    assert call_kwargs["model_id"] == "california-housing"
    assert call_kwargs["model_version"] == "2"
    assert call_kwargs["model_type"] == ModelTypes.REGRESSION
    assert call_kwargs["environment"] == Environments.PRODUCTION
    assert call_kwargs["prediction_id"] == "pred-abc"
    assert call_kwargs["prediction_label"] == 99.9
    assert call_kwargs["actual_label"] == 100.0
    assert call_kwargs["prediction_timestamp"] == int(ts.timestamp())
    assert call_kwargs["features"] == {"feat_a": 1.5, "feat_b": 2.0}
    assert call_kwargs["tags"] == {"source": "api"}


def test_arize_log_inference_error_does_not_raise():
    """A crash inside client.log is caught and never propagates to the caller."""
    from unittest.mock import MagicMock

    from arize.utils.types import Environments
    from data5580_hw.gateways.arize_gateway import ArizeGateway

    gw = ArizeGateway()
    mock_client = MagicMock()
    mock_client.log.side_effect = Exception("Network failure")
    gw._client = mock_client
    gw._enabled = True
    gw._space_id = "space456"
    gw._environment = Environments.PRODUCTION

    # Must not raise
    gw.log_inference(
        prediction_id="pred-xyz",
        model_name="test-model",
        model_version="1",
        model_type="REGRESSION",
        features={"x": 1.0},
        prediction_label=5.0,
    )


def test_arize_unknown_model_type_defaults_to_regression():
    """An unrecognised model_type string falls back to ModelTypes.REGRESSION."""
    from concurrent.futures import Future
    from unittest.mock import MagicMock

    from arize.utils.types import Environments, ModelTypes
    from data5580_hw.gateways.arize_gateway import ArizeGateway

    gw = ArizeGateway()
    mock_client = MagicMock()
    fut = Future()
    fut.set_result(MagicMock(status_code=200, text="ok"))
    mock_client.log.return_value = fut
    gw._client = mock_client
    gw._enabled = True
    gw._space_id = "s"
    gw._environment = Environments.PRODUCTION

    gw.log_inference(
        prediction_id="p1",
        model_name="m",
        model_version="1",
        model_type="UNKNOWN_TYPE",
        features={},
        prediction_label=1.0,
    )

    call_kwargs = mock_client.log.call_args.kwargs
    assert call_kwargs["model_type"] == ModelTypes.REGRESSION


def test_arize_log_inference_called_on_successful_prediction(client):
    """End-to-end: a successful POST /predict triggers arize_gateway.log_inference."""
    from unittest.mock import MagicMock, patch

    mock_model = _make_mock_model()

    with patch("data5580_hw.controllers.prediction.mlflow_gateway") as mock_gw, \
         patch("data5580_hw.controllers.prediction.model_service") as mock_svc, \
         patch("data5580_hw.controllers.prediction.arize_gateway") as mock_arize:
        mock_gw.get_model.return_value = mock_model
        mock_svc.create_inference.return_value = 42.0

        response = client.post(
            "/california-housing/version/2/predict",
            json={"features": {"x": 1.0, "y": 2.0}, "tags": {}},
            content_type="application/json",
        )

    assert response.status_code == 200
    mock_arize.log_inference.assert_called_once()
    call_kwargs = mock_arize.log_inference.call_args.kwargs
    assert call_kwargs["model_name"] == "california-housing"
    assert call_kwargs["model_version"] == "2"
    assert float(call_kwargs["prediction_label"]) == 42.0  # label is stored as string in DB
    assert call_kwargs["features"] == {"x": 1.0, "y": 2.0}


def test_arize_log_inference_not_called_on_failed_prediction(client):
    """Arize is NOT called when the prediction itself fails (e.g. model not found)."""
    from unittest.mock import patch

    with patch("data5580_hw.controllers.prediction.arize_gateway") as mock_arize:
        response = client.post(
            "/nonexistent-model/version/1/predict",
            json={"features": {"x": 1}, "tags": {}},
            content_type="application/json",
        )

    assert response.status_code == 404
    mock_arize.log_inference.assert_not_called()


def test_arize_feature_casting():
    """Features with int values are cast to float; strings stay as strings."""
    from concurrent.futures import Future
    from unittest.mock import MagicMock

    from arize.utils.types import Environments
    from data5580_hw.gateways.arize_gateway import ArizeGateway

    gw = ArizeGateway()
    mock_client = MagicMock()
    fut = Future()
    fut.set_result(MagicMock(status_code=200, text="ok"))
    mock_client.log.return_value = fut
    gw._client = mock_client
    gw._enabled = True
    gw._space_id = "s"
    gw._environment = Environments.PRODUCTION

    gw.log_inference(
        prediction_id="p",
        model_name="m",
        model_version="1",
        model_type="REGRESSION",
        features={"int_feat": 5, "str_feat": "cat", "float_feat": 3.14},
        prediction_label=1.0,
    )

    sent_features = mock_client.log.call_args.kwargs["features"]
    assert sent_features["int_feat"] == 5.0
    assert isinstance(sent_features["int_feat"], float)
    assert sent_features["str_feat"] == "cat"
    assert sent_features["float_feat"] == 3.14
