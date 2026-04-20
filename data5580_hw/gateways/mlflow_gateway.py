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
        logger.info(
            "MLflow gateway MODELS keys: %s",
            {name: list(vers.keys()) for name, vers in self.models.items()},
        )

        if app.config.get("TESTING") or os.environ.get("TESTING"):
            return

        try:
            self._assert_tracking_server_available(app.config["TRACKING_URI"])
            self._load_registered_models()
        except Exception as e:
            logger.warning(
                "MLFlow not available at %s: %s. App will start; /models/compare and prediction need MLFlow. Start with: mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db (on Windows add --workers 1).",
                app.config["TRACKING_URI"],
                e,
            )

    def _assert_tracking_server_available(self, tracking_uri: str) -> None:
        response = requests.get(tracking_uri, timeout=2)
        if response.status_code != 200:
            raise requests.HTTPError(
                f"MLFlow server returned {response.status_code} for {tracking_uri}"
            )

    def _load_registered_models(self) -> None:
        client = MlflowClient()
        for model_name, versions in self.models.items():
            for version, model_cfg in versions.items():
                flavor_ = model_cfg.get("mlflow_flavor", "pyfunc")
                model_cfg["model"] = self._load_model(
                    self._get_model_uri(model_name, version), flavor_
                )
                model_cfg["explainer"] = self._load_linked_explainer(
                    client, model_name, version
                )

    def _load_linked_explainer(
        self, client: MlflowClient, model_name: str, version: str
    ):
        # Keep app startup resilient if explainer discovery fails.
        try:
            model_version_info = client.get_model_version(model_name, version)
            run = mlflow.get_run(model_version_info.run_id)
            outputs = getattr(run, "outputs", None)
            model_outputs = getattr(outputs, "model_outputs", []) if outputs else []
            if not model_outputs:
                return None
            logged_model = mlflow.get_logged_model(model_outputs[0].model_id)
            return mlflow.pyfunc.load_model(logged_model.model_uri)
        except Exception:
            return None

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

    def _registry(self):
        """
        Prefer Flask app config during requests so lookups match the running app
        even if this singleton's self.models was never set (e.g. class default {}).
        """
        try:
            from flask import current_app, has_app_context

            if has_app_context() and "MODELS" in current_app.config:
                return current_app.config["MODELS"]
        except RuntimeError:
            pass
        return self.models

    def get_model(self, model_name, model_version) -> Model:
        # URL path segments are strings; config keys must match (e.g. "4" not 4).
        ver = str(model_version).strip()
        registry = self._registry()
        versions = registry.get(model_name)
        if versions is None:
            raise KeyError(model_name)
        model_ = versions.get(ver)
        if model_ is None and ver.isdigit():
            model_ = versions.get(int(ver))
        if model_ is None:
            raise KeyError((model_name, ver))
        # Startup model loading can be skipped or fail transiently; load on demand.
        if model_.get("model") is None:
            flavor_ = model_.get("mlflow_flavor", "pyfunc")
            model_["model"] = self._load_model(self._get_model_uri(model_name, ver), flavor_)
        model = Model(type=model_["model_type"], name=model_name, version=str(model_version))
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
