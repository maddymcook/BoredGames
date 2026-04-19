"""Tests for Prediction.get_pandas_frame_aligned_to_model edge cases."""

import pytest

from data5580_hw.models.prediction import Prediction


def test_aligned_frame_raises_when_feature_missing():
    raw = type("M", (), {"feature_names_in_": ["a", "b", "c"]})()
    pred = Prediction(features={"a": 1.0, "b": 2.0})

    with pytest.raises(ValueError, match="Missing features"):
        pred.get_pandas_frame_aligned_to_model(raw)
