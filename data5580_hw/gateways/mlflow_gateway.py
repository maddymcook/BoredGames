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
        mlflow.set_tracking_uri(app.config['TRACKING_URI'])
        self.models = app.config['MODELS']

        # Unit tests run without a live MLflow server.
        if app.config.get('TESTING') or os.environ.get('TESTING'):
            return

        try:
            response = requests.get(app.config['TRACKING_URI'], timeout=5)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")
        except Exception as e:
            logger.warning(
                "MLflow not reachable at %s: %s. App will start; prediction needs a running server. "
                "Start with: python -m mlflow server --host 127.0.0.1 --port 8080 "
                "--backend-store-uri sqlite:///mlruns.db --workers 1",
                app.config['TRACKING_URI'],
                e,
            )
            return

        client = MlflowClient()
        for model_name in list(self.models.keys()):
            for version in list(self.models[model_name].keys()):
                flavor_ = self.models[model_name][version].get(
                    'mlflow_flavor', 'pyfunc'
                )
                try:
                    self.models[model_name][version]["model"] = self._load_model(
                        self._get_model_uri(model_name, version), flavor_
                    )
                except Exception as e:
                    logger.warning(
                        "Could not load MLflow model %s version %s: %s. "
                        "Register it with: python generate_regression_model.py (MLflow must be running).",
                        model_name,
                        version,
                        e,
                    )
                    self.models[model_name][version]["model"] = None
                    continue

                try:
                    run_id = client.get_model_version(model_name, version).run_id
                    run = mlflow.get_run(run_id)
                    outputs = getattr(run, "outputs", None)
                    model_outputs = (
                        getattr(outputs, "model_outputs", None) if outputs else None
                    )
                    if model_outputs:
                        for model_ in model_outputs:
                            model_details = mlflow.get_logged_model(model_.model_id)
                            if model_details.name == "model-explainer":
                                self.models[model_name][version]["explainer"] = (
                                    mlflow.pyfunc.load_model(model_details.model_uri)
                                )
                                break
                except Exception as ex:
                    logger.warning(
                        "Optional explainer not loaded for %s v%s: %s",
                        model_name,
                        version,
                        ex,
                    )

    def _get_model_uri(self, model_name, model_version):
        return f"models:/{model_name}/{model_version}"

    def _get_explainer_uri(self, run_id):
        return f"runs:/{run_id}/model-explainer"

    def _load_model(self, model_uri, model_flavor):
        if model_flavor == "sklearn":
            return mlflow.sklearn.load_model(model_uri)
        elif model_flavor == "tensorflow":
            return mlflow.tensorflow.load_model(model_uri)
        elif model_flavor == "pytorch":
            return mlflow.pytorch.load_model(model_uri)
        elif model_flavor == "xgboost":
            return mlflow.xgboost.load_model(model_uri)
        elif model_flavor == "pyfunc":
            return mlflow.pyfunc.load_model(model_uri)
        else:
            raise ValueError(f"Unsupported model flavor: {model_flavor}")

    def get_model(self, model_name, model_version) -> Model:

        model_ = self.models[model_name][model_version]

        model = Model(
            type=model_["model_type"]
            , name=model_name
            , version=model_version
        )

        model._model = model_['model']
        model._explainer = model_.get('explainer', None)

        return model

    def get_run_metrics(self, run_id: str):
        """
        Get run and its metrics from MLFlow by run ID.
        Returns dict with run_id, metrics, artifact_uri.
        Raises Exception if run_id is invalid or run not found.
        """
        client = MlflowClient()
        run = client.get_run(run_id)
        return {
            "run_id": run.info.run_id,
            "metrics": dict(run.data.metrics) if run.data.metrics else {},
            "artifact_uri": run.info.artifact_uri,
        }

mlflow_gateway: MLFlowGateway = MLFlowGateway()
