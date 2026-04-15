import os

import numpy as np
import pytest
from unittest.mock import patch

from data5580_hw.app import create_app
from data5580_hw.controllers.prediction import prediction_controller
from data5580_hw.models.prediction import Explanations, Explanation, Model
from data5580_hw.services.database.database_client import db


@pytest.fixture
def app(tmp_path):
    os.environ["TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    db_path = tmp_path / "test.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    with app.app_context():
        db.create_all()

    yield app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def test_umap_service_single_row_returns_embedding_shape(tmp_path):
    from data5580_hw.services.umap_service import UMAPEmbeddingService

    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    # Warm-up fit with enough real rows (no synthetic augmentation).
    X_warm = np.random.RandomState(0).rand(8, 3)
    svc.compute_embeddings(X_warm, umap_params={"n_components": 2, "n_jobs": 1})

    X = np.array([[1.0, 2.0, 3.0]])
    embeddings = svc.compute_embeddings(X, umap_params={"n_components": 2, "n_jobs": 1})

    assert isinstance(embeddings, list)
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 2


def test_umap_service_single_row_without_history_raises(tmp_path):
    from data5580_hw.services.umap_service import UMAPEmbeddingService

    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    X = np.array([[1.0, 2.0, 3.0]])

    with pytest.raises(ValueError, match="not fitted yet"):
        svc.compute_embeddings(X, umap_params={"n_components": 2, "n_jobs": 1})


def test_umap_service_single_row_degenerate_single_feature(tmp_path):
    from data5580_hw.services.umap_service import UMAPEmbeddingService

    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    X = np.array([[5.0]])

    embeddings = svc.compute_embeddings(X, umap_params={"n_components": 2, "n_jobs": 1})

    assert embeddings == [[0.0, 0.0]]


def test_umap_service_multi_row_fits_and_persists(tmp_path):
    from data5580_hw.services.umap_service import UMAPEmbeddingService

    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    X = np.random.RandomState(0).rand(8, 3)

    embeddings1 = svc.compute_embeddings(X, umap_params={"n_components": 2, "n_jobs": 1})
    embeddings2 = svc.compute_embeddings(X, umap_params={"n_components": 2, "n_jobs": 1})

    assert len(embeddings1) == 8
    assert len(embeddings1[0]) == 2
    assert len(embeddings2) == 8

    # Persisted model + training matrix should exist on disk.
    assert any(str(p).endswith(".pkl") for p in tmp_path.glob("umap_model_*.pkl"))
    assert any(str(p).endswith(".npy") for p in tmp_path.glob("umap_training_*.npy"))


def test_prediction_controller_success_returns_label_and_embeddings(client, app):
    # Patch model loading/inference + make UMAP deterministic for fast tests.
    fake_model = Model(name="california-housing", version="4", type="REGRESSION")
    fake_model._explainer = None

    with patch(
        "data5580_hw.controllers.prediction.mlflow_gateway.get_model",
        return_value=fake_model,
    ), patch(
        "data5580_hw.controllers.prediction.model_service.create_inference",
        return_value=10,
    ), patch(
        "data5580_hw.controllers.prediction.umap_embedding_service.compute_embeddings",
        return_value=[[0.1, -0.2]],
    ):
        response = client.post(
            "/california-housing/version/4/predict",
            json={"features": {"x1": 1.0, "x2": 2.0}, "tags": {}},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert "label" in body
    assert "embeddings" in body
    assert isinstance(body["embeddings"], list)
    assert len(body["embeddings"]) == 1
    assert len(body["embeddings"][0]) == 2


def test_prediction_controller_get_prediction_by_id_uses_db(app):
    pred = Model(name="california-housing", version="4", type="REGRESSION")

    # Minimal Prediction object; db access is mocked below.
    from data5580_hw.models.prediction import Prediction

    prediction = Prediction(features={"x1": 1.0}, tags={}, label=10, model=pred)

    class MockQuery:
        def __init__(self, prediction_sql):
            self._prediction_sql = prediction_sql

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self._prediction_sql

    mock_prediction_sql = type(
        "MockPredictionSQL",
        (),
        {"to_prediction": lambda self: prediction},
    )()

    with patch(
        "data5580_hw.controllers.prediction.db.session.query",
        return_value=MockQuery(mock_prediction_sql),
    ):
        with app.app_context():
            resp, status = prediction_controller.get_prediction_by_id("any-id")

    assert status == 200
    assert resp.get_json()["id"] == prediction.id


def test_prediction_controller_invalid_input_returns_400(client):
    with patch(
        "data5580_hw.controllers.prediction.mlflow_gateway.get_model",
        return_value=Model(name="california-housing", version="4", type="REGRESSION"),
    ):
        response = client.post(
            "/california-housing/version/4/predict",
            json={"features": {"x1": 1.0}, "tags": "not-a-dict"},
        )

    assert response.status_code == 400
    assert "Invalid input data" in response.get_json().get("error", "")


def test_prediction_controller_umap_failure_returns_400(client):
    fake_model = Model(name="california-housing", version="4", type="REGRESSION")
    fake_model._explainer = None

    with patch(
        "data5580_hw.controllers.prediction.mlflow_gateway.get_model",
        return_value=fake_model,
    ), patch(
        "data5580_hw.controllers.prediction.model_service.create_inference",
        return_value=10,
    ), patch(
        "data5580_hw.controllers.prediction.umap_embedding_service.compute_embeddings",
        side_effect=ValueError("bad input for umap"),
    ):
        response = client.post(
            "/california-housing/version/4/predict",
            json={"features": {"x1": 1.0, "x2": 2.0}, "tags": {}},
        )

    assert response.status_code == 400
    assert "UMAP embedding calculation failed" in response.get_json().get("error", "")


def test_prediction_controller_explanations_branch(client):
    fake_model = Model(name="california-housing", version="4", type="REGRESSION")
    fake_model._explainer = object()  # make truthy so explanations are generated

    explanations = Explanations(
        explanations=[
            Explanation(name="0", values={"x1": 1.23}),
        ]
    )

    with patch(
        "data5580_hw.controllers.prediction.mlflow_gateway.get_model",
        return_value=fake_model,
    ), patch(
        "data5580_hw.controllers.prediction.model_service.create_inference",
        return_value=10,
    ), patch(
        "data5580_hw.controllers.prediction.umap_embedding_service.compute_embeddings",
        return_value=[[0.1, -0.2]],
    ), patch(
        "data5580_hw.controllers.prediction.explainer_service.create_explanation",
        return_value=explanations,
    ):
        response = client.post(
            "/california-housing/version/4/predict",
            json={"features": {"x1": 1.0}, "tags": {}},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert "explanations" in body
    assert body["explanations"] is not None

