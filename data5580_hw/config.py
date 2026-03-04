import os
from pathlib import Path


class Config:

    # MLFlow
    TRACKING_URI = "http://localhost:8080"
    MODELS = {
        "california-housing": {
            "4": {
                "model": None
                , "model_type": "REGRESSION"
                , "mlflow_flavor": "sklearn"
            }
        }
    }

environments = {
    'config': Config()
}
