import logging
import os

import mlflow
import requests
from mlflow.tracking import MlflowClient

from data5580_hw.models.prediction import Model

logger = logging.getLogger(__name__)


class MLFlowGateway:
    models = {}

    def init_app(self, app):
        mlflow.set_tracking_uri(app.config["TRACKING_URI"])
        self.models = app.config.get("MODELS", {})

        if app.config.get("TESTING") or os.environ.get("TESTING"):
            return

        try:
            response = requests.get(app.config["TRACKING_URI"], timeout=2)
            if response.status_code != 200:
                raise Exception(f"MLFlow server returned {response.status_code}")

            client = MlflowClient()
            for model in self.models.keys():
                for version in self.models[model].keys():
                    flavor_ = self.models[model][version].get("mlflow_flavor", "pyfunc")
                    self.models[model][version]["model"] = self._load_model(
                        self._get_model_uri(model, version), flavor_
                    )
                    # Optionally load a linked explainer model from the run's outputs.
                    try:
                        model_version_info = client.get_model_version(model, version)
                        run = mlflow.get_run(model_version_info.run_id)
                        outputs = getattr(run, "outputs", None)
                        model_outputs = getattr(outputs, "model_outputs", []) if outputs else []
                        if model_outputs:
                            logged_model = mlflow.get_logged_model(model_outputs[0].model_id)
                            self.models[model][version]["explainer"] = mlflow.pyfunc.load_model(
                                logged_model.model_uri
                            )
                    except Exception:
                        # Keep app startup resilient if explainer discovery fails.
                        self.models[model][version]["explainer"] = None
        except Exception as e:
            logger.warning(
                "MLFlow not available at %s: %s. App will start; /models/compare and prediction need MLFlow. Start with: mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db (on Windows add --workers 1).",
                app.config["TRACKING_URI"],
                e,
            )

    def _get_model_uri(self, model_name, model_version):
        return f"models:/{model_name}/{model_version}"

    def _load_model(self, model_uri, model_flavor):
        if model_flavor == "sklearn":
            return mlflow.sklearn.load_model(model_uri)
        if model_flavor == "tensorflow":
            return mlflow.tensorflow.load_model(model_uri)
        if model_flavor == "pytorch":
            return mlflow.pytorch.load_model(model_uri)
        if model_flavor == "xgboost":
            return mlflow.xgboost.load_model(model_uri)
        if model_flavor == "pyfunc":
            return mlflow.pyfunc.load_model(model_uri)
        raise ValueError(f"Unsupported model flavor: {model_flavor}")

    def get_model(self, model_name, model_version) -> Model:
        model_ = self.models[model_name][model_version]
        model = Model(type=model_["model_type"], name=model_name, version=model_version)
        model._model = model_["model"]
        model._explainer = model_.get("explainer", None)
        return model

    def get_run_metrics(self, run_id: str):
        client = MlflowClient()
        run = client.get_run(run_id)
        return {
            "run_id": run.info.run_id,
            "metrics": dict(run.data.metrics) if run.data.metrics else {},
            "artifact_uri": run.info.artifact_uri,
        }


mlflow_gateway: MLFlowGateway = MLFlowGateway()
