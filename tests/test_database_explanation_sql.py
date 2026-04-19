"""Coverage for ExplanationSql.from_prediction."""

from data5580_hw.models.prediction import Explanation, Explanations, Prediction
from data5580_hw.services.database.prediction import ExplanationSql


def test_from_prediction_empty_when_no_explanations():
    p = Prediction(features={"x": 1.0})
    p.id = "pid"
    assert ExplanationSql.from_prediction(p) == []


def test_from_prediction_maps_explanation_rows():
    ex = Explanations()
    ex.explanations.append(Explanation(name="0", values={"f": 0.5}))
    p = Prediction(features={"f": 1.0})
    p.id = "pid-1"
    p.explanations = ex

    rows = ExplanationSql.from_prediction(p)
    assert len(rows) == 1
    assert rows[0].prediction_id == "pid-1"
    assert rows[0].name == "0"
    assert '"f": 0.5' in rows[0].values or "0.5" in rows[0].values
