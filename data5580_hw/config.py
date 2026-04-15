import os
from pathlib import Path


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

environments = {
    'config': Config()
}
