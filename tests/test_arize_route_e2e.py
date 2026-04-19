import os
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from data5580_hw.app import create_app
from data5580_hw.gateways.arize_gateway import _SDK_BACKEND_LEGACY
from tests.arize_compat import arize_client_patch_target


@pytest.fixture
def client_with_arize_env(monkeypatch):
    # Keep TESTING=1 so MLflowGateway.init_app() doesn't try to download/load models.
    monkeypatch.setenv("TESTING", "1")

    monkeypatch.setenv("ARIZE_ENABLED", "1")
    monkeypatch.setenv("ARIZE_API_KEY", "dummy-api-key")
    monkeypatch.setenv("ARIZE_SPACE_KEY", "test-space-id")
    monkeypatch.setenv("ARIZE_ENVIRONMENT", "production")

    # Patch arize.api.Client during app creation so ArizeGateway.init_app() uses the mock.
    mock_arize_client = MagicMock()
    _fut = Future()
    _fut.set_result(MagicMock(status_code=200, text="ok"))
    mock_arize_client.log = MagicMock(return_value=_fut)
    mock_arize_client.log_stream = MagicMock(return_value=_fut)

    with patch(
        arize_client_patch_target(),
        return_value=mock_arize_client,
    ), patch("data5580_hw.app.load_dotenv", return_value=None):
        app = create_app()

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.test_client() as c:
        with app.app_context():
            from data5580_hw.services.database.database_client import db

            db.create_all()
        yield c, mock_arize_client


def test_predict_route_triggers_arize_log(monkeypatch, client_with_arize_env):
    # Patch arize.api.Client so we don't need network/real credentials.
    client, mock_arize_client = client_with_arize_env

    fake_model_payload = {
        "name": "california-housing",
        "version": "1",
        "type": "REGRESSION",
    }

    # Features are arbitrary here; model inference is mocked.
    prediction_payload = {
        "features": {"f1": 1.0, "f2": 2.0},
        "tags": {"source": "test-e2e"},
        "actual": 2.25,
    }

    # Create a real Model instance via pydantic so DB serialization works.
    from data5580_hw.models.prediction import Model

    fake_model = Model(**fake_model_payload)
    fake_model._explainer = None

    with patch(
        "data5580_hw.controllers.prediction.mlflow_gateway.get_model",
        return_value=fake_model,
    ), patch(
        "data5580_hw.controllers.prediction.model_service.create_inference",
        return_value=10.5,
    ), patch(
        "data5580_hw.controllers.prediction.umap_embedding_service.compute_embeddings",
        return_value=[[0.1, 0.2]],
    ):
        # The module-global ArizeGateway instance is initialized during create_app(),
        # but other tests/env state can affect its internal flags. Force it on
        # and point it at our mock so the route actually exercises Arize logging.
        from data5580_hw.gateways.arize_gateway import arize_gateway as arize_gw_instance

        arize_gw_instance._enabled = True
        arize_gw_instance._client = mock_arize_client
        arize_gw_instance._sdk_backend = _SDK_BACKEND_LEGACY

        resp = client.post(
            "/california-housing/version/1/predict",
            json=prediction_payload,
        )

    assert resp.status_code == 200
    mock_arize_client.log.assert_called_once()
    call_kw = mock_arize_client.log.call_args[1]

    assert call_kw["model_id"] == "california-housing"
    assert call_kw["model_version"] == "1"
    assert call_kw["prediction_label"] == 10.5
    assert call_kw["actual_label"] == 2.25

