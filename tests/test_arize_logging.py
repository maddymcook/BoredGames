"""Unit tests for Arize inference logging."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from data5580_hw.controllers.prediction import _should_log_arize_request
from data5580_hw.gateways.arize_gateway import ArizeGateway, _normalize_arize_space_id
from data5580_hw.models.prediction import Model, Prediction


@pytest.fixture
def regression_model() -> Model:
    return Model(name="california-housing", version="2", type="REGRESSION")


@pytest.fixture
def sample_prediction(regression_model: Model) -> Prediction:
    p = Prediction(features={"MedInc": 3.0, "HouseAge": 20.0}, tags={"source": "test"})
    p.label = 1.23
    p.model = regression_model
    return p


def _app_config(tmp_path, **overrides):
    base = {
        "TESTING": False,
        "ARIZE_ENABLED": True,
        "ARIZE_API_KEY": "test-api-key",
        "ARIZE_SPACE_KEY": "test-space-id",
        "ARIZE_ENVIRONMENT": "production",
        "ARIZE_FALLBACK_PATH": str(tmp_path / "arize_failed.jsonl"),
        "ARIZE_REGION": "",
        "ARIZE_VALIDATION_BATCH_ID": "staging-batch",
    }
    base.update(overrides)
    return base


def test_normalize_space_id_keeps_relay_base64_for_api():
    """UI Space key is Base64(Space:...); API expects opaque string, not digits-only."""
    assert _normalize_arize_space_id("U3BhY2U6MzkyOTk6MmtFVQ==") == "U3BhY2U6MzkyOTk6MmtFVQ=="


def test_normalize_space_id_plain_unchanged():
    assert _normalize_arize_space_id("test-space-id") == "test-space-id"


def test_normalize_space_id_respects_no_decode(monkeypatch):
    monkeypatch.setenv("ARIZE_SPACE_KEY_NO_DECODE", "1")
    raw = "U3BhY2U6MzkyOTk6MmtFVQ=="
    assert _normalize_arize_space_id(raw) == raw


def test_normalize_space_id_numeric_only_extracts_digits(monkeypatch):
    monkeypatch.setenv("ARIZE_SPACE_KEY_NUMERIC_ONLY", "1")
    assert _normalize_arize_space_id("U3BhY2U6MzkyOTk6MmtFVQ==") == "39299"


def test_should_log_arize_request_defaults_true():
    app = Flask(__name__)
    with app.test_request_context("/"):
        assert _should_log_arize_request() is True


def test_should_log_arize_request_query_false():
    app = Flask(__name__)
    with app.test_request_context("/?arize_log=false"):
        assert _should_log_arize_request() is False


def test_should_log_arize_request_header_false():
    app = Flask(__name__)
    with app.test_request_context("/", headers={"X-Arize-Log": "false"}):
        assert _should_log_arize_request() is False


def test_init_app_disabled_leaves_no_client(tmp_path):
    gw = ArizeGateway()
    app = SimpleNamespace(config=_app_config(tmp_path, ARIZE_ENABLED=False))
    gw.init_app(app)
    assert gw._client is None


def test_init_app_testing_skips_client(tmp_path):
    gw = ArizeGateway()
    app = SimpleNamespace(config=_app_config(tmp_path, TESTING=True))
    gw.init_app(app)
    assert gw._client is None


def test_log_inference_skips_when_no_client(sample_prediction, regression_model):
    gw = ArizeGateway()
    gw._enabled = False
    gw._client = None
    gw.log_inference(regression_model, sample_prediction)  # no exception


@patch("arize.api.Client")
def test_log_inference_calls_client_log(mock_client_cls, tmp_path, sample_prediction, regression_model):
    from concurrent.futures import Future
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    fut = Future()
    fut.set_result(MagicMock(status_code=200, text="ok"))
    mock_client.log.return_value = fut
    mock_client_cls.return_value = mock_client

    gw = ArizeGateway()
    app = SimpleNamespace(config=_app_config(tmp_path))
    gw.init_app(app)

    gw.log_inference(regression_model, sample_prediction)

    mock_client.log.assert_called_once()
    call_kw = mock_client.log.call_args[1]
    assert call_kw["model_id"] == "california-housing"
    assert call_kw["model_version"] == "2"


@patch("arize.api.Client")
def test_log_failure_writes_fallback_jsonl(mock_client_cls, tmp_path, sample_prediction, regression_model):
    mock_client = MagicMock()
    mock_client.log.side_effect = RuntimeError("upstream failure")
    mock_client_cls.return_value = mock_client

    fb = tmp_path / "failed.jsonl"
    gw = ArizeGateway()
    cfg = _app_config(tmp_path)
    cfg["ARIZE_FALLBACK_PATH"] = str(fb)
    app = SimpleNamespace(config=cfg)
    gw.init_app(app)

    gw.log_inference(regression_model, sample_prediction)

    lines = fb.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert "upstream failure" in payload["error"]
    assert payload["model_name"] == "california-housing"
    assert payload["true_value"] is None
    assert payload["prediction"] == 1.23


def test_end_to_end_arize_documentation_placeholder():
    """E2E: enable Arize via env, POST a prediction with optional ?arize_log=true, confirm in Arize UI."""
    pytest.skip("Manual verification against a dev/staging space; not run in CI.")
