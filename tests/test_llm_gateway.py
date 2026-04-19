"""Tests for LLMGateway (Gemini) without calling the real API."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from data5580_hw.gateways.llm_gateway import LLMGateway


def test_summarize_when_disabled_returns_config_message():
    gw = LLMGateway()
    gw.init_app(SimpleNamespace(config={"GEMINI_API_KEY": ""}))
    text = gw.summarize_prediction_differences("any prompt")
    assert "Gemini is not configured" in text


def test_summarize_success_extracts_text():
    gw = LLMGateway()
    gw._enabled = True
    gw._api_key = "k"
    gw._model = "gemini-test"
    gw._timeout_seconds = 5

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Hello"}, {"text": "World"}],
                }
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("data5580_hw.gateways.llm_gateway.requests.post", return_value=mock_resp):
        out = gw.summarize_prediction_differences("prompt")

    assert "Hello" in out and "World" in out


def test_summarize_empty_candidates_message():
    gw = LLMGateway()
    gw._enabled = True
    gw._api_key = "k"
    gw._model = "gemini-test"
    gw._timeout_seconds = 5

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"candidates": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("data5580_hw.gateways.llm_gateway.requests.post", return_value=mock_resp):
        out = gw.summarize_prediction_differences("p")

    assert "No summary generated" in out


def test_summarize_timeout_message():
    gw = LLMGateway()
    gw._enabled = True
    gw._api_key = "k"
    gw._model = "gemini-test"
    gw._timeout_seconds = 1

    with patch(
        "data5580_hw.gateways.llm_gateway.requests.post",
        side_effect=requests.Timeout,
    ):
        out = gw.summarize_prediction_differences("p")

    assert "timed out" in out.lower()


def test_summarize_api_error_message():
    gw = LLMGateway()
    gw._enabled = True
    gw._api_key = "k"
    gw._model = "gemini-test"
    gw._timeout_seconds = 1

    with patch(
        "data5580_hw.gateways.llm_gateway.requests.post",
        side_effect=RuntimeError("boom"),
    ):
        out = gw.summarize_prediction_differences("p")

    assert "upstream" in out.lower() or "unavailable" in out.lower()


def test_init_app_reads_config():
    gw = LLMGateway()
    cfg = SimpleNamespace(
        config={
            "GEMINI_API_KEY": "  secret  ",
            "GEMINI_MODEL": " custom-model ",
            "GEMINI_TIMEOUT_SECONDS": "12",
        }
    )
    gw.init_app(cfg)
    assert gw._api_key == "secret"
    assert gw._model == "custom-model"
    assert gw._timeout_seconds == 12
    assert gw._enabled is True
