"""Unit tests for ModelService.create_inference."""

from unittest.mock import MagicMock

import pytest

from data5580_hw.models.prediction import Model, Prediction
from data5580_hw.services.model_service import ModelService


def test_create_inference_calls_sklearn_predict():
    raw = MagicMock()
    raw.predict = MagicMock(return_value=[42.5])
    raw.feature_names_in_ = None

    model = Model(name="m", version="1", type="REGRESSION")
    model._model = raw

    pred = Prediction(features={"x": 1.0, "y": 2.0})
    out = ModelService.create_inference(model, pred)

    assert out == 42.5
    raw.predict.assert_called_once()
    call_df = raw.predict.call_args[0][0]
    assert len(call_df) == 1
    assert {"x", "y"} <= set(call_df.columns)
