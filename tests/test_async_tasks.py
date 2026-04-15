import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from data5580_hw.app import create_app


@pytest.fixture
def client():
    os.environ["TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.test_client() as c:
        with app.app_context():
            from data5580_hw.services.database.database_client import db

            db.create_all()
        yield c


def test_enqueue_short_task_returns_202(client):
    with patch("data5580_hw.routes.tasks.short_running_task.apply_async") as mock_apply:
        mock_apply.return_value = SimpleNamespace(id="short-123")
        response = client.post(
            "/tasks/short",
            json={"payload": {"idempotency_key": "abc-1"}},
        )

    assert response.status_code == 202
    assert response.json["task_id"] == "short-123"
    assert response.json["state"] == "PENDING"


def test_enqueue_short_task_wait_true_returns_result(client):
    fake_async = SimpleNamespace(id="short-wait-1", state="SUCCESS")
    fake_async.get = lambda timeout=15: {"status": "completed"}
    with patch("data5580_hw.routes.tasks.short_running_task.apply_async", return_value=fake_async):
        response = client.post("/tasks/short?wait=true&timeout=5", json={"payload": {}})

    assert response.status_code == 200
    assert response.json["task_id"] == "short-wait-1"
    assert response.json["state"] == "SUCCESS"
    assert response.json["result"]["status"] == "completed"


def test_enqueue_long_task_validates_duration(client):
    response = client.post("/tasks/long", json={"duration_seconds": "bad"})
    assert response.status_code == 400
    assert "duration_seconds" in response.json["error"]

    response = client.post("/tasks/long", json={"duration_seconds": 0})
    assert response.status_code == 400
    assert "greater than 0" in response.json["error"]


def test_enqueue_long_task_returns_202(client):
    with patch("data5580_hw.routes.tasks.long_running_task.apply_async") as mock_apply:
        mock_apply.return_value = SimpleNamespace(id="long-123")
        response = client.post(
            "/tasks/long",
            json={"duration_seconds": 3, "payload": {"idempotency_key": "abc-2"}},
        )

    assert response.status_code == 202
    assert response.json["task_id"] == "long-123"
    assert response.json["state"] == "PENDING"
    assert response.json["duration_seconds"] == 3


def test_enqueue_long_task_wait_true_returns_result(client):
    fake_async = SimpleNamespace(id="long-wait-1", state="SUCCESS")
    fake_async.get = lambda timeout=15: {"status": "completed", "duration_seconds": 3}
    with patch("data5580_hw.routes.tasks.long_running_task.apply_async", return_value=fake_async):
        response = client.post(
            "/tasks/long?wait=true&timeout=5",
            json={"duration_seconds": 3, "payload": {"idempotency_key": "abc-3"}},
        )

    assert response.status_code == 200
    assert response.json["task_id"] == "long-wait-1"
    assert response.json["state"] == "SUCCESS"


def test_get_task_status_success(client):
    fake_result = SimpleNamespace(
        state="SUCCESS",
        info={"done": True},
        result={"status": "completed"},
    )
    with patch("data5580_hw.routes.tasks.celery_app.AsyncResult", return_value=fake_result):
        response = client.get("/tasks/task-1")

    assert response.status_code == 200
    assert response.json["state"] == "SUCCESS"
    assert response.json["result"]["status"] == "completed"


def test_get_task_status_failure(client):
    fake_result = SimpleNamespace(state="FAILURE", info=RuntimeError("boom"), result=None)
    with patch("data5580_hw.routes.tasks.celery_app.AsyncResult", return_value=fake_result):
        response = client.get("/tasks/task-2")

    assert response.status_code == 500
    assert response.json["state"] == "FAILURE"
    assert "boom" in response.json["error"]
