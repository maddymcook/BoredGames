import os
import json
from datetime import datetime
from unittest.mock import patch

import pytest

from data5580_hw.app import create_app
from data5580_hw.models.prediction import Model
from data5580_hw.services.database.database_client import db
from data5580_hw.services.database.prediction import ModelSql, PredictionSQL


@pytest.fixture
def client():
    os.environ["TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
        yield c


def _seed_prediction(prediction_id: str, model_sql: ModelSql, features: dict, label: float, embeddings):
    p = PredictionSQL(
        id=prediction_id,
        features=json.dumps(features),
        tags="{}",
        label=str(label),
        embeddings=json.dumps(embeddings),
        actual=None,
        threshold=None,
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        model_id=model_sql.id,
    )
    db.session.add(p)
    db.session.commit()
    return p


def test_get_prediction_by_id_route_returns_prediction(client):
    with client.application.app_context():
        model = Model(name="california-housing", version="1", type="REGRESSION")
        model_sql = ModelSql.from_model(model)
        _seed_prediction(
            prediction_id="pred-1",
            model_sql=model_sql,
            features={"f1": 1.0, "f2": 2.0},
            label=10.0,
            embeddings=[[1.0, 2.0]],
        )

    response = client.get("/prediction/pred-1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "pred-1"
    assert data["features"]["f1"] == 1.0


def test_get_prediction_explainer_returns_summary_and_nearest(client):
    with client.application.app_context():
        model = Model(name="california-housing", version="1", type="REGRESSION")
        model_sql = ModelSql.from_model(model)
        _seed_prediction("pred-main", model_sql, {"f1": 1.0, "f2": 2.0}, 10.0, [[1.0, 2.0]])
        _seed_prediction("pred-near-1", model_sql, {"f1": 1.1, "f2": 2.0}, 10.4, [[1.1, 2.0]])
        _seed_prediction("pred-near-2", model_sql, {"f1": 0.9, "f2": 2.1}, 9.8, [[0.9, 2.1]])

    with patch(
        "data5580_hw.controllers.prediction.llm_gateway.summarize_prediction_differences",
        return_value="- Similar labels\n- Minor feature variance",
    ):
        response = client.get("/prediction/pred-main/explainer")

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "pred-main"
    assert "summary" in data and "Similar labels" in data["summary"]
    assert len(data["nearest_predictions"]) >= 1
    assert isinstance(data["key_differences"], list)


def test_get_prediction_explainer_handles_no_nearest_predictions(client):
    with client.application.app_context():
        model = Model(name="california-housing", version="1", type="REGRESSION")
        model_sql = ModelSql.from_model(model)
        _seed_prediction("pred-alone", model_sql, {"f1": 1.0}, 5.0, [[1.0]])

    response = client.get("/prediction/pred-alone/explainer")
    assert response.status_code == 200
    data = response.get_json()
    assert data["nearest_predictions"] == []
    assert "No similar predictions" in data["summary"]


def test_get_prediction_explainer_handles_llm_failure(client):
    with client.application.app_context():
        model = Model(name="california-housing", version="1", type="REGRESSION")
        model_sql = ModelSql.from_model(model)
        _seed_prediction("pred-main-2", model_sql, {"f1": 1.0, "f2": 2.0}, 10.0, [[1.0, 2.0]])
        _seed_prediction("pred-near-3", model_sql, {"f1": 1.2, "f2": 2.1}, 11.0, [[1.2, 2.1]])

    with patch(
        "data5580_hw.controllers.prediction.llm_gateway.summarize_prediction_differences",
        return_value="LLM summary unavailable due to an upstream API error.",
    ):
        response = client.get("/prediction/pred-main-2/explainer")

    assert response.status_code == 200
    data = response.get_json()
    assert "LLM summary unavailable" in data["summary"]
