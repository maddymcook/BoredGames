import time
from typing import Any

from data5580_hw.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="data5580_hw.tasks.short_running_task",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_jitter=True,
)
def short_running_task(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Fast async task example.
    Include an idempotency key in payload for callers retrying submissions.
    """
    payload = payload or {}
    if payload.get("simulate_failure"):
        raise RuntimeError("Simulated transient failure for retry testing.")
    return {
        "status": "completed",
        "task": "short_running_task",
        "idempotency_key": payload.get("idempotency_key"),
        "echo": payload,
    }


@celery_app.task(
    bind=True,
    name="data5580_hw.tasks.long_running_task",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_jitter=True,
)
def long_running_task(
    self,
    duration_seconds: int = 10,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Long-running async task example with progress updates.
    """
    payload = payload or {}
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than 0")

    for i in range(duration_seconds):
        time.sleep(1)
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": duration_seconds},
        )

    if payload.get("simulate_failure"):
        raise RuntimeError("Simulated transient failure for retry testing.")

    return {
        "status": "completed",
        "task": "long_running_task",
        "duration_seconds": duration_seconds,
        "idempotency_key": payload.get("idempotency_key"),
        "echo": payload,
    }
