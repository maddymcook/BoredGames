"""
One-shot local check: MLflow up, POST /predict, optional Arize.

Setup (two terminals from repo root `data5580_hw`):

  Terminal A — MLflow (if not already running):
    python -m mlflow server --host 127.0.0.1 --port 8080 `
      --backend-store-uri sqlite:///mlruns.db --workers 1

  Terminal B — Arize + API (PowerShell):
    $env:ARIZE_ENABLED="1"; $env:ARIZE_API_KEY="..."; $env:ARIZE_SPACE_KEY="..."
    $env:ARIZE_ENVIRONMENT="production"
    python -m flask --app data5580_hw.app:create_app run --host 127.0.0.1 --port 5000

  Terminal C — smoke test:
    python scripts/smoke_predict.py

If the model is missing in MLflow, register it once:
  python generate_regression_model.py

Requires the same env as the API for Arize logging on the server process.
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smoke_predict")

MLFLOW_URL = "http://127.0.0.1:8080"
API_BASE = "http://127.0.0.1:5000"

# sklearn California housing feature names (order does not matter for dict JSON)
PAYLOAD = {
    "features": {
        "MedInc": 3.8477,
        "HouseAge": 52.0,
        "AveRooms": 6.2814,
        "AveBedrms": 1.0811,
        "Population": 1422.0,
        "AveOccup": 3.0,
        "Latitude": 35.63,
        "Longitude": -119.59,
    },
    "tags": {"smoke": "scripts/smoke_predict.py"},
    "actual": 1.85,
}


def _get(url: str, timeout: float = 5.0) -> int:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def _post_json(url: str, body: dict, timeout: float = 120.0) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def main() -> int:
    try:
        code = _get(MLFLOW_URL)
        logger.info("MLflow OK at %s (HTTP %s)", MLFLOW_URL, code)
    except urllib.error.URLError as e:
        logger.error(
            "MLflow not reachable at %s. Start: python -m mlflow server "
            "--host 127.0.0.1 --port 8080 --backend-store-uri sqlite:///mlruns.db --workers 1",
            MLFLOW_URL,
        )
        logger.error("%s", e)
        return 1

    url = f"{API_BASE}/california-housing/version/1/predict"
    try:
        status, text = _post_json(url, PAYLOAD)
    except urllib.error.URLError as e:
        logger.error(
            "API not reachable at %s. In another terminal: "
            "python -m flask --app data5580_hw.app:create_app run --host 127.0.0.1 --port 5000",
            API_BASE,
        )
        logger.error("%s", e)
        return 1
    except Exception as e:
        logger.error("Request failed: %s", e)
        return 1

    logger.info("POST %s -> HTTP %s", url, status)
    print(text[:2000])
    if status != 200:
        return 1

    logger.info(
        "If ARIZE_ENABLED=1 and keys are set, check Arize UI for model "
        "'california-housing' (same version as in the URL). "
        "On failure, see instance/arize_failed.jsonl"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
