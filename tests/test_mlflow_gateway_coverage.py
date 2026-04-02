import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from data5580_hw.gateways.mlflow_gateway import MLFlowGateway


def _models_payload():
    return {
        "california-housing": {
            "1": {"model": None, "model_type": "REGRESSION", "mlflow_flavor": "sklearn"}
        }
    }


def test_init_app_loads_model_and_optional_explainer(monkeypatch):
    # MLFlowGateway.init_app short-circuits if either app.config["TESTING"]
    # OR os.environ["TESTING"] is set. Clear the env var to ensure we
    # actually exercise the "real" init_app loading path.
    monkeypatch.delenv("TESTING", raising=False)

    gw = MLFlowGateway()

    app = SimpleNamespace(
        config={
            "TESTING": False,
            "TRACKING_URI": "http://localhost:8080",
            "MODELS": _models_payload(),
        }
    )

    mock_response = SimpleNamespace(status_code=200)
    mock_client = MagicMock()
    mock_client.get_model_version.return_value = SimpleNamespace(run_id="run123")

    mock_run = SimpleNamespace(
        outputs=SimpleNamespace(
            model_outputs=[SimpleNamespace(model_id="model-out-1")]
        )
    )

    mock_logged_model = SimpleNamespace(
        name="model-explainer",
        model_uri="uri://explainer",
    )

    mock_pyfunc = SimpleNamespace(load_model=MagicMock(return_value="sentinel_explainer"))

    with patch("data5580_hw.gateways.mlflow_gateway.requests.get", return_value=mock_response), patch(
        "data5580_hw.gateways.mlflow_gateway.mlflow.set_tracking_uri"
    ), patch(
        "data5580_hw.gateways.mlflow_gateway.MlflowClient",
        return_value=mock_client,
    ), patch(
        "data5580_hw.gateways.mlflow_gateway.mlflow.get_run",
        return_value=mock_run,
    ) as mock_get_run, patch(
        "data5580_hw.gateways.mlflow_gateway.mlflow.get_logged_model",
        return_value=mock_logged_model,
    ) as mock_get_logged_model, patch(
        "data5580_hw.gateways.mlflow_gateway.mlflow.pyfunc",
        new=mock_pyfunc,
    ), patch(
        "data5580_hw.gateways.mlflow_gateway.MLFlowGateway._load_model",
        return_value="sentinel_model",
    ):
        gw.init_app(app)

    assert mock_get_run.called
    assert mock_get_logged_model.called
    assert gw.models["california-housing"]["1"]["model"] == "sentinel_model"
    assert mock_pyfunc.load_model.called
    assert gw.models["california-housing"]["1"]["explainer"] == "sentinel_explainer"


def test_init_app_request_failure_leaves_models_untouched(monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)

    gw = MLFlowGateway()

    models = _models_payload()
    app = SimpleNamespace(
        config={
            "TESTING": False,
            "TRACKING_URI": "http://localhost:8080",
            "MODELS": models,
        }
    )

    mock_client_cls = MagicMock()

    with patch(
        "data5580_hw.gateways.mlflow_gateway.requests.get",
        side_effect=RuntimeError("connection refused"),
    ), patch(
        "data5580_hw.gateways.mlflow_gateway.mlflow.set_tracking_uri"
    ), patch(
        "data5580_hw.gateways.mlflow_gateway.MlflowClient",
        mock_client_cls,
    ):
        gw.init_app(app)

    # init_app should return early and not populate models
    assert gw.models["california-housing"]["1"]["model"] is None
    assert mock_client_cls.call_count == 0


def test_load_model_unsupported_flavor_raises():
    gw = MLFlowGateway()
    with pytest.raises(ValueError, match="Unsupported model flavor"):
        gw._load_model("models:/x/1", "definitely-not-a-flavor")


def test_get_run_metrics_returns_expected_payload():
    gw = MLFlowGateway()

    mock_client = MagicMock()
    mock_run = SimpleNamespace(
        info=SimpleNamespace(run_id="run1", artifact_uri="file:///art"),
        data=SimpleNamespace(metrics={"r2": 0.9}),
    )
    mock_client.get_run.return_value = mock_run

    with patch(
        "data5580_hw.gateways.mlflow_gateway.MlflowClient",
        return_value=mock_client,
    ):
        payload = gw.get_run_metrics("run1")

    assert payload["run_id"] == "run1"
    assert payload["artifact_uri"] == "file:///art"
    assert payload["metrics"] == {"r2": 0.9}

