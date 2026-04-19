"""Unit tests for ExplainerService (SHAP-style array layouts)."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from data5580_hw.models.prediction import Model, Prediction
from data5580_hw.services.explainer_service import ExplainerService


def test_create_explanation_reshapes_1d_array():
    raw_model = MagicMock()
    raw_model.feature_names_in_ = np.array(["a", "b"])
    explainer = MagicMock()
    explainer.predict = MagicMock(return_value=np.array([0.1, 0.2]))

    model = Model(name="m", version="1", type="REGRESSION")
    model._model = raw_model
    model._explainer = explainer

    pred = Prediction(features={"a": 1.0, "b": 2.0})
    out = ExplainerService.create_explanation(model, pred)

    assert len(out.explanations) == 1
    assert out.explanations[0].values["a"] == pytest.approx(0.1)
    assert out.explanations[0].values["b"] == pytest.approx(0.2)


def test_create_explanation_keeps_2d_array_rows():
    raw_model = MagicMock()
    raw_model.feature_names_in_ = np.array(["f1"])
    explainer = MagicMock()
    explainer.predict = MagicMock(
        return_value=np.array([[0.5], [0.6]])
    )

    model = Model(name="m", version="1", type="REGRESSION")
    model._model = raw_model
    model._explainer = explainer

    pred = Prediction(features={"f1": 3.0})
    out = ExplainerService.create_explanation(model, pred)

    assert len(out.explanations) == 2
    assert out.explanations[0].name == "0"
    assert out.explanations[1].name == "1"
