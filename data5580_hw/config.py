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

    # MLFlow
    TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:8080")
    MODELS = {
        "california-housing": {
            "1": {
                "model": None
                , "model_type": "REGRESSION"
                , "mlflow_flavor": "sklearn"
            },
            "2": {
                "model": None
                , "model_type": "REGRESSION"
                , "mlflow_flavor": "sklearn"
            },
            "4": {
                "model": None
                , "model_type": "REGRESSION"
                , "mlflow_flavor": "sklearn"
            }
        }
    }

    # Gemini LLM integration
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TIMEOUT_SECONDS = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "8"))
    # Arize (see data5580_hw.gateways.arize_gateway)
    ARIZE_ENABLED = _env_bool("ARIZE_ENABLED", True)
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

    # Celery + Redis async task processing
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_TRACK_STARTED = _env_bool("CELERY_TASK_TRACK_STARTED", True)
    CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "300"))
    CELERY_TASK_SOFT_TIME_LIMIT = int(
        os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "240")
    )
    CELERY_TASK_DEFAULT_RETRY_DELAY = int(
        os.environ.get("CELERY_TASK_DEFAULT_RETRY_DELAY", "10")
    )
    CELERY_TASK_MAX_RETRIES = int(os.environ.get("CELERY_TASK_MAX_RETRIES", "3"))
    CELERY_RESULT_EXPIRES = int(os.environ.get("CELERY_RESULT_EXPIRES", "3600"))

environments = {
    'config': Config()
}
