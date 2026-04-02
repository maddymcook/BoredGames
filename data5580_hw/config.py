import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ARIZE_FALLBACK = _REPO_ROOT / "instance" / "arize_failed.jsonl"


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class Config:

    # MLflow — use the server where your registered models live (see Models in UI).
    # Override with MLFLOW_TRACKING_URI, e.g. http://localhost:8080 (not an empty server on another port).
    TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:8080")
    MODELS = {
        "california-housing": {
            # Version 1 is created by generate_regression_model.py on first register.
            "1": {
                "model": None,
                "model_type": "REGRESSION",
                "mlflow_flavor": "sklearn",
            },
            "2": {
                "model": None
                , "model_type": "REGRESSION"
                , "mlflow_flavor": "sklearn"
            }
            ,
            "4": {
                "model": None
                , "model_type": "REGRESSION"
                , "mlflow_flavor": "sklearn"
            }
        }
    }

    # Arize (see data5580_hw.gateways.arize_gateway)
    ARIZE_ENABLED = _env_bool("ARIZE_ENABLED", False)
    ARIZE_API_KEY = os.environ.get("ARIZE_API_KEY", "")
    ARIZE_SPACE_KEY = os.environ.get("ARIZE_SPACE_KEY", "")
    ARIZE_ENVIRONMENT = os.environ.get("ARIZE_ENVIRONMENT", "production")
    ARIZE_FALLBACK_PATH = os.environ.get(
        "ARIZE_FALLBACK_PATH", str(_DEFAULT_ARIZE_FALLBACK)
    )
    ARIZE_REGION = os.environ.get("ARIZE_REGION", "")
    ARIZE_VALIDATION_BATCH_ID = os.environ.get(
        "ARIZE_VALIDATION_BATCH_ID", "staging-batch"
    )

environments = {
    'config': Config()
}
