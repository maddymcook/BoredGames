from flask import Blueprint, jsonify, request
from celery.exceptions import TimeoutError as CeleryTimeoutError

from data5580_hw.celery_app import celery_app
from data5580_hw.tasks.jobs import long_running_task, short_running_task

tasks = Blueprint("tasks", __name__)


def _parse_wait_args() -> tuple[bool, int]:
    wait = request.args.get("wait", "false").lower() in {"1", "true", "yes"}
    timeout_raw = request.args.get("timeout", "15")
    try:
        timeout = int(timeout_raw)
    except (TypeError, ValueError):
        timeout = 15
    return wait, max(1, timeout)


def _wait_response(async_result, timeout: int):
    try:
        result = async_result.get(timeout=timeout)
        return jsonify({"task_id": async_result.id, "state": "SUCCESS", "result": result}), 200
    except CeleryTimeoutError:
        return jsonify({"task_id": async_result.id, "state": async_result.state}), 202
    except Exception as e:
        return jsonify({"task_id": async_result.id, "state": "FAILURE", "error": str(e)}), 500


@tasks.route("/tasks/short", methods=["POST"])
def enqueue_short_task():
    data = request.get_json(silent=True) or {}
    payload = data.get("payload") if isinstance(data, dict) else {}
    async_result = short_running_task.apply_async(args=[payload])
    wait, timeout = _parse_wait_args()
    if wait:
        return _wait_response(async_result, timeout)
    return jsonify({"task_id": async_result.id, "state": "PENDING"}), 202


@tasks.route("/tasks/long", methods=["POST"])
def enqueue_long_task():
    data = request.get_json(silent=True) or {}
    payload = data.get("payload") if isinstance(data, dict) else {}
    duration = data.get("duration_seconds", 10) if isinstance(data, dict) else 10

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return jsonify({"error": "duration_seconds must be an integer"}), 400

    if duration <= 0:
        return jsonify({"error": "duration_seconds must be greater than 0"}), 400

    async_result = long_running_task.apply_async(args=[duration, payload])
    wait, timeout = _parse_wait_args()
    if wait:
        return _wait_response(async_result, timeout)
    return (
        jsonify(
            {
                "task_id": async_result.id,
                "state": "PENDING",
                "duration_seconds": duration,
            }
        ),
        202,
    )


@tasks.route("/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    response = {"task_id": task_id, "state": result.state}

    if result.state == "PENDING":
        response["status"] = "Task is queued or unknown."
        return jsonify(response), 200

    if result.state in {"STARTED", "PROGRESS"}:
        response["progress"] = result.info or {}
        return jsonify(response), 200

    if result.state == "SUCCESS":
        response["result"] = result.result
        return jsonify(response), 200

    if result.state in {"FAILURE", "REVOKED"}:
        response["error"] = str(result.info)
        return jsonify(response), 500

    response["meta"] = str(result.info)
    return jsonify(response), 200
